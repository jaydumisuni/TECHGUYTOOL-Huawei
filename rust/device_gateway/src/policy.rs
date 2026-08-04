use crate::error::GatewayError;
use crate::model::{OperationStage, ProviderManifest};
use chrono::{DateTime, Duration, Utc};
use std::collections::BTreeSet;

pub const MAX_WORKER_LEASE_SECONDS: i64 = 300;

const ALLOWED_CAPABILITIES: &[&str] = &[
    "contract.publish",
    "diagnostics.read",
    "evidence.read",
    "journal.append",
    "operation.coordinate",
    "session.coordinate",
    "worker.heartbeat",
];

const FORBIDDEN_DEVICE_CAPABILITIES: &[&str] = &[
    "device.erase",
    "device.flash",
    "device.loader_transfer",
    "device.partition_write",
    "device.reboot",
    "device.relock",
    "device.unlock",
    "device.write_oeminfo",
];

pub fn validate_sha256(value: &str, field: &str) -> Result<(), GatewayError> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return Err(GatewayError::InvalidInput(format!(
            "{field} must be a lowercase SHA-256 digest"
        )));
    }
    Ok(())
}

pub fn validate_provider_manifest(manifest: &ProviderManifest) -> Result<(), GatewayError> {
    if manifest.component_id.is_empty() || manifest.component_id.len() > 128 {
        return Err(GatewayError::InvalidInput(
            "component_id must contain 1 to 128 characters".to_owned(),
        ));
    }
    if !manifest
        .component_id
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
    {
        return Err(GatewayError::InvalidInput(
            "component_id contains unsupported characters".to_owned(),
        ));
    }
    validate_semver(&manifest.version)?;
    validate_sorted_unique(&manifest.contract_authorities, "contract_authorities")?;
    validate_sorted_unique(&manifest.capabilities, "capabilities")?;
    if manifest.capabilities.is_empty() {
        return Err(GatewayError::InvalidInput(
            "provider must declare at least one capability".to_owned(),
        ));
    }
    for capability in &manifest.capabilities {
        if FORBIDDEN_DEVICE_CAPABILITIES.contains(&capability.as_str()) {
            return Err(GatewayError::PolicyDenied(format!(
                "Phase 3 forbids device capability {capability:?}"
            )));
        }
        if !ALLOWED_CAPABILITIES.contains(&capability.as_str()) {
            return Err(GatewayError::PolicyDenied(format!(
                "capability {capability:?} is not in the Phase 3 allowlist"
            )));
        }
    }
    Ok(())
}

pub fn ensure_provider_authority(
    manifest: &ProviderManifest,
    authority: &str,
) -> Result<(), GatewayError> {
    if !manifest
        .contract_authorities
        .iter()
        .any(|candidate| candidate == authority)
    {
        return Err(GatewayError::PolicyDenied(format!(
            "provider {:?} is not allowed to publish authority {:?}",
            manifest.component_id, authority
        )));
    }
    if !manifest
        .capabilities
        .iter()
        .any(|capability| capability == "contract.publish")
    {
        return Err(GatewayError::PolicyDenied(format!(
            "provider {:?} lacks contract.publish capability",
            manifest.component_id
        )));
    }
    Ok(())
}

pub fn ensure_worker_capabilities(capabilities: &[String]) -> Result<(), GatewayError> {
    validate_sorted_unique(capabilities, "worker capabilities")?;
    if capabilities.is_empty() {
        return Err(GatewayError::InvalidInput(
            "worker must declare at least one capability".to_owned(),
        ));
    }
    for capability in capabilities {
        if FORBIDDEN_DEVICE_CAPABILITIES.contains(&capability.as_str()) {
            return Err(GatewayError::PolicyDenied(format!(
                "Phase 3 worker capability {capability:?} is forbidden"
            )));
        }
        if !ALLOWED_CAPABILITIES.contains(&capability.as_str()) {
            return Err(GatewayError::PolicyDenied(format!(
                "worker capability {capability:?} is not allowlisted"
            )));
        }
    }
    Ok(())
}

pub fn validate_worker_deadline(now: &str, deadline_at: &str) -> Result<(), GatewayError> {
    let now = parse_timestamp(now)?;
    let deadline = parse_timestamp(deadline_at)?;
    if deadline <= now {
        return Err(GatewayError::InvalidInput(
            "worker deadline must be in the future".to_owned(),
        ));
    }
    let maximum = now
        .checked_add_signed(Duration::seconds(MAX_WORKER_LEASE_SECONDS))
        .ok_or_else(|| GatewayError::InvalidInput("worker deadline overflowed".to_owned()))?;
    if deadline > maximum {
        return Err(GatewayError::InvalidInput(format!(
            "worker deadline exceeds the {MAX_WORKER_LEASE_SECONDS}-second maximum lease"
        )));
    }
    Ok(())
}

pub fn ensure_stage_transition(
    current: OperationStage,
    next: OperationStage,
) -> Result<(), GatewayError> {
    if current == next {
        return Ok(());
    }
    let allowed = match current {
        OperationStage::Requested => matches!(
            next,
            OperationStage::EvidenceCollection
                | OperationStage::Blocked
                | OperationStage::Failed
                | OperationStage::Cancelled
        ),
        OperationStage::EvidenceCollection => matches!(
            next,
            OperationStage::DecisionPending
                | OperationStage::Blocked
                | OperationStage::Failed
                | OperationStage::Cancelled
        ),
        OperationStage::DecisionPending => matches!(
            next,
            OperationStage::AuthorizationPending
                | OperationStage::Blocked
                | OperationStage::Failed
                | OperationStage::Cancelled
        ),
        OperationStage::AuthorizationPending => matches!(
            next,
            OperationStage::VerificationPending
                | OperationStage::Blocked
                | OperationStage::Failed
                | OperationStage::Cancelled
        ),
        OperationStage::VerificationPending => matches!(
            next,
            OperationStage::Completed | OperationStage::Blocked | OperationStage::Failed
        ),
        OperationStage::Blocked => matches!(
            next,
            OperationStage::EvidenceCollection
                | OperationStage::DecisionPending
                | OperationStage::Failed
                | OperationStage::Cancelled
        ),
        OperationStage::Completed | OperationStage::Failed | OperationStage::Cancelled => false,
    };
    if !allowed {
        return Err(GatewayError::PolicyDenied(format!(
            "operation stage transition {current:?} -> {next:?} is not permitted"
        )));
    }
    Ok(())
}

pub(crate) fn parse_timestamp(value: &str) -> Result<DateTime<Utc>, GatewayError> {
    DateTime::parse_from_rfc3339(value)
        .map(|timestamp| timestamp.with_timezone(&Utc))
        .map_err(|_| {
            GatewayError::InvalidInput(format!(
                "timestamp {value:?} must be RFC3339 with an explicit offset"
            ))
        })
}

fn validate_semver(value: &str) -> Result<(), GatewayError> {
    let parts: Vec<&str> = value.split('.').collect();
    if parts.len() != 3
        || parts.iter().any(|part| {
            part.is_empty()
                || !part.bytes().all(|byte| byte.is_ascii_digit())
                || (part.len() > 1 && part.starts_with('0'))
        })
    {
        return Err(GatewayError::InvalidInput(
            "provider version must use ASCII MAJOR.MINOR.PATCH".to_owned(),
        ));
    }
    Ok(())
}

fn validate_sorted_unique(values: &[String], field: &str) -> Result<(), GatewayError> {
    let set: BTreeSet<&String> = values.iter().collect();
    let sorted: Vec<String> = set.into_iter().cloned().collect();
    if values != sorted {
        return Err(GatewayError::InvalidInput(format!(
            "{field} must be lexicographically sorted and unique"
        )));
    }
    Ok(())
}

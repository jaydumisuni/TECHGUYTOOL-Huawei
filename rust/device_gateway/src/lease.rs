use chrono::DateTime;
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeSet;
use std::fmt;
use std::path::Path;
use techguy_contracts_core::{load_registry, validate_contract, ValidationContext};

#[derive(Debug)]
pub enum LeaseGuardError {
    Contract(String),
    InvalidContext(String),
    Policy(String),
    Storage(rusqlite::Error),
}

impl fmt::Display for LeaseGuardError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Contract(message) => write!(f, "contract rejected: {message}"),
            Self::InvalidContext(message) => write!(f, "invalid lease context: {message}"),
            Self::Policy(message) => write!(f, "lease policy rejected: {message}"),
            Self::Storage(error) => write!(f, "lease storage error: {error}"),
        }
    }
}

impl std::error::Error for LeaseGuardError {}

impl From<rusqlite::Error> for LeaseGuardError {
    fn from(value: rusqlite::Error) -> Self {
        Self::Storage(value)
    }
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct ModeLeaseContext {
    pub physical_session_id: String,
    pub current_mode: String,
    pub now: String,
    pub request_reboot: bool,
    pub request_stock_fastboot_restore: bool,
    pub satisfied_release_conditions: BTreeSet<String>,
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct ExecutionLeaseContext {
    pub physical_session_id: String,
    pub recipe_hash: String,
    pub adapter_id: String,
    pub adapter_version: String,
    pub artifact_hashes: Vec<String>,
    pub partition: String,
    pub range_manifest_sha256: String,
    pub write_bytes: u64,
    pub current_mode: String,
    pub stage_id: String,
    pub request_reboot: bool,
    pub now: String,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct ModeLeaseDecision {
    pub lease_id: String,
    pub current_mode: String,
    pub reboot_allowed: bool,
    pub stock_fastboot_restore_allowed: bool,
    pub release_ready: bool,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct ExecutionPermit {
    pub lease_id: String,
    pub physical_session_id: String,
    pub stage_id: String,
    pub partition: String,
    pub max_write_bytes: u64,
    pub requested_write_bytes: u64,
    pub reboot_allowed: bool,
    pub claimed_at: String,
}

pub struct LeaseGuard {
    connection: Connection,
}

impl LeaseGuard {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, LeaseGuardError> {
        let connection = Connection::open(path)?;
        Self::from_connection(connection)
    }

    pub fn in_memory() -> Result<Self, LeaseGuardError> {
        let connection = Connection::open_in_memory()?;
        Self::from_connection(connection)
    }

    fn from_connection(connection: Connection) -> Result<Self, LeaseGuardError> {
        connection.execute_batch(
            "PRAGMA foreign_keys = ON;
             CREATE TABLE IF NOT EXISTS execution_lease_claims (
               lease_id TEXT PRIMARY KEY,
               physical_session_id TEXT NOT NULL,
               stage_id TEXT NOT NULL,
               contract_sha256 TEXT NOT NULL,
               claimed_at TEXT NOT NULL
             );",
        )?;
        Ok(Self { connection })
    }

    pub fn authorize_mode(
        &self,
        lease: &Value,
        context: &ModeLeaseContext,
    ) -> Result<ModeLeaseDecision, LeaseGuardError> {
        validate_timestamp(&context.now)?;
        let validated = validate(
            lease,
            "mode_lease",
            "governance",
            context.physical_session_id.as_str(),
            &context.now,
            None,
            None,
        )?;
        let payload = payload(lease)?;
        let lease_id = string(payload, "lease_id")?;
        let mode = string(payload, "mode")?;
        if mode != context.current_mode {
            return Err(policy("MODE_MISMATCH"));
        }
        if payload
            .get("released_at")
            .is_some_and(|value| !value.is_null())
        {
            return Err(policy("MODE_LEASE_ALREADY_RELEASED"));
        }
        let reboot_allowed = boolean(payload, "reboot_allowed")?;
        let stock_fastboot_restore_allowed = boolean(payload, "stock_fastboot_restore_allowed")?;
        if context.request_reboot && !reboot_allowed {
            return Err(policy("REBOOT_BLOCKED_BY_ACTIVE_MODE_LEASE"));
        }
        if context.request_stock_fastboot_restore && !stock_fastboot_restore_allowed {
            return Err(policy(
                "STOCK_FASTBOOT_RESTORE_BLOCKED_BY_ACTIVE_MODE_LEASE",
            ));
        }
        let required = string_set(payload, "release_conditions")?;
        let release_ready = required.is_subset(&context.satisfied_release_conditions);
        let _ = validated;
        Ok(ModeLeaseDecision {
            lease_id,
            current_mode: context.current_mode.clone(),
            reboot_allowed,
            stock_fastboot_restore_allowed,
            release_ready,
        })
    }

    pub fn claim_execution(
        &mut self,
        lease: &Value,
        context: &ExecutionLeaseContext,
    ) -> Result<ExecutionPermit, LeaseGuardError> {
        validate_timestamp(&context.now)?;
        let mut expected_artifacts = context.artifact_hashes.clone();
        expected_artifacts.sort();
        expected_artifacts.dedup();
        if expected_artifacts != context.artifact_hashes {
            return Err(LeaseGuardError::InvalidContext(
                "artifact_hashes must be sorted and unique".to_owned(),
            ));
        }
        let validated = validate(
            lease,
            "execution_lease",
            "execution",
            context.physical_session_id.as_str(),
            &context.now,
            Some(context.recipe_hash.as_str()),
            Some(context.artifact_hashes.clone()),
        )?;
        let payload = payload(lease)?;
        let lease_id = string(payload, "lease_id")?;
        exact_string(
            payload,
            "recipe_hash",
            &context.recipe_hash,
            "RECIPE_HASH_MISMATCH",
        )?;
        exact_string(
            payload,
            "adapter_id",
            &context.adapter_id,
            "ADAPTER_ID_MISMATCH",
        )?;
        exact_string(
            payload,
            "adapter_version",
            &context.adapter_version,
            "ADAPTER_VERSION_MISMATCH",
        )?;
        exact_string(
            payload,
            "range_manifest_sha256",
            &context.range_manifest_sha256,
            "RANGE_MANIFEST_MISMATCH",
        )?;
        exact_string(payload, "stage_id", &context.stage_id, "STAGE_MISMATCH")?;
        exact_string(
            payload,
            "expected_mode",
            &context.current_mode,
            "MODE_MISMATCH",
        )?;

        let allowed_partitions = string_set(payload, "allowed_partitions")?;
        if !allowed_partitions.contains(&context.partition) {
            return Err(policy("PARTITION_NOT_AUTHORIZED"));
        }
        let max_write_bytes = integer_u64(payload, "max_write_bytes")?;
        if context.write_bytes == 0 || context.write_bytes > max_write_bytes {
            return Err(policy("WRITE_RANGE_EXCEEDS_LEASE"));
        }
        let reboot_allowed = boolean(payload, "reboot_allowed")?;
        if context.request_reboot && !reboot_allowed {
            return Err(policy("REBOOT_NOT_AUTHORIZED_BY_EXECUTION_LEASE"));
        }

        let contract_sha256 = validated.sha256.ok_or_else(|| {
            LeaseGuardError::Contract("validated lease has no canonical hash".to_owned())
        })?;
        let transaction = self.connection.transaction()?;
        let existing: Option<String> = transaction
            .query_row(
                "SELECT lease_id FROM execution_lease_claims WHERE lease_id = ?1",
                params![lease_id],
                |row| row.get(0),
            )
            .optional()?;
        if existing.is_some() {
            return Err(policy("EXECUTION_LEASE_ALREADY_CONSUMED"));
        }
        transaction.execute(
            "INSERT INTO execution_lease_claims
             (lease_id, physical_session_id, stage_id, contract_sha256, claimed_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                lease_id,
                context.physical_session_id,
                context.stage_id,
                contract_sha256,
                context.now,
            ],
        )?;
        transaction.commit()?;

        Ok(ExecutionPermit {
            lease_id,
            physical_session_id: context.physical_session_id.clone(),
            stage_id: context.stage_id.clone(),
            partition: context.partition.clone(),
            max_write_bytes,
            requested_write_bytes: context.write_bytes,
            reboot_allowed,
            claimed_at: context.now.clone(),
        })
    }

    pub fn is_execution_lease_consumed(&self, lease_id: &str) -> Result<bool, LeaseGuardError> {
        let existing: Option<String> = self
            .connection
            .query_row(
                "SELECT lease_id FROM execution_lease_claims WHERE lease_id = ?1",
                params![lease_id],
                |row| row.get(0),
            )
            .optional()?;
        Ok(existing.is_some())
    }
}

fn validate(
    lease: &Value,
    contract_type: &str,
    authority: &str,
    physical_session_id: &str,
    now: &str,
    recipe_hash: Option<&str>,
    artifact_hashes: Option<Vec<String>>,
) -> Result<techguy_contracts_core::ValidationResult, LeaseGuardError> {
    let registry = load_registry().map_err(|error| LeaseGuardError::Contract(error.to_string()))?;
    let context = ValidationContext {
        now: Some(now.to_owned()),
        expected_contract_type: Some(contract_type.to_owned()),
        expected_physical_session_id: Some(physical_session_id.to_owned()),
        expected_recipe_hash: recipe_hash.map(str::to_owned),
        expected_artifact_hashes: artifact_hashes,
        expected_authority: Some(authority.to_owned()),
        allow_consumed: false,
    };
    let result = validate_contract(lease, &context, &registry);
    if result.ok {
        Ok(result)
    } else {
        let codes = result
            .errors
            .iter()
            .map(|error| error.code.as_str())
            .collect::<Vec<_>>()
            .join(",");
        Err(LeaseGuardError::Contract(codes))
    }
}

fn payload(document: &Value) -> Result<&serde_json::Map<String, Value>, LeaseGuardError> {
    document
        .get("payload")
        .and_then(Value::as_object)
        .ok_or_else(|| LeaseGuardError::Contract("payload missing after validation".to_owned()))
}

fn string(payload: &serde_json::Map<String, Value>, name: &str) -> Result<String, LeaseGuardError> {
    payload
        .get(name)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| LeaseGuardError::Contract(format!("{name} is not a string")))
}

fn exact_string(
    payload: &serde_json::Map<String, Value>,
    name: &str,
    expected: &str,
    code: &str,
) -> Result<(), LeaseGuardError> {
    if string(payload, name)? == expected {
        Ok(())
    } else {
        Err(policy(code))
    }
}

fn boolean(payload: &serde_json::Map<String, Value>, name: &str) -> Result<bool, LeaseGuardError> {
    payload
        .get(name)
        .and_then(Value::as_bool)
        .ok_or_else(|| LeaseGuardError::Contract(format!("{name} is not a boolean")))
}

fn integer_u64(
    payload: &serde_json::Map<String, Value>,
    name: &str,
) -> Result<u64, LeaseGuardError> {
    payload
        .get(name)
        .and_then(Value::as_u64)
        .ok_or_else(|| LeaseGuardError::Contract(format!("{name} is not a positive integer")))
}

fn string_set(
    payload: &serde_json::Map<String, Value>,
    name: &str,
) -> Result<BTreeSet<String>, LeaseGuardError> {
    let values = payload
        .get(name)
        .and_then(Value::as_array)
        .ok_or_else(|| LeaseGuardError::Contract(format!("{name} is not an array")))?;
    values
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| LeaseGuardError::Contract(format!("{name} contains a non-string")))
        })
        .collect()
}

fn validate_timestamp(value: &str) -> Result<(), LeaseGuardError> {
    DateTime::parse_from_rfc3339(value)
        .map(|_| ())
        .map_err(|_| LeaseGuardError::InvalidContext("now must be RFC3339".to_owned()))
}

fn policy(code: &str) -> LeaseGuardError {
    LeaseGuardError::Policy(code.to_owned())
}

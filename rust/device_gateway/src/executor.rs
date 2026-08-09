use crate::{ExecutionLeaseContext, LeaseGuard, LeaseGuardError};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

#[derive(Debug)]
pub enum ExecutorError {
    Lease(LeaseGuardError),
    Policy(String),
    Adapter(String),
}

impl fmt::Display for ExecutorError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Lease(error) => write!(f, "lease rejected: {error}"),
            Self::Policy(message) => write!(f, "executor policy rejected: {message}"),
            Self::Adapter(message) => write!(f, "adapter failed: {message}"),
        }
    }
}

impl std::error::Error for ExecutorError {}

impl From<LeaseGuardError> for ExecutorError {
    fn from(value: LeaseGuardError) -> Self {
        Self::Lease(value)
    }
}

#[derive(Debug, Clone, Eq, PartialEq)]
pub struct BoundedStageRequest {
    pub physical_session_id: String,
    pub stage_id: String,
    pub partition: String,
    pub adapter_id: String,
    pub adapter_version: String,
    pub current_mode: String,
    pub range_manifest_sha256: String,
    pub payload: Vec<u8>,
    pub payload_sha256: String,
    pub backup_required: bool,
    pub readback_required: bool,
    pub exact_readback_required: bool,
    pub request_reboot: bool,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct RawAdapterResult {
    pub bytes_written: u64,
    pub backup_sha256: Option<String>,
    pub readback_sha256: Option<String>,
    pub adapter_code: String,
    pub adapter_message: String,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct ExecutorResult {
    pub lease_id: String,
    pub physical_session_id: String,
    pub stage_id: String,
    pub partition: String,
    pub adapter_id: String,
    pub adapter_version: String,
    pub payload_sha256: String,
    pub bytes_written: u64,
    pub backup_sha256: Option<String>,
    pub readback_sha256: Option<String>,
    pub adapter_code: String,
    pub adapter_message: String,
    pub verified: bool,
}

#[derive(Clone, Default)]
pub struct CancellationFlag {
    cancelled: Arc<AtomicBool>,
}

impl CancellationFlag {
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }
}

pub trait BoundedAdapter: Send {
    fn adapter_id(&self) -> &str;
    fn adapter_version(&self) -> &str;
    fn execute(
        &mut self,
        request: &BoundedStageRequest,
        cancellation: &CancellationFlag,
    ) -> Result<RawAdapterResult, String>;
}

pub struct BoundedExecutor {
    lease_guard: LeaseGuard,
    adapters: BTreeMap<(String, String), Box<dyn BoundedAdapter>>,
}

impl BoundedExecutor {
    pub fn new(lease_guard: LeaseGuard) -> Self {
        Self {
            lease_guard,
            adapters: BTreeMap::new(),
        }
    }

    pub fn register_adapter(
        &mut self,
        adapter: Box<dyn BoundedAdapter>,
    ) -> Result<(), ExecutorError> {
        let key = (
            adapter.adapter_id().to_owned(),
            adapter.adapter_version().to_owned(),
        );
        if key.0.trim().is_empty() || key.1.trim().is_empty() {
            return Err(policy("ADAPTER_IDENTITY_EMPTY"));
        }
        if self.adapters.contains_key(&key) {
            return Err(policy("ADAPTER_ALREADY_REGISTERED"));
        }
        self.adapters.insert(key, adapter);
        Ok(())
    }

    pub fn execute_authorized(
        &mut self,
        lease: &Value,
        lease_context: &ExecutionLeaseContext,
        request: &BoundedStageRequest,
        cancellation: &CancellationFlag,
    ) -> Result<ExecutorResult, ExecutorError> {
        if cancellation.is_cancelled() {
            return Err(policy("EXECUTION_CANCELLED_BEFORE_CLAIM"));
        }
        validate_request(lease_context, request)?;
        let payload_hash = sha256_hex(&request.payload);
        if payload_hash != request.payload_sha256 {
            return Err(policy("PAYLOAD_HASH_MISMATCH"));
        }
        if !lease_context
            .artifact_hashes
            .iter()
            .any(|hash| hash == &request.payload_sha256)
        {
            return Err(policy("PAYLOAD_NOT_AUTHORIZED_ARTIFACT"));
        }
        if request.payload.len() as u64 != lease_context.write_bytes {
            return Err(policy("PAYLOAD_SIZE_MISMATCH"));
        }

        let key = (request.adapter_id.clone(), request.adapter_version.clone());
        if !self.adapters.contains_key(&key) {
            return Err(policy("ADAPTER_NOT_REGISTERED"));
        }

        // The caller never supplies an ExecutionPermit. The executor owns the guard,
        // claims the exact lease internally and consumes the resulting permit here.
        let permit = self.lease_guard.claim_execution(lease, lease_context)?;
        if cancellation.is_cancelled() {
            return Err(policy("EXECUTION_CANCELLED_AFTER_CLAIM"));
        }

        let adapter = self
            .adapters
            .get_mut(&key)
            .ok_or_else(|| policy("ADAPTER_NOT_REGISTERED"))?;
        let raw = adapter
            .execute(request, cancellation)
            .map_err(ExecutorError::Adapter)?;

        if raw.bytes_written != permit.requested_write_bytes {
            return Err(policy("ADAPTER_WRITE_COUNT_MISMATCH"));
        }
        if request.backup_required && raw.backup_sha256.is_none() {
            return Err(policy("MANDATORY_BACKUP_MISSING"));
        }
        if request.readback_required && raw.readback_sha256.is_none() {
            return Err(policy("MANDATORY_READBACK_MISSING"));
        }
        if request.exact_readback_required
            && raw.readback_sha256.as_deref() != Some(request.payload_sha256.as_str())
        {
            return Err(policy("READBACK_HASH_MISMATCH"));
        }
        if cancellation.is_cancelled() {
            return Err(policy("EXECUTION_CANCELLED_DURING_ADAPTER"));
        }

        Ok(ExecutorResult {
            lease_id: permit.lease_id,
            physical_session_id: request.physical_session_id.clone(),
            stage_id: request.stage_id.clone(),
            partition: request.partition.clone(),
            adapter_id: request.adapter_id.clone(),
            adapter_version: request.adapter_version.clone(),
            payload_sha256: request.payload_sha256.clone(),
            bytes_written: raw.bytes_written,
            backup_sha256: raw.backup_sha256,
            readback_sha256: raw.readback_sha256,
            adapter_code: raw.adapter_code,
            adapter_message: raw.adapter_message,
            verified: true,
        })
    }
}

fn validate_request(
    lease_context: &ExecutionLeaseContext,
    request: &BoundedStageRequest,
) -> Result<(), ExecutorError> {
    exact(
        &request.physical_session_id,
        &lease_context.physical_session_id,
        "EXECUTOR_SESSION_MISMATCH",
    )?;
    exact(
        &request.stage_id,
        &lease_context.stage_id,
        "EXECUTOR_STAGE_MISMATCH",
    )?;
    exact(
        &request.partition,
        &lease_context.partition,
        "EXECUTOR_PARTITION_MISMATCH",
    )?;
    exact(
        &request.adapter_id,
        &lease_context.adapter_id,
        "EXECUTOR_ADAPTER_MISMATCH",
    )?;
    exact(
        &request.adapter_version,
        &lease_context.adapter_version,
        "EXECUTOR_ADAPTER_VERSION_MISMATCH",
    )?;
    exact(
        &request.current_mode,
        &lease_context.current_mode,
        "EXECUTOR_MODE_MISMATCH",
    )?;
    exact(
        &request.range_manifest_sha256,
        &lease_context.range_manifest_sha256,
        "EXECUTOR_RANGE_MISMATCH",
    )?;
    if request.request_reboot != lease_context.request_reboot {
        return Err(policy("EXECUTOR_REBOOT_REQUEST_MISMATCH"));
    }
    Ok(())
}

fn exact(actual: &str, expected: &str, code: &str) -> Result<(), ExecutorError> {
    if actual == expected {
        Ok(())
    } else {
        Err(policy(code))
    }
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut digest = Sha256::new();
    digest.update(bytes);
    format!("{:x}", digest.finalize())
}

fn policy(code: &str) -> ExecutorError {
    ExecutorError::Policy(code.to_owned())
}

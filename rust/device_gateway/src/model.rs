use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const GATEWAY_SCHEMA_VERSION: i64 = 1;
pub const DEVICE_AUTHORITY: &str = "none";
pub const XRAY_AUTHORITY: &str = "read_only";

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionState {
    Active,
    Closed,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OperationStage {
    Requested,
    EvidenceCollection,
    DecisionPending,
    AuthorizationPending,
    VerificationPending,
    Completed,
    Blocked,
    Failed,
    Cancelled,
}

impl OperationStage {
    pub fn is_terminal(self) -> bool {
        matches!(self, Self::Completed | Self::Failed | Self::Cancelled)
    }
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OperationStatus {
    Active,
    Recovering,
    Completed,
    Blocked,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DeviceAccess {
    None,
    ReadOnly,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum WorkerStatus {
    Ready,
    Running,
    TimedOut,
    Stopped,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GatewayEventKind {
    GatewayStarted,
    GatewayRecovered,
    PhysicalSessionOpened,
    PhysicalSessionClosed,
    EndpointObserved,
    OperationOpened,
    OperationTransitioned,
    OperationResumed,
    ProviderRegistered,
    ContractAccepted,
    WorkerRegistered,
    WorkerHeartbeat,
    WorkerTimedOut,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct PhysicalDeviceSession {
    pub session_id: String,
    pub fingerprint_sha256: String,
    pub state: SessionState,
    pub created_at: String,
    pub updated_at: String,
    pub recovery_count: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EndpointObservationRecord {
    pub observation_id: String,
    pub session_id: String,
    pub endpoint_key: String,
    pub mode: String,
    pub transport: String,
    pub observed_at: String,
    pub payload: Value,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct OperationSession {
    pub operation_id: String,
    pub physical_session_id: String,
    pub request_sha256: String,
    pub stage: OperationStage,
    pub status: OperationStatus,
    pub created_at: String,
    pub updated_at: String,
    pub recovery_count: u64,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProviderManifest {
    pub component_id: String,
    pub version: String,
    pub device_access: DeviceAccess,
    pub contract_authorities: Vec<String>,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct WorkerRecord {
    pub worker_id: String,
    pub provider_id: String,
    pub capabilities: Vec<String>,
    pub status: WorkerStatus,
    pub last_heartbeat_at: String,
    pub deadline_at: String,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GatewayEvent {
    pub sequence: i64,
    pub event_id: String,
    pub event_type: GatewayEventKind,
    pub producer: String,
    pub physical_session_id: Option<String>,
    pub operation_id: Option<String>,
    pub timestamp: String,
    pub payload: Value,
    pub previous_hash: Option<String>,
    pub event_hash: String,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct RecoverySummary {
    pub physical_sessions: Vec<String>,
    pub operation_sessions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContractIngressReceipt {
    pub contract_type: String,
    pub contract_sha256: String,
    pub event: GatewayEvent,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct DoctorReport {
    pub healthy: bool,
    pub schema_version: i64,
    pub journal_valid: bool,
    pub active_physical_sessions: u64,
    pub active_operation_sessions: u64,
    pub recovering_operation_sessions: u64,
    pub registered_providers: u64,
    pub timed_out_workers: u64,
    pub device_authority: String,
    pub xray_authority: String,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GatewaySnapshot {
    pub schema_version: i64,
    pub physical_sessions: Vec<PhysicalDeviceSession>,
    pub operation_sessions: Vec<OperationSession>,
    pub providers: Vec<ProviderManifest>,
    pub workers: Vec<WorkerRecord>,
    pub last_event_sequence: i64,
    pub device_authority: String,
    pub xray_authority: String,
}

#[derive(Debug, Clone, Eq, PartialEq, Serialize, Deserialize)]
pub struct GatewayHealth {
    pub status: String,
    pub schema_version: i64,
    pub device_authority: String,
    pub xray_authority: String,
}

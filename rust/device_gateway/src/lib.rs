mod error;
mod gateway;
mod model;
mod policy;
mod protocol;
mod server;
mod storage;

pub use error::GatewayError;
pub use gateway::{now_utc, Gateway};
pub use model::{
    ContractIngressReceipt, DeviceAccess, DoctorReport, EndpointObservationRecord, GatewayEvent,
    GatewayEventKind, GatewayHealth, GatewaySnapshot, OperationSession, OperationStage,
    OperationStatus, PhysicalDeviceSession, ProviderManifest, RecoverySummary, SessionState,
    WorkerRecord, WorkerStatus, DEVICE_AUTHORITY, GATEWAY_SCHEMA_VERSION, XRAY_AUTHORITY,
};
pub use protocol::{dispatch, GatewayCommand, GatewayRequest, GatewayResponse, ProtocolError};
pub use server::run_listener;

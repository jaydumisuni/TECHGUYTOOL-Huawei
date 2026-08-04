use crate::error::GatewayError;
use crate::gateway::Gateway;
use crate::model::{OperationStage, ProviderManifest};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use techguy_contracts_core::ValidationContext;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GatewayRequest {
    pub request_id: String,
    pub command: GatewayCommand,
}

#[derive(Debug, Deserialize)]
#[serde(
    tag = "name",
    content = "params",
    rename_all = "snake_case",
    deny_unknown_fields
)]
pub enum GatewayCommand {
    Health,
    Doctor,
    Snapshot,
    OpenPhysicalSession {
        fingerprint_sha256: String,
    },
    GetPhysicalSession {
        session_id: String,
    },
    ClosePhysicalSession {
        session_id: String,
    },
    RecordEndpoint {
        session_id: String,
        endpoint_key: String,
        mode: String,
        transport: String,
        #[serde(default)]
        payload: Value,
    },
    OpenOperation {
        physical_session_id: String,
        request_sha256: String,
    },
    GetOperation {
        operation_id: String,
    },
    TransitionOperation {
        operation_id: String,
        stage: OperationStage,
    },
    ResumeOperation {
        operation_id: String,
    },
    RegisterProvider {
        manifest: ProviderManifest,
    },
    PublishContract {
        component_id: String,
        contract: Value,
        #[serde(default)]
        context: ValidationContext,
    },
    RegisterWorker {
        worker_id: String,
        provider_id: String,
        capabilities: Vec<String>,
        deadline_at: String,
    },
    HeartbeatWorker {
        worker_id: String,
        deadline_at: String,
    },
    SweepWorkers,
    ListEvents {
        #[serde(default)]
        after_sequence: i64,
        #[serde(default = "default_event_limit")]
        limit: u32,
    },
    VerifyJournal,
    Shutdown,
}

impl GatewayCommand {
    pub fn is_shutdown(&self) -> bool {
        matches!(self, Self::Shutdown)
    }
}

#[derive(Debug, Serialize)]
pub struct GatewayResponse {
    pub request_id: String,
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<ProtocolError>,
}

#[derive(Debug, Serialize)]
pub struct ProtocolError {
    pub code: String,
    pub message: String,
}

impl GatewayResponse {
    pub fn success(request_id: String, result: Value) -> Self {
        Self {
            request_id,
            ok: true,
            result: Some(result),
            error: None,
        }
    }

    pub fn failure(request_id: String, error: &GatewayError) -> Self {
        Self {
            request_id,
            ok: false,
            result: None,
            error: Some(ProtocolError {
                code: error.code().to_owned(),
                message: error.to_string(),
            }),
        }
    }
}

pub fn dispatch(gateway: &Gateway, request: GatewayRequest) -> GatewayResponse {
    let request_id = request.request_id;
    if request_id.is_empty() || request_id.len() > 128 {
        return GatewayResponse::failure(
            request_id,
            &GatewayError::Protocol("request_id must contain 1 to 128 characters".to_owned()),
        );
    }
    let result = dispatch_command(gateway, request.command);
    match result {
        Ok(value) => GatewayResponse::success(request_id, value),
        Err(error) => GatewayResponse::failure(request_id, &error),
    }
}

fn dispatch_command(gateway: &Gateway, command: GatewayCommand) -> Result<Value, GatewayError> {
    match command {
        GatewayCommand::Health => Ok(serde_json::to_value(gateway.health())?),
        GatewayCommand::Doctor => Ok(serde_json::to_value(gateway.doctor()?)?),
        GatewayCommand::Snapshot => Ok(serde_json::to_value(gateway.snapshot()?)?),
        GatewayCommand::OpenPhysicalSession { fingerprint_sha256 } => Ok(serde_json::to_value(
            gateway.open_physical_session(&fingerprint_sha256)?,
        )?),
        GatewayCommand::GetPhysicalSession { session_id } => Ok(serde_json::to_value(
            gateway.get_physical_session(&session_id)?,
        )?),
        GatewayCommand::ClosePhysicalSession { session_id } => Ok(serde_json::to_value(
            gateway.close_physical_session(&session_id)?,
        )?),
        GatewayCommand::RecordEndpoint {
            session_id,
            endpoint_key,
            mode,
            transport,
            payload,
        } => Ok(serde_json::to_value(gateway.record_endpoint(
            &session_id,
            &endpoint_key,
            &mode,
            &transport,
            payload,
        )?)?),
        GatewayCommand::OpenOperation {
            physical_session_id,
            request_sha256,
        } => Ok(serde_json::to_value(
            gateway.open_operation(&physical_session_id, &request_sha256)?,
        )?),
        GatewayCommand::GetOperation { operation_id } => {
            Ok(serde_json::to_value(gateway.get_operation(&operation_id)?)?)
        }
        GatewayCommand::TransitionOperation {
            operation_id,
            stage,
        } => Ok(serde_json::to_value(
            gateway.transition_operation(&operation_id, stage)?,
        )?),
        GatewayCommand::ResumeOperation { operation_id } => Ok(serde_json::to_value(
            gateway.resume_operation(&operation_id)?,
        )?),
        GatewayCommand::RegisterProvider { manifest } => {
            Ok(serde_json::to_value(gateway.register_provider(manifest)?)?)
        }
        GatewayCommand::PublishContract {
            component_id,
            contract,
            context,
        } => Ok(serde_json::to_value(gateway.publish_contract(
            &component_id,
            &contract,
            &context,
        )?)?),
        GatewayCommand::RegisterWorker {
            worker_id,
            provider_id,
            capabilities,
            deadline_at,
        } => Ok(serde_json::to_value(gateway.register_worker(
            &worker_id,
            &provider_id,
            &capabilities,
            &deadline_at,
        )?)?),
        GatewayCommand::HeartbeatWorker {
            worker_id,
            deadline_at,
        } => Ok(serde_json::to_value(
            gateway.heartbeat_worker(&worker_id, &deadline_at)?,
        )?),
        GatewayCommand::SweepWorkers => Ok(serde_json::to_value(gateway.sweep_workers()?)?),
        GatewayCommand::ListEvents {
            after_sequence,
            limit,
        } => Ok(serde_json::to_value(
            gateway.list_events(after_sequence, limit)?,
        )?),
        GatewayCommand::VerifyJournal => {
            gateway.verify_journal()?;
            Ok(json!({"journal_valid": true}))
        }
        GatewayCommand::Shutdown => Ok(json!({"shutdown": true})),
    }
}

fn default_event_limit() -> u32 {
    100
}

use crate::error::GatewayError;
use crate::model::{
    ContractIngressReceipt, DoctorReport, EndpointObservationRecord, GatewayEvent,
    GatewayEventKind, GatewayHealth, GatewaySnapshot, OperationSession, OperationStage,
    PhysicalDeviceSession, ProviderManifest, RecoverySummary, WorkerRecord, DEVICE_AUTHORITY,
    GATEWAY_SCHEMA_VERSION, XRAY_AUTHORITY,
};
use crate::policy::{
    ensure_provider_authority, ensure_worker_capabilities, validate_provider_manifest,
    validate_worker_deadline,
};
use crate::storage::Storage;
use chrono::{SecondsFormat, Utc};
use serde_json::{json, Value};
use std::path::Path;
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use techguy_contracts_core::{load_registry, validate_contract_json, Registry, ValidationContext};

#[derive(Clone, Debug)]
pub struct Gateway {
    storage: Storage,
    registry: Registry,
    subscribers: Arc<Mutex<Vec<Sender<GatewayEvent>>>>,
}

impl Gateway {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, GatewayError> {
        let gateway = Self::build(path)?;
        gateway.storage.verify_journal()?;
        let now = now_utc();
        let (_recovered, recovery_event) = gateway.storage.recover_on_start(&now)?;
        if let Some(event) = recovery_event {
            gateway.notify_event(&event);
        }
        gateway.publish_internal(
            GatewayEventKind::GatewayStarted,
            None,
            None,
            json!({
                "database": gateway.storage.path().display().to_string(),
                "schema_version": GATEWAY_SCHEMA_VERSION
            }),
            &now,
        )?;
        Ok(gateway)
    }

    pub fn inspect(path: impl AsRef<Path>) -> Result<Self, GatewayError> {
        Self::build(path)
    }

    fn build(path: impl AsRef<Path>) -> Result<Self, GatewayError> {
        let storage = Storage::open(path)?;
        let registry = load_registry().map_err(|error| {
            GatewayError::Storage(format!("contract registry is unavailable: {error}"))
        })?;
        Ok(Self {
            storage,
            registry,
            subscribers: Arc::new(Mutex::new(Vec::new())),
        })
    }

    pub fn health(&self) -> GatewayHealth {
        GatewayHealth {
            status: "ready".to_owned(),
            schema_version: GATEWAY_SCHEMA_VERSION,
            device_authority: DEVICE_AUTHORITY.to_owned(),
            xray_authority: XRAY_AUTHORITY.to_owned(),
        }
    }

    pub fn recovery_state(&self) -> Result<RecoverySummary, GatewayError> {
        let snapshot = self.snapshot()?;
        Ok(RecoverySummary {
            physical_sessions: snapshot
                .physical_sessions
                .into_iter()
                .filter(|session| session.recovery_count > 0)
                .map(|session| session.session_id)
                .collect(),
            operation_sessions: snapshot
                .operation_sessions
                .into_iter()
                .filter(|operation| operation.recovery_count > 0)
                .map(|operation| operation.operation_id)
                .collect(),
        })
    }

    pub fn subscribe(&self) -> Receiver<GatewayEvent> {
        let (sender, receiver) = mpsc::channel();
        let mut subscribers = match self.subscribers.lock() {
            Ok(subscribers) => subscribers,
            Err(poisoned) => poisoned.into_inner(),
        };
        subscribers.push(sender);
        receiver
    }

    pub fn open_physical_session(
        &self,
        fingerprint_sha256: &str,
    ) -> Result<PhysicalDeviceSession, GatewayError> {
        let now = now_utc();
        let (session, event) = self
            .storage
            .open_physical_session(fingerprint_sha256, &now)?;
        self.notify_event(&event);
        Ok(session)
    }

    pub fn get_physical_session(
        &self,
        session_id: &str,
    ) -> Result<PhysicalDeviceSession, GatewayError> {
        self.storage.get_physical_session(session_id)
    }

    pub fn close_physical_session(
        &self,
        session_id: &str,
    ) -> Result<PhysicalDeviceSession, GatewayError> {
        let now = now_utc();
        let (session, event) = self.storage.close_physical_session(session_id, &now)?;
        self.notify_event(&event);
        Ok(session)
    }

    pub fn record_endpoint(
        &self,
        session_id: &str,
        endpoint_key: &str,
        mode: &str,
        transport: &str,
        payload: Value,
    ) -> Result<EndpointObservationRecord, GatewayError> {
        let now = now_utc();
        let (observation, event) = self.storage.record_endpoint(
            session_id,
            endpoint_key,
            mode,
            transport,
            payload,
            &now,
        )?;
        self.notify_event(&event);
        Ok(observation)
    }

    pub fn open_operation(
        &self,
        physical_session_id: &str,
        request_sha256: &str,
    ) -> Result<OperationSession, GatewayError> {
        let now = now_utc();
        let (operation, event) =
            self.storage
                .open_operation(physical_session_id, request_sha256, &now)?;
        self.notify_event(&event);
        Ok(operation)
    }

    pub fn get_operation(&self, operation_id: &str) -> Result<OperationSession, GatewayError> {
        self.storage.get_operation(operation_id)
    }

    pub fn transition_operation(
        &self,
        operation_id: &str,
        next: OperationStage,
    ) -> Result<OperationSession, GatewayError> {
        let now = now_utc();
        let (_previous_stage, operation, event) = self
            .storage
            .transition_operation(operation_id, next, &now)?;
        if let Some(event) = event {
            self.notify_event(&event);
        }
        Ok(operation)
    }

    pub fn resume_operation(&self, operation_id: &str) -> Result<OperationSession, GatewayError> {
        let now = now_utc();
        let (operation, event) = self.storage.resume_operation(operation_id, &now)?;
        self.notify_event(&event);
        Ok(operation)
    }

    pub fn register_provider(
        &self,
        manifest: ProviderManifest,
    ) -> Result<ProviderManifest, GatewayError> {
        validate_provider_manifest(&manifest)?;
        let now = now_utc();
        let (registered, event) = self.storage.register_provider(&manifest, &now)?;
        if let Some(event) = event {
            self.notify_event(&event);
        }
        Ok(registered)
    }

    pub fn publish_contract(
        &self,
        component_id: &str,
        contract: &Value,
        context: &ValidationContext,
    ) -> Result<ContractIngressReceipt, GatewayError> {
        let provider = self.storage.get_provider(component_id)?;
        let document = serde_json::to_string(contract)?;
        let result = validate_contract_json(&document, context, &self.registry);
        if !result.ok {
            return Err(GatewayError::ContractRejected(serde_json::to_string(
                &result.errors,
            )?));
        }
        let producer = contract
            .get("producer")
            .and_then(Value::as_str)
            .ok_or_else(|| GatewayError::InvalidInput("contract producer is missing".to_owned()))?;
        if producer != component_id {
            return Err(GatewayError::PolicyDenied(format!(
                "contract producer {producer:?} does not match provider {component_id:?}"
            )));
        }
        let authority = contract
            .get("authority")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                GatewayError::InvalidInput("contract authority is missing".to_owned())
            })?;
        ensure_provider_authority(&provider, authority)?;
        if let Some(session_id) = contract.get("physical_session_id").and_then(Value::as_str) {
            self.storage.get_physical_session(session_id)?;
        }
        let contract_type = contract
            .get("contract_type")
            .and_then(Value::as_str)
            .ok_or_else(|| GatewayError::InvalidInput("contract type is missing".to_owned()))?
            .to_owned();
        let contract_sha256 = result.sha256.ok_or_else(|| {
            GatewayError::ContractRejected("validated contract has no SHA-256".to_owned())
        })?;
        let now = now_utc();
        let event = self.publish_internal(
            GatewayEventKind::ContractAccepted,
            contract.get("physical_session_id").and_then(Value::as_str),
            None,
            json!({
                "canonical": result.canonical,
                "contract_sha256": contract_sha256.clone(),
                "contract_type": contract_type.clone()
            }),
            &now,
        )?;
        Ok(ContractIngressReceipt {
            contract_type,
            contract_sha256,
            event,
        })
    }

    pub fn register_worker(
        &self,
        worker_id: &str,
        provider_id: &str,
        capabilities: &[String],
        deadline_at: &str,
    ) -> Result<WorkerRecord, GatewayError> {
        ensure_worker_capabilities(capabilities)?;
        let provider = self.storage.get_provider(provider_id)?;
        for capability in capabilities {
            if !provider
                .capabilities
                .iter()
                .any(|allowed| allowed == capability)
            {
                return Err(GatewayError::PolicyDenied(format!(
                    "worker capability {capability:?} exceeds provider {:?}",
                    provider.component_id
                )));
            }
        }
        let now = now_utc();
        validate_worker_deadline(&now, deadline_at)?;
        let (worker, event) = self.storage.register_worker(
            worker_id,
            provider_id,
            capabilities,
            deadline_at,
            &now,
        )?;
        self.notify_event(&event);
        Ok(worker)
    }

    pub fn heartbeat_worker(
        &self,
        worker_id: &str,
        deadline_at: &str,
    ) -> Result<WorkerRecord, GatewayError> {
        let now = now_utc();
        validate_worker_deadline(&now, deadline_at)?;
        let (worker, event) = self
            .storage
            .heartbeat_worker(worker_id, deadline_at, &now)?;
        self.notify_event(&event);
        Ok(worker)
    }

    pub fn sweep_workers(&self) -> Result<Vec<WorkerRecord>, GatewayError> {
        let now = now_utc();
        let results = self.storage.sweep_workers(&now)?;
        let mut workers = Vec::with_capacity(results.len());
        for (worker, event) in results {
            self.notify_event(&event);
            workers.push(worker);
        }
        Ok(workers)
    }

    pub fn list_events(
        &self,
        after_sequence: i64,
        limit: u32,
    ) -> Result<Vec<GatewayEvent>, GatewayError> {
        self.storage.list_events(after_sequence, limit)
    }

    pub fn verify_journal(&self) -> Result<(), GatewayError> {
        self.storage.verify_journal()
    }

    pub fn doctor(&self) -> Result<DoctorReport, GatewayError> {
        self.storage.doctor()
    }

    pub fn snapshot(&self) -> Result<GatewaySnapshot, GatewayError> {
        self.storage.snapshot()
    }

    fn publish_internal(
        &self,
        event_type: GatewayEventKind,
        physical_session_id: Option<&str>,
        operation_id: Option<&str>,
        payload: Value,
        timestamp: &str,
    ) -> Result<GatewayEvent, GatewayError> {
        let event = self.storage.append_event(
            event_type,
            "ttg.device-gateway",
            physical_session_id,
            operation_id,
            payload,
            timestamp,
        )?;
        self.notify_event(&event);
        Ok(event)
    }

    fn notify_event(&self, event: &GatewayEvent) {
        let mut subscribers = match self.subscribers.lock() {
            Ok(subscribers) => subscribers,
            Err(poisoned) => poisoned.into_inner(),
        };
        subscribers.retain(|sender| sender.send(event.clone()).is_ok());
    }
}

pub fn now_utc() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, true)
}

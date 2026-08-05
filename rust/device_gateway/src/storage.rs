use crate::error::GatewayError;
use crate::model::{
    DoctorReport, EndpointObservationRecord, GatewayEvent, GatewayEventKind, GatewaySnapshot,
    OperationSession, OperationStage, OperationStatus, PhysicalDeviceSession, ProviderManifest,
    RecoverySummary, SessionState, WorkerRecord, WorkerStatus, DEVICE_AUTHORITY,
    GATEWAY_SCHEMA_VERSION, XRAY_AUTHORITY,
};
use crate::policy::{ensure_stage_transition, parse_timestamp, validate_sha256};
use rusqlite::{params, Connection, OptionalExtension, Transaction, TransactionBehavior};
use serde::de::DeserializeOwned;
use serde::Serialize;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use techguy_contracts_core::canonical_sha256;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct Storage {
    path: PathBuf,
}

impl Storage {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, GatewayError> {
        let path = path.as_ref().to_path_buf();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let storage = Self { path };
        storage.initialize()?;
        Ok(storage)
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    fn connect(&self) -> Result<Connection, GatewayError> {
        let connection = Connection::open(&self.path)?;
        connection.pragma_update(None, "foreign_keys", "ON")?;
        connection.busy_timeout(std::time::Duration::from_secs(5))?;
        Ok(connection)
    }

    fn initialize(&self) -> Result<(), GatewayError> {
        let connection = self.connect()?;
        connection.execute_batch(
            "PRAGMA journal_mode=WAL;
             CREATE TABLE IF NOT EXISTS gateway_meta (
                 key TEXT PRIMARY KEY,
                 value TEXT NOT NULL
             );
             CREATE TABLE IF NOT EXISTS physical_sessions (
                 session_id TEXT PRIMARY KEY,
                 fingerprint_sha256 TEXT NOT NULL,
                 state TEXT NOT NULL,
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL,
                 recovery_count INTEGER NOT NULL DEFAULT 0
             );
             CREATE TABLE IF NOT EXISTS endpoint_observations (
                 observation_id TEXT PRIMARY KEY,
                 session_id TEXT NOT NULL REFERENCES physical_sessions(session_id),
                 endpoint_key TEXT NOT NULL,
                 mode TEXT NOT NULL,
                 transport TEXT NOT NULL,
                 observed_at TEXT NOT NULL,
                 payload_json TEXT NOT NULL
             );
             CREATE INDEX IF NOT EXISTS endpoint_observations_session_idx
                 ON endpoint_observations(session_id, observed_at);
             CREATE TABLE IF NOT EXISTS operation_sessions (
                 operation_id TEXT PRIMARY KEY,
                 physical_session_id TEXT NOT NULL REFERENCES physical_sessions(session_id),
                 request_sha256 TEXT NOT NULL,
                 stage TEXT NOT NULL,
                 status TEXT NOT NULL,
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL,
                 recovery_count INTEGER NOT NULL DEFAULT 0
             );
             CREATE INDEX IF NOT EXISTS operation_sessions_physical_idx
                 ON operation_sessions(physical_session_id, updated_at);
             CREATE TABLE IF NOT EXISTS providers (
                 component_id TEXT PRIMARY KEY,
                 manifest_json TEXT NOT NULL,
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL
             );
             CREATE TABLE IF NOT EXISTS workers (
                 worker_id TEXT PRIMARY KEY,
                 provider_id TEXT NOT NULL REFERENCES providers(component_id),
                 capabilities_json TEXT NOT NULL,
                 status TEXT NOT NULL,
                 last_heartbeat_at TEXT NOT NULL,
                 deadline_at TEXT NOT NULL,
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL
             );
             CREATE INDEX IF NOT EXISTS workers_deadline_idx
                 ON workers(status, deadline_at);
             CREATE TABLE IF NOT EXISTS journal_events (
                 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                 event_id TEXT NOT NULL UNIQUE,
                 event_type TEXT NOT NULL,
                 producer TEXT NOT NULL,
                 physical_session_id TEXT,
                 operation_id TEXT,
                 timestamp TEXT NOT NULL,
                 payload_json TEXT NOT NULL,
                 previous_hash TEXT,
                 event_hash TEXT NOT NULL UNIQUE
             );",
        )?;
        connection.execute(
            "INSERT INTO gateway_meta(key, value) VALUES('schema_version', ?1)
             ON CONFLICT(key) DO NOTHING",
            params![GATEWAY_SCHEMA_VERSION.to_string()],
        )?;
        let version: String = connection.query_row(
            "SELECT value FROM gateway_meta WHERE key = 'schema_version'",
            [],
            |row| row.get(0),
        )?;
        if version != GATEWAY_SCHEMA_VERSION.to_string() {
            return Err(GatewayError::Storage(format!(
                "unsupported gateway database schema version {version:?}"
            )));
        }
        Ok(())
    }

    pub fn recover_on_start(
        &self,
        now: &str,
    ) -> Result<(RecoverySummary, Option<GatewayEvent>), GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let physical_sessions = query_strings(
            &transaction,
            "SELECT session_id FROM physical_sessions WHERE state = 'active' ORDER BY session_id",
        )?;
        let operation_sessions = query_strings(
            &transaction,
            "SELECT operation_id FROM operation_sessions
             WHERE status IN ('active', 'recovering') ORDER BY operation_id",
        )?;
        transaction.execute(
            "UPDATE physical_sessions
             SET recovery_count = recovery_count + 1, updated_at = ?1
             WHERE state = 'active'",
            params![now],
        )?;
        transaction.execute(
            "UPDATE operation_sessions
             SET recovery_count = recovery_count + 1, status = 'recovering', updated_at = ?1
             WHERE status IN ('active', 'recovering')",
            params![now],
        )?;
        let summary = RecoverySummary {
            physical_sessions,
            operation_sessions,
        };
        let event = if summary.physical_sessions.is_empty() && summary.operation_sessions.is_empty()
        {
            None
        } else {
            Some(append_event_in_transaction(
                &transaction,
                GatewayEventKind::GatewayRecovered,
                "ttg.device-gateway",
                None,
                None,
                serde_json::to_value(&summary)?,
                now,
            )?)
        };
        transaction.commit()?;
        Ok((summary, event))
    }

    pub fn open_physical_session(
        &self,
        fingerprint_sha256: &str,
        now: &str,
    ) -> Result<(PhysicalDeviceSession, GatewayEvent), GatewayError> {
        validate_sha256(fingerprint_sha256, "fingerprint_sha256")?;
        let session = PhysicalDeviceSession {
            session_id: Uuid::new_v4().to_string(),
            fingerprint_sha256: fingerprint_sha256.to_owned(),
            state: SessionState::Active,
            created_at: now.to_owned(),
            updated_at: now.to_owned(),
            recovery_count: 0,
        };
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        transaction.execute(
            "INSERT INTO physical_sessions(
                session_id, fingerprint_sha256, state, created_at, updated_at, recovery_count
             ) VALUES(?1, ?2, ?3, ?4, ?5, 0)",
            params![
                session.session_id,
                session.fingerprint_sha256,
                encode_enum(session.state)?,
                session.created_at,
                session.updated_at
            ],
        )?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::PhysicalSessionOpened,
            "ttg.device-gateway",
            Some(&session.session_id),
            None,
            json!({"fingerprint_sha256": session.fingerprint_sha256.clone()}),
            now,
        )?;
        transaction.commit()?;
        Ok((session, event))
    }

    pub fn get_physical_session(
        &self,
        session_id: &str,
    ) -> Result<PhysicalDeviceSession, GatewayError> {
        let connection = self.connect()?;
        get_physical_session_on(&connection, session_id)
    }

    pub fn list_physical_sessions(&self) -> Result<Vec<PhysicalDeviceSession>, GatewayError> {
        let connection = self.connect()?;
        list_physical_sessions_on(&connection)
    }

    pub fn close_physical_session(
        &self,
        session_id: &str,
        now: &str,
    ) -> Result<(PhysicalDeviceSession, GatewayEvent), GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let updated = transaction.execute(
            "UPDATE physical_sessions SET state = 'closed', updated_at = ?2
             WHERE session_id = ?1 AND state = 'active'",
            params![session_id, now],
        )?;
        if updated == 0 {
            return Err(GatewayError::Conflict(format!(
                "physical session {session_id:?} is missing or already closed"
            )));
        }
        let session = get_physical_session_on(&transaction, session_id)?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::PhysicalSessionClosed,
            "ttg.device-gateway",
            Some(session_id),
            None,
            json!({}),
            now,
        )?;
        transaction.commit()?;
        Ok((session, event))
    }

    pub fn record_endpoint(
        &self,
        session_id: &str,
        endpoint_key: &str,
        mode: &str,
        transport: &str,
        payload: Value,
        now: &str,
    ) -> Result<(EndpointObservationRecord, GatewayEvent), GatewayError> {
        if endpoint_key.is_empty() || mode.is_empty() || transport.is_empty() {
            return Err(GatewayError::InvalidInput(
                "endpoint_key, mode, and transport must be non-empty".to_owned(),
            ));
        }
        let observation = EndpointObservationRecord {
            observation_id: Uuid::new_v4().to_string(),
            session_id: session_id.to_owned(),
            endpoint_key: endpoint_key.to_owned(),
            mode: mode.to_owned(),
            transport: transport.to_owned(),
            observed_at: now.to_owned(),
            payload,
        };
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let touched = transaction.execute(
            "UPDATE physical_sessions SET updated_at = ?2
             WHERE session_id = ?1 AND state = 'active'",
            params![session_id, now],
        )?;
        if touched == 0 {
            return Err(GatewayError::Conflict(
                "endpoint observations require an active physical session".to_owned(),
            ));
        }
        transaction.execute(
            "INSERT INTO endpoint_observations(
                observation_id, session_id, endpoint_key, mode, transport, observed_at, payload_json
             ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                observation.observation_id,
                observation.session_id,
                observation.endpoint_key,
                observation.mode,
                observation.transport,
                observation.observed_at,
                serde_json::to_string(&observation.payload)?
            ],
        )?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::EndpointObserved,
            "ttg.device-gateway",
            Some(session_id),
            None,
            serde_json::to_value(&observation)?,
            now,
        )?;
        transaction.commit()?;
        Ok((observation, event))
    }

    pub fn open_operation(
        &self,
        physical_session_id: &str,
        request_sha256: &str,
        now: &str,
    ) -> Result<(OperationSession, GatewayEvent), GatewayError> {
        validate_sha256(request_sha256, "request_sha256")?;
        let operation = OperationSession {
            operation_id: Uuid::new_v4().to_string(),
            physical_session_id: physical_session_id.to_owned(),
            request_sha256: request_sha256.to_owned(),
            stage: OperationStage::Requested,
            status: OperationStatus::Active,
            created_at: now.to_owned(),
            updated_at: now.to_owned(),
            recovery_count: 0,
        };
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let active: Option<i64> = transaction
            .query_row(
                "SELECT 1 FROM physical_sessions WHERE session_id = ?1 AND state = 'active'",
                params![physical_session_id],
                |row| row.get(0),
            )
            .optional()?;
        if active.is_none() {
            return Err(GatewayError::Conflict(
                "operation requires an active physical session".to_owned(),
            ));
        }
        transaction.execute(
            "INSERT INTO operation_sessions(
                operation_id, physical_session_id, request_sha256, stage, status,
                created_at, updated_at, recovery_count
             ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, 0)",
            params![
                operation.operation_id,
                operation.physical_session_id,
                operation.request_sha256,
                encode_enum(operation.stage)?,
                encode_enum(operation.status)?,
                operation.created_at,
                operation.updated_at
            ],
        )?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::OperationOpened,
            "ttg.device-gateway",
            Some(physical_session_id),
            Some(&operation.operation_id),
            serde_json::to_value(&operation)?,
            now,
        )?;
        transaction.commit()?;
        Ok((operation, event))
    }

    pub fn get_operation(&self, operation_id: &str) -> Result<OperationSession, GatewayError> {
        let connection = self.connect()?;
        get_operation_on(&connection, operation_id)
    }

    pub fn list_operations(&self) -> Result<Vec<OperationSession>, GatewayError> {
        let connection = self.connect()?;
        list_operations_on(&connection)
    }

    pub fn transition_operation(
        &self,
        operation_id: &str,
        next: OperationStage,
        now: &str,
    ) -> Result<(OperationStage, OperationSession, Option<GatewayEvent>), GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let current = get_operation_on(&transaction, operation_id)?;
        ensure_stage_transition(current.stage, next)?;
        if current.stage == next {
            transaction.commit()?;
            return Ok((current.stage, current, None));
        }
        let status = match next {
            OperationStage::Completed => OperationStatus::Completed,
            OperationStage::Blocked => OperationStatus::Blocked,
            OperationStage::Failed => OperationStatus::Failed,
            OperationStage::Cancelled => OperationStatus::Cancelled,
            _ => OperationStatus::Active,
        };
        let current_stage = encode_enum(current.stage)?;
        let updated = transaction.execute(
            "UPDATE operation_sessions SET stage = ?2, status = ?3, updated_at = ?4
             WHERE operation_id = ?1 AND stage = ?5",
            params![
                operation_id,
                encode_enum(next)?,
                encode_enum(status)?,
                now,
                current_stage
            ],
        )?;
        if updated == 0 {
            return Err(GatewayError::Conflict(format!(
                "operation {operation_id:?} changed before the transition committed"
            )));
        }
        let operation = get_operation_on(&transaction, operation_id)?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::OperationTransitioned,
            "ttg.device-gateway",
            Some(&operation.physical_session_id),
            Some(operation_id),
            json!({
                "from": current.stage,
                "status": operation.status,
                "to": operation.stage
            }),
            now,
        )?;
        transaction.commit()?;
        Ok((current.stage, operation, Some(event)))
    }

    pub fn resume_operation(
        &self,
        operation_id: &str,
        now: &str,
    ) -> Result<(OperationSession, GatewayEvent), GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let updated = transaction.execute(
            "UPDATE operation_sessions SET status = 'active', updated_at = ?2
             WHERE operation_id = ?1 AND status = 'recovering'",
            params![operation_id, now],
        )?;
        if updated == 0 {
            return Err(GatewayError::Conflict(
                "only a recovering operation may be resumed".to_owned(),
            ));
        }
        let operation = get_operation_on(&transaction, operation_id)?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::OperationResumed,
            "ttg.device-gateway",
            Some(&operation.physical_session_id),
            Some(operation_id),
            json!({"stage": operation.stage}),
            now,
        )?;
        transaction.commit()?;
        Ok((operation, event))
    }

    pub fn register_provider(
        &self,
        manifest: &ProviderManifest,
        now: &str,
    ) -> Result<(ProviderManifest, Option<GatewayEvent>), GatewayError> {
        let manifest_json = serde_json::to_string(manifest)?;
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let existing: Option<String> = transaction
            .query_row(
                "SELECT manifest_json FROM providers WHERE component_id = ?1",
                params![manifest.component_id],
                |row| row.get(0),
            )
            .optional()?;
        if let Some(existing) = existing {
            if existing == manifest_json {
                transaction.commit()?;
                return Ok((manifest.clone(), None));
            }
            return Err(GatewayError::Conflict(format!(
                "provider {:?} is already registered with a different manifest",
                manifest.component_id
            )));
        }
        transaction.execute(
            "INSERT INTO providers(component_id, manifest_json, created_at, updated_at)
             VALUES(?1, ?2, ?3, ?3)",
            params![manifest.component_id, manifest_json, now],
        )?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::ProviderRegistered,
            "ttg.device-gateway",
            None,
            None,
            serde_json::to_value(manifest)?,
            now,
        )?;
        transaction.commit()?;
        Ok((manifest.clone(), Some(event)))
    }

    pub fn get_provider(&self, component_id: &str) -> Result<ProviderManifest, GatewayError> {
        let connection = self.connect()?;
        get_provider_on(&connection, component_id)
    }

    pub fn list_providers(&self) -> Result<Vec<ProviderManifest>, GatewayError> {
        let connection = self.connect()?;
        list_providers_on(&connection)
    }

    pub fn register_worker(
        &self,
        worker_id: &str,
        provider_id: &str,
        capabilities: &[String],
        deadline_at: &str,
        now: &str,
    ) -> Result<(WorkerRecord, GatewayEvent), GatewayError> {
        if worker_id.is_empty() {
            return Err(GatewayError::InvalidInput(
                "worker_id must be non-empty".to_owned(),
            ));
        }
        parse_timestamp(deadline_at)?;
        let worker = WorkerRecord {
            worker_id: worker_id.to_owned(),
            provider_id: provider_id.to_owned(),
            capabilities: capabilities.to_vec(),
            status: WorkerStatus::Ready,
            last_heartbeat_at: now.to_owned(),
            deadline_at: deadline_at.to_owned(),
            created_at: now.to_owned(),
            updated_at: now.to_owned(),
        };
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        get_provider_on(&transaction, provider_id)?;
        let existing: Option<i64> = transaction
            .query_row(
                "SELECT 1 FROM workers WHERE worker_id = ?1",
                params![worker_id],
                |row| row.get(0),
            )
            .optional()?;
        if existing.is_some() {
            return Err(GatewayError::Conflict(format!(
                "worker {worker_id:?} is already registered"
            )));
        }
        transaction.execute(
            "INSERT INTO workers(
                worker_id, provider_id, capabilities_json, status, last_heartbeat_at,
                deadline_at, created_at, updated_at
             ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7)",
            params![
                worker.worker_id,
                worker.provider_id,
                serde_json::to_string(&worker.capabilities)?,
                encode_enum(worker.status)?,
                worker.last_heartbeat_at,
                worker.deadline_at,
                worker.created_at
            ],
        )?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::WorkerRegistered,
            "ttg.device-gateway",
            None,
            None,
            serde_json::to_value(&worker)?,
            now,
        )?;
        transaction.commit()?;
        Ok((worker, event))
    }

    pub fn heartbeat_worker(
        &self,
        worker_id: &str,
        deadline_at: &str,
        now: &str,
    ) -> Result<(WorkerRecord, GatewayEvent), GatewayError> {
        parse_timestamp(deadline_at)?;
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let updated = transaction.execute(
            "UPDATE workers
             SET status = 'running', last_heartbeat_at = ?2, deadline_at = ?3, updated_at = ?2
             WHERE worker_id = ?1 AND status IN ('ready', 'running')",
            params![worker_id, now, deadline_at],
        )?;
        if updated == 0 {
            return Err(GatewayError::Conflict(format!(
                "worker {worker_id:?} is missing, stopped, or timed out"
            )));
        }
        let worker = get_worker_on(&transaction, worker_id)?;
        let event = append_event_in_transaction(
            &transaction,
            GatewayEventKind::WorkerHeartbeat,
            "ttg.device-gateway",
            None,
            None,
            json!({"deadline_at": deadline_at, "worker_id": worker_id}),
            now,
        )?;
        transaction.commit()?;
        Ok((worker, event))
    }

    pub fn get_worker(&self, worker_id: &str) -> Result<WorkerRecord, GatewayError> {
        let connection = self.connect()?;
        get_worker_on(&connection, worker_id)
    }

    pub fn list_workers(&self) -> Result<Vec<WorkerRecord>, GatewayError> {
        let connection = self.connect()?;
        list_workers_on(&connection)
    }

    pub fn sweep_workers(
        &self,
        now: &str,
    ) -> Result<Vec<(WorkerRecord, GatewayEvent)>, GatewayError> {
        let now_value = parse_timestamp(now)?;
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let workers = list_workers_on(&transaction)?;
        let mut timed_out = Vec::new();
        for worker in workers {
            if matches!(worker.status, WorkerStatus::Ready | WorkerStatus::Running)
                && parse_timestamp(&worker.deadline_at)? <= now_value
            {
                let updated = transaction.execute(
                    "UPDATE workers SET status = 'timed_out', updated_at = ?2
                     WHERE worker_id = ?1 AND status IN ('ready', 'running')",
                    params![worker.worker_id, now],
                )?;
                if updated == 0 {
                    continue;
                }
                let updated_worker = get_worker_on(&transaction, &worker.worker_id)?;
                let event = append_event_in_transaction(
                    &transaction,
                    GatewayEventKind::WorkerTimedOut,
                    "ttg.device-gateway",
                    None,
                    None,
                    json!({
                        "deadline_at": updated_worker.deadline_at.clone(),
                        "worker_id": updated_worker.worker_id.clone()
                    }),
                    now,
                )?;
                timed_out.push((updated_worker, event));
            }
        }
        transaction.commit()?;
        Ok(timed_out)
    }

    pub fn append_event(
        &self,
        event_type: GatewayEventKind,
        producer: &str,
        physical_session_id: Option<&str>,
        operation_id: Option<&str>,
        payload: Value,
        timestamp: &str,
    ) -> Result<GatewayEvent, GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
        let event = append_event_in_transaction(
            &transaction,
            event_type,
            producer,
            physical_session_id,
            operation_id,
            payload,
            timestamp,
        )?;
        transaction.commit()?;
        Ok(event)
    }

    pub fn list_events(
        &self,
        after_sequence: i64,
        limit: u32,
    ) -> Result<Vec<GatewayEvent>, GatewayError> {
        if limit == 0 || limit > 1_000 {
            return Err(GatewayError::InvalidInput(
                "event limit must be between 1 and 1000".to_owned(),
            ));
        }
        let connection = self.connect()?;
        list_events_on(&connection, after_sequence, limit)
    }

    pub fn verify_journal(&self) -> Result<(), GatewayError> {
        let mut after_sequence = 0;
        let mut expected_previous: Option<String> = None;
        loop {
            let events = self.list_events(after_sequence, 1_000)?;
            if events.is_empty() {
                break;
            }
            for event in events {
                if event.previous_hash != expected_previous {
                    return Err(GatewayError::JournalCorrupt(format!(
                        "journal sequence {} has an invalid previous hash",
                        event.sequence
                    )));
                }
                let core = event_core(EventCore {
                    event_id: &event.event_id,
                    event_type: event.event_type,
                    producer: &event.producer,
                    physical_session_id: event.physical_session_id.as_deref(),
                    operation_id: event.operation_id.as_deref(),
                    timestamp: &event.timestamp,
                    payload: &event.payload,
                    previous_hash: event.previous_hash.as_deref(),
                })?;
                let actual = canonical_sha256(&core).map_err(GatewayError::Json)?;
                if actual != event.event_hash {
                    return Err(GatewayError::JournalCorrupt(format!(
                        "journal sequence {} has an invalid event hash",
                        event.sequence
                    )));
                }
                after_sequence = event.sequence;
                expected_previous = Some(event.event_hash);
            }
        }
        Ok(())
    }

    pub fn doctor(&self) -> Result<DoctorReport, GatewayError> {
        let connection = self.connect()?;
        let schema_version: i64 = connection
            .query_row(
                "SELECT value FROM gateway_meta WHERE key = 'schema_version'",
                [],
                |row| row.get::<_, String>(0),
            )?
            .parse()
            .map_err(|_| GatewayError::Storage("invalid schema version metadata".to_owned()))?;
        let active_physical_sessions = count_query(
            &connection,
            "SELECT COUNT(*) FROM physical_sessions WHERE state = 'active'",
        )?;
        let active_operation_sessions = count_query(
            &connection,
            "SELECT COUNT(*) FROM operation_sessions WHERE status = 'active'",
        )?;
        let recovering_operation_sessions = count_query(
            &connection,
            "SELECT COUNT(*) FROM operation_sessions WHERE status = 'recovering'",
        )?;
        let registered_providers = count_query(&connection, "SELECT COUNT(*) FROM providers")?;
        let timed_out_workers = count_query(
            &connection,
            "SELECT COUNT(*) FROM workers WHERE status = 'timed_out'",
        )?;
        let mut errors = Vec::new();
        let journal_valid = match self.verify_journal() {
            Ok(()) => true,
            Err(error) => {
                errors.push(error.to_string());
                false
            }
        };
        if schema_version != GATEWAY_SCHEMA_VERSION {
            errors.push(format!(
                "database schema {schema_version} does not match {GATEWAY_SCHEMA_VERSION}"
            ));
        }
        Ok(DoctorReport {
            healthy: errors.is_empty(),
            schema_version,
            journal_valid,
            active_physical_sessions,
            active_operation_sessions,
            recovering_operation_sessions,
            registered_providers,
            timed_out_workers,
            device_authority: DEVICE_AUTHORITY.to_owned(),
            xray_authority: XRAY_AUTHORITY.to_owned(),
            errors,
        })
    }

    pub fn snapshot(&self) -> Result<GatewaySnapshot, GatewayError> {
        let mut connection = self.connect()?;
        let transaction = connection.transaction_with_behavior(TransactionBehavior::Deferred)?;
        let last_event_sequence = transaction.query_row(
            "SELECT COALESCE(MAX(sequence), 0) FROM journal_events",
            [],
            |row| row.get(0),
        )?;
        let snapshot = GatewaySnapshot {
            schema_version: GATEWAY_SCHEMA_VERSION,
            physical_sessions: list_physical_sessions_on(&transaction)?,
            operation_sessions: list_operations_on(&transaction)?,
            providers: list_providers_on(&transaction)?,
            workers: list_workers_on(&transaction)?,
            last_event_sequence,
            device_authority: DEVICE_AUTHORITY.to_owned(),
            xray_authority: XRAY_AUTHORITY.to_owned(),
        };
        transaction.commit()?;
        Ok(snapshot)
    }
}

fn append_event_in_transaction(
    transaction: &Transaction<'_>,
    event_type: GatewayEventKind,
    producer: &str,
    physical_session_id: Option<&str>,
    operation_id: Option<&str>,
    payload: Value,
    timestamp: &str,
) -> Result<GatewayEvent, GatewayError> {
    let previous_hash: Option<String> = transaction
        .query_row(
            "SELECT event_hash FROM journal_events ORDER BY sequence DESC LIMIT 1",
            [],
            |row| row.get(0),
        )
        .optional()?;
    let event_id = Uuid::new_v4().to_string();
    let core = event_core(EventCore {
        event_id: &event_id,
        event_type,
        producer,
        physical_session_id,
        operation_id,
        timestamp,
        payload: &payload,
        previous_hash: previous_hash.as_deref(),
    })?;
    let event_hash = canonical_sha256(&core).map_err(GatewayError::Json)?;
    transaction.execute(
        "INSERT INTO journal_events(
            event_id, event_type, producer, physical_session_id, operation_id,
            timestamp, payload_json, previous_hash, event_hash
         ) VALUES(?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            event_id,
            encode_enum(event_type)?,
            producer,
            physical_session_id,
            operation_id,
            timestamp,
            serde_json::to_string(&payload)?,
            previous_hash,
            event_hash
        ],
    )?;
    let sequence = transaction.last_insert_rowid();
    Ok(GatewayEvent {
        sequence,
        event_id,
        event_type,
        producer: producer.to_owned(),
        physical_session_id: physical_session_id.map(str::to_owned),
        operation_id: operation_id.map(str::to_owned),
        timestamp: timestamp.to_owned(),
        payload,
        previous_hash,
        event_hash,
    })
}

fn get_physical_session_on(
    connection: &Connection,
    session_id: &str,
) -> Result<PhysicalDeviceSession, GatewayError> {
    let raw = connection
        .query_row(
            "SELECT session_id, fingerprint_sha256, state, created_at, updated_at, recovery_count
             FROM physical_sessions WHERE session_id = ?1",
            params![session_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, u64>(5)?,
                ))
            },
        )
        .optional()?;
    let Some((session_id, fingerprint_sha256, state, created_at, updated_at, recovery_count)) = raw
    else {
        return Err(GatewayError::NotFound(format!(
            "physical session {session_id:?} does not exist"
        )));
    };
    Ok(PhysicalDeviceSession {
        session_id,
        fingerprint_sha256,
        state: decode_enum(&state)?,
        created_at,
        updated_at,
        recovery_count,
    })
}

fn list_physical_sessions_on(
    connection: &Connection,
) -> Result<Vec<PhysicalDeviceSession>, GatewayError> {
    let mut statement = connection.prepare(
        "SELECT session_id, fingerprint_sha256, state, created_at, updated_at, recovery_count
         FROM physical_sessions ORDER BY created_at, session_id",
    )?;
    let rows = statement.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4)?,
            row.get::<_, u64>(5)?,
        ))
    })?;
    rows.map(|row| {
        let (session_id, fingerprint_sha256, state, created_at, updated_at, recovery_count) = row?;
        Ok(PhysicalDeviceSession {
            session_id,
            fingerprint_sha256,
            state: decode_enum(&state)?,
            created_at,
            updated_at,
            recovery_count,
        })
    })
    .collect()
}

fn get_operation_on(
    connection: &Connection,
    operation_id: &str,
) -> Result<OperationSession, GatewayError> {
    let raw = connection
        .query_row(
            "SELECT operation_id, physical_session_id, request_sha256, stage, status,
                    created_at, updated_at, recovery_count
             FROM operation_sessions WHERE operation_id = ?1",
            params![operation_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, u64>(7)?,
                ))
            },
        )
        .optional()?;
    let Some((
        operation_id,
        physical_session_id,
        request_sha256,
        stage,
        status,
        created_at,
        updated_at,
        recovery_count,
    )) = raw
    else {
        return Err(GatewayError::NotFound(format!(
            "operation {operation_id:?} does not exist"
        )));
    };
    Ok(OperationSession {
        operation_id,
        physical_session_id,
        request_sha256,
        stage: decode_enum(&stage)?,
        status: decode_enum(&status)?,
        created_at,
        updated_at,
        recovery_count,
    })
}

fn list_operations_on(connection: &Connection) -> Result<Vec<OperationSession>, GatewayError> {
    let mut statement = connection.prepare(
        "SELECT operation_id, physical_session_id, request_sha256, stage, status,
                created_at, updated_at, recovery_count
         FROM operation_sessions ORDER BY created_at, operation_id",
    )?;
    let rows = statement.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4)?,
            row.get::<_, String>(5)?,
            row.get::<_, String>(6)?,
            row.get::<_, u64>(7)?,
        ))
    })?;
    rows.map(|row| {
        let (
            operation_id,
            physical_session_id,
            request_sha256,
            stage,
            status,
            created_at,
            updated_at,
            recovery_count,
        ) = row?;
        Ok(OperationSession {
            operation_id,
            physical_session_id,
            request_sha256,
            stage: decode_enum(&stage)?,
            status: decode_enum(&status)?,
            created_at,
            updated_at,
            recovery_count,
        })
    })
    .collect()
}

fn get_provider_on(
    connection: &Connection,
    component_id: &str,
) -> Result<ProviderManifest, GatewayError> {
    let manifest: Option<String> = connection
        .query_row(
            "SELECT manifest_json FROM providers WHERE component_id = ?1",
            params![component_id],
            |row| row.get(0),
        )
        .optional()?;
    let Some(manifest) = manifest else {
        return Err(GatewayError::NotFound(format!(
            "provider {component_id:?} is not registered"
        )));
    };
    Ok(serde_json::from_str(&manifest)?)
}

fn list_providers_on(connection: &Connection) -> Result<Vec<ProviderManifest>, GatewayError> {
    let mut statement =
        connection.prepare("SELECT manifest_json FROM providers ORDER BY component_id")?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    rows.map(|row| Ok(serde_json::from_str(&row?)?)).collect()
}

fn get_worker_on(connection: &Connection, worker_id: &str) -> Result<WorkerRecord, GatewayError> {
    let raw = connection
        .query_row(
            "SELECT worker_id, provider_id, capabilities_json, status, last_heartbeat_at,
                    deadline_at, created_at, updated_at
             FROM workers WHERE worker_id = ?1",
            params![worker_id],
            |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                    row.get::<_, String>(4)?,
                    row.get::<_, String>(5)?,
                    row.get::<_, String>(6)?,
                    row.get::<_, String>(7)?,
                ))
            },
        )
        .optional()?;
    let Some((
        worker_id,
        provider_id,
        capabilities,
        status,
        last_heartbeat_at,
        deadline_at,
        created_at,
        updated_at,
    )) = raw
    else {
        return Err(GatewayError::NotFound(format!(
            "worker {worker_id:?} does not exist"
        )));
    };
    Ok(WorkerRecord {
        worker_id,
        provider_id,
        capabilities: serde_json::from_str(&capabilities)?,
        status: decode_enum(&status)?,
        last_heartbeat_at,
        deadline_at,
        created_at,
        updated_at,
    })
}

fn list_workers_on(connection: &Connection) -> Result<Vec<WorkerRecord>, GatewayError> {
    let mut statement = connection.prepare(
        "SELECT worker_id, provider_id, capabilities_json, status, last_heartbeat_at,
                deadline_at, created_at, updated_at
         FROM workers ORDER BY worker_id",
    )?;
    let rows = statement.query_map([], |row| {
        Ok((
            row.get::<_, String>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, String>(4)?,
            row.get::<_, String>(5)?,
            row.get::<_, String>(6)?,
            row.get::<_, String>(7)?,
        ))
    })?;
    rows.map(|row| {
        let (
            worker_id,
            provider_id,
            capabilities,
            status,
            last_heartbeat_at,
            deadline_at,
            created_at,
            updated_at,
        ) = row?;
        Ok(WorkerRecord {
            worker_id,
            provider_id,
            capabilities: serde_json::from_str(&capabilities)?,
            status: decode_enum(&status)?,
            last_heartbeat_at,
            deadline_at,
            created_at,
            updated_at,
        })
    })
    .collect()
}

fn list_events_on(
    connection: &Connection,
    after_sequence: i64,
    limit: u32,
) -> Result<Vec<GatewayEvent>, GatewayError> {
    let mut statement = connection.prepare(
        "SELECT sequence, event_id, event_type, producer, physical_session_id,
                operation_id, timestamp, payload_json, previous_hash, event_hash
         FROM journal_events WHERE sequence > ?1 ORDER BY sequence LIMIT ?2",
    )?;
    let rows = statement.query_map(params![after_sequence, i64::from(limit)], |row| {
        Ok((
            row.get::<_, i64>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, String>(3)?,
            row.get::<_, Option<String>>(4)?,
            row.get::<_, Option<String>>(5)?,
            row.get::<_, String>(6)?,
            row.get::<_, String>(7)?,
            row.get::<_, Option<String>>(8)?,
            row.get::<_, String>(9)?,
        ))
    })?;
    rows.map(|row| {
        let (
            sequence,
            event_id,
            event_type,
            producer,
            physical_session_id,
            operation_id,
            timestamp,
            payload,
            previous_hash,
            event_hash,
        ) = row?;
        Ok(GatewayEvent {
            sequence,
            event_id,
            event_type: decode_enum(&event_type)?,
            producer,
            physical_session_id,
            operation_id,
            timestamp,
            payload: serde_json::from_str(&payload)?,
            previous_hash,
            event_hash,
        })
    })
    .collect()
}

struct EventCore<'a> {
    event_id: &'a str,
    event_type: GatewayEventKind,
    producer: &'a str,
    physical_session_id: Option<&'a str>,
    operation_id: Option<&'a str>,
    timestamp: &'a str,
    payload: &'a Value,
    previous_hash: Option<&'a str>,
}

fn event_core(input: EventCore<'_>) -> Result<Value, GatewayError> {
    Ok(json!({
        "event_id": input.event_id,
        "event_type": encode_enum(input.event_type)?,
        "operation_id": input.operation_id,
        "payload": input.payload,
        "physical_session_id": input.physical_session_id,
        "previous_hash": input.previous_hash,
        "producer": input.producer,
        "timestamp": input.timestamp
    }))
}

fn encode_enum<T: Serialize>(value: T) -> Result<String, GatewayError> {
    let encoded = serde_json::to_value(value)?;
    encoded
        .as_str()
        .map(str::to_owned)
        .ok_or_else(|| GatewayError::Json("enum did not serialize as a string".to_owned()))
}

fn decode_enum<T: DeserializeOwned>(value: &str) -> Result<T, GatewayError> {
    Ok(serde_json::from_value(Value::String(value.to_owned()))?)
}

fn query_strings(connection: &Connection, query: &str) -> Result<Vec<String>, GatewayError> {
    let mut statement = connection.prepare(query)?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    rows.map(|row| Ok(row?)).collect()
}

fn count_query(connection: &Connection, query: &str) -> Result<u64, GatewayError> {
    Ok(connection.query_row(query, [], |row| row.get(0))?)
}

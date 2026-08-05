use chrono::{Duration as ChronoDuration, SecondsFormat, Utc};
use serde_json::{json, Value};
use std::fs;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Barrier};
use std::thread;
use std::time::Duration;
use techguy_contracts_core::ValidationContext;
use techguy_device_gateway::{
    DeviceAccess, Gateway, GatewayEventKind, OperationStage, OperationStatus, ProviderManifest,
    WorkerStatus,
};
use tempfile::tempdir;

const VALID_CONTRACTS: &str = include_str!("../../../contracts/fixtures/valid_contracts.json");

#[test]
fn persistent_identity_and_stage_survive_gateway_restart() {
    let root = tempdir().expect("tempdir");
    let database = root.path().join("gateway.sqlite3");

    let gateway = Gateway::open(&database).expect("first gateway");
    let session = gateway
        .open_physical_session(&"a".repeat(64))
        .expect("physical session");
    let operation = gateway
        .open_operation(&session.session_id, &"b".repeat(64))
        .expect("operation");
    let operation = gateway
        .transition_operation(&operation.operation_id, OperationStage::EvidenceCollection)
        .expect("transition");
    assert_eq!(operation.stage, OperationStage::EvidenceCollection);
    drop(gateway);

    let gateway = Gateway::open(&database).expect("restarted gateway");
    let recovered_session = gateway
        .get_physical_session(&session.session_id)
        .expect("recovered physical session");
    let recovered_operation = gateway
        .get_operation(&operation.operation_id)
        .expect("recovered operation");
    assert_eq!(recovered_session.session_id, session.session_id);
    assert_eq!(
        recovered_session.fingerprint_sha256,
        session.fingerprint_sha256
    );
    assert!(recovered_session.recovery_count >= 1);
    assert_eq!(
        recovered_operation.stage,
        OperationStage::EvidenceCollection
    );
    assert_eq!(recovered_operation.status, OperationStatus::Recovering);
    assert!(recovered_operation.recovery_count >= 1);

    let resumed = gateway
        .resume_operation(&operation.operation_id)
        .expect("resume operation");
    assert_eq!(resumed.status, OperationStatus::Active);
    assert!(gateway.doctor().expect("doctor").healthy);
}

#[test]
fn provider_and_worker_capabilities_are_fail_closed() {
    let root = tempdir().expect("tempdir");
    let gateway = Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway");

    let forbidden = ProviderManifest {
        component_id: "unsafe.provider".to_owned(),
        version: "1.0.0".to_owned(),
        device_access: DeviceAccess::ReadOnly,
        contract_authorities: vec!["observation".to_owned()],
        capabilities: vec!["device.flash".to_owned()],
    };
    let error = gateway
        .register_provider(forbidden)
        .expect_err("device write capability must fail");
    assert_eq!(error.code(), "POLICY_DENIED");

    let provider = ProviderManifest {
        component_id: "kirin.xray".to_owned(),
        version: "1.0.0".to_owned(),
        device_access: DeviceAccess::ReadOnly,
        contract_authorities: vec!["observation".to_owned()],
        capabilities: vec!["contract.publish".to_owned(), "evidence.read".to_owned()],
    };
    gateway
        .register_provider(provider)
        .expect("read-only provider");

    let error = gateway
        .register_worker(
            "worker-1",
            "kirin.xray",
            &["device.partition_write".to_owned()],
            &future_timestamp(30),
        )
        .expect_err("worker write capability must fail");
    assert_eq!(error.code(), "POLICY_DENIED");
}

#[test]
fn shared_contract_ingress_is_validated_and_authority_bound() {
    let root = tempdir().expect("tempdir");
    let gateway = Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway");
    let session = gateway
        .open_physical_session(&"c".repeat(64))
        .expect("physical session");

    let fixtures: Value = serde_json::from_str(VALID_CONTRACTS).expect("fixtures");
    let case = fixtures["contracts"]
        .as_array()
        .expect("contracts")
        .iter()
        .find(|case| case["name"] == "physical_device_session")
        .expect("physical device session fixture");
    let mut contract = case["contract"].clone();
    contract["producer"] = json!("kirin.xray");
    contract["physical_session_id"] = json!(session.session_id);
    let authority = contract["authority"]
        .as_str()
        .expect("authority")
        .to_owned();
    let mut context: ValidationContext =
        serde_json::from_value(case["context"].clone()).expect("context");
    context.expected_physical_session_id = Some(session.session_id.clone());

    gateway
        .register_provider(ProviderManifest {
            component_id: "kirin.xray".to_owned(),
            version: "1.0.0".to_owned(),
            device_access: DeviceAccess::ReadOnly,
            contract_authorities: vec![authority],
            capabilities: vec!["contract.publish".to_owned(), "evidence.read".to_owned()],
        })
        .expect("provider");

    let receipt = gateway
        .publish_contract("kirin.xray", &contract, &context)
        .expect("contract ingress");
    assert_eq!(receipt.contract_type, "physical_device_session");
    assert_eq!(receipt.contract_sha256.len(), 64);
    gateway.verify_journal().expect("journal chain");

    contract["producer"] = json!("other.provider");
    let error = gateway
        .publish_contract("kirin.xray", &contract, &context)
        .expect_err("producer mismatch must fail");
    assert_eq!(error.code(), "POLICY_DENIED");
}

#[test]
fn watchdog_marks_stale_workers_without_device_authority() {
    let root = tempdir().expect("tempdir");
    let gateway = Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway");
    gateway
        .register_provider(ProviderManifest {
            component_id: "gateway.diagnostics".to_owned(),
            version: "1.0.0".to_owned(),
            device_access: DeviceAccess::None,
            contract_authorities: vec![],
            capabilities: vec!["diagnostics.read".to_owned(), "worker.heartbeat".to_owned()],
        })
        .expect("provider");
    gateway
        .register_worker(
            "doctor-worker",
            "gateway.diagnostics",
            &["worker.heartbeat".to_owned()],
            &future_timestamp(1),
        )
        .expect("worker");
    thread::sleep(Duration::from_millis(1_200));
    let timed_out = gateway.sweep_workers().expect("watchdog sweep");
    assert_eq!(timed_out.len(), 1);
    assert_eq!(timed_out[0].status, WorkerStatus::TimedOut);
    assert_eq!(gateway.health().device_authority, "none");
}

#[test]
fn worker_deadlines_are_future_and_bounded() {
    let root = tempdir().expect("tempdir");
    let gateway = Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway");
    gateway
        .register_provider(ProviderManifest {
            component_id: "gateway.worker-policy".to_owned(),
            version: "1.0.0".to_owned(),
            device_access: DeviceAccess::None,
            contract_authorities: vec![],
            capabilities: vec!["worker.heartbeat".to_owned()],
        })
        .expect("provider");

    let past = (Utc::now() - ChronoDuration::seconds(1)).to_rfc3339_opts(SecondsFormat::Secs, true);
    let error = gateway
        .register_worker(
            "past-worker",
            "gateway.worker-policy",
            &["worker.heartbeat".to_owned()],
            &past,
        )
        .expect_err("past deadline must fail");
    assert_eq!(error.code(), "INVALID_INPUT");

    let error = gateway
        .register_worker(
            "long-worker",
            "gateway.worker-policy",
            &["worker.heartbeat".to_owned()],
            &future_timestamp(600),
        )
        .expect_err("excessive deadline must fail");
    assert_eq!(error.code(), "INVALID_INPUT");
}

#[test]
fn concurrent_transition_has_one_accurate_audit_event() {
    let root = tempdir().expect("tempdir");
    let gateway = Arc::new(Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway"));
    let session = gateway
        .open_physical_session(&"e".repeat(64))
        .expect("session");
    let operation = gateway
        .open_operation(&session.session_id, &"f".repeat(64))
        .expect("operation");
    let barrier = Arc::new(Barrier::new(3));
    let mut handles = Vec::new();
    for _ in 0..2 {
        let gateway = Arc::clone(&gateway);
        let barrier = Arc::clone(&barrier);
        let operation_id = operation.operation_id.clone();
        handles.push(thread::spawn(move || {
            barrier.wait();
            gateway.transition_operation(&operation_id, OperationStage::EvidenceCollection)
        }));
    }
    barrier.wait();
    for handle in handles {
        let result = handle.join().expect("transition thread");
        assert_eq!(
            result.expect("idempotent transition").stage,
            OperationStage::EvidenceCollection
        );
    }
    let events = gateway.list_events(0, 100).expect("events");
    let transitions: Vec<_> = events
        .iter()
        .filter(|event| event.event_type == GatewayEventKind::OperationTransitioned)
        .collect();
    assert_eq!(transitions.len(), 1);
    assert_eq!(transitions[0].payload["from"], "requested");
    assert_eq!(transitions[0].payload["to"], "evidence_collection");
    gateway.verify_journal().expect("journal");
}

#[test]
fn snapshot_is_consistent_during_concurrent_writes() {
    let root = tempdir().expect("tempdir");
    let gateway = Arc::new(Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway"));
    let finished = Arc::new(AtomicBool::new(false));
    let writer_gateway = Arc::clone(&gateway);
    let writer_finished = Arc::clone(&finished);
    let writer = thread::spawn(move || {
        for index in 0..64_u64 {
            let session = writer_gateway
                .open_physical_session(&format!("{index:064x}"))
                .expect("session");
            writer_gateway
                .open_operation(&session.session_id, &format!("{:064x}", index + 1_000))
                .expect("operation");
        }
        writer_finished.store(true, Ordering::Release);
    });

    while !finished.load(Ordering::Acquire) {
        assert_snapshot_consistent(&gateway.snapshot().expect("snapshot"));
        thread::yield_now();
    }
    writer.join().expect("writer");
    assert_snapshot_consistent(&gateway.snapshot().expect("final snapshot"));
}

#[test]
fn journal_tampering_is_detected() {
    let root = tempdir().expect("tempdir");
    let database = root.path().join("gateway.sqlite3");
    let gateway = Gateway::open(&database).expect("gateway");
    gateway
        .open_physical_session(&"d".repeat(64))
        .expect("session");
    gateway.verify_journal().expect("valid journal");
    drop(gateway);

    let connection = rusqlite::Connection::open(&database).expect("database");
    connection
        .execute(
            "UPDATE journal_events SET payload_json = ?1 WHERE sequence = 1",
            ["{\"tampered\":true}"],
        )
        .expect("tamper");
    drop(connection);

    let error = Gateway::open(&database).expect_err("corrupt journal must block startup");
    assert_eq!(error.code(), "JOURNAL_CORRUPT");
    let gateway = Gateway::inspect(&database).expect("diagnostic gateway");
    let doctor = gateway.doctor().expect("doctor");
    assert!(!doctor.healthy);
    assert!(!doctor.journal_valid);
}

#[test]
fn source_has_no_device_execution_surface() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut source = String::new();
    for entry in fs::read_dir(root).expect("source directory") {
        let path = entry.expect("entry").path();
        if path.extension().and_then(|value| value.to_str()) == Some("rs") {
            source.push_str(&fs::read_to_string(path).expect("source file"));
        }
    }
    for forbidden in [
        "fastboot flash",
        "fastboot erase",
        "adb reboot",
        "HUAWEI USB COM 1.0",
        "write_oeminfo(",
        "partition_write(",
    ] {
        assert!(
            !source.contains(forbidden),
            "forbidden surface: {forbidden}"
        );
    }
}

fn assert_snapshot_consistent(snapshot: &techguy_device_gateway::GatewaySnapshot) {
    let expected_events = 1 + snapshot.physical_sessions.len() + snapshot.operation_sessions.len();
    assert_eq!(snapshot.last_event_sequence as usize, expected_events);
}

fn future_timestamp(seconds: i64) -> String {
    (Utc::now() + ChronoDuration::seconds(seconds)).to_rfc3339_opts(SecondsFormat::Secs, true)
}

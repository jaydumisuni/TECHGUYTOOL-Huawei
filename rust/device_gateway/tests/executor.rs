use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use techguy_device_gateway::{
    BoundedAdapter, BoundedExecutor, BoundedStageRequest, CancellationFlag, ExecutionLeaseContext,
    ExecutorError, LeaseGuard, RawAdapterResult,
};

const SESSION: &str = "11111111-1111-4111-8111-111111111111";
const LEASE_ID: &str = "33333333-3333-4333-8333-333333333333";
const RECIPE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const RANGE: &str = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
const NOW: &str = "2026-08-09T13:00:00Z";
const PAYLOAD: &[u8] = b"phase7-bounded-payload";

fn payload_hash() -> String {
    let mut digest = Sha256::new();
    digest.update(PAYLOAD);
    format!("{:x}", digest.finalize())
}

fn lease() -> Value {
    json!({
        "schema_version": 1,
        "contract_type": "execution_lease",
        "contract_id": "55555555-5555-4555-8555-555555555555",
        "producer": "repair.governor",
        "created_at": "2026-08-09T12:50:00Z",
        "physical_session_id": SESSION,
        "evidence_hashes": [],
        "confidence_bps": 10000,
        "expires_at": "2026-08-09T14:00:00Z",
        "authority": "execution",
        "single_use": true,
        "consumed_at": null,
        "payload": {
            "lease_id": LEASE_ID,
            "recipe_hash": RECIPE,
            "adapter_id": "test.memory.adapter",
            "adapter_version": "1.0.0",
            "artifact_hashes": [payload_hash()],
            "allowed_partitions": ["oeminfo"],
            "range_manifest_sha256": RANGE,
            "max_write_bytes": 4096,
            "expected_mode": "board_service_fastboot",
            "stage_id": "restore.main-version",
            "reboot_allowed": false
        }
    })
}

fn lease_context() -> ExecutionLeaseContext {
    ExecutionLeaseContext {
        physical_session_id: SESSION.to_owned(),
        recipe_hash: RECIPE.to_owned(),
        adapter_id: "test.memory.adapter".to_owned(),
        adapter_version: "1.0.0".to_owned(),
        artifact_hashes: vec![payload_hash()],
        partition: "oeminfo".to_owned(),
        range_manifest_sha256: RANGE.to_owned(),
        write_bytes: PAYLOAD.len() as u64,
        current_mode: "board_service_fastboot".to_owned(),
        stage_id: "restore.main-version".to_owned(),
        request_reboot: false,
        now: NOW.to_owned(),
    }
}

fn request() -> BoundedStageRequest {
    BoundedStageRequest {
        physical_session_id: SESSION.to_owned(),
        stage_id: "restore.main-version".to_owned(),
        partition: "oeminfo".to_owned(),
        adapter_id: "test.memory.adapter".to_owned(),
        adapter_version: "1.0.0".to_owned(),
        current_mode: "board_service_fastboot".to_owned(),
        range_manifest_sha256: RANGE.to_owned(),
        payload: PAYLOAD.to_vec(),
        payload_sha256: payload_hash(),
        backup_required: true,
        readback_required: true,
        exact_readback_required: true,
        request_reboot: false,
    }
}

#[derive(Default)]
struct MemoryAdapter {
    calls: usize,
    omit_backup: bool,
    corrupt_readback: bool,
    wrong_count: bool,
    cancel_during: bool,
}

impl BoundedAdapter for MemoryAdapter {
    fn adapter_id(&self) -> &str {
        "test.memory.adapter"
    }

    fn adapter_version(&self) -> &str {
        "1.0.0"
    }

    fn execute(
        &mut self,
        request: &BoundedStageRequest,
        cancellation: &CancellationFlag,
    ) -> Result<RawAdapterResult, String> {
        self.calls += 1;
        if self.cancel_during {
            cancellation.cancel();
        }
        Ok(RawAdapterResult {
            bytes_written: if self.wrong_count {
                request.payload.len() as u64 - 1
            } else {
                request.payload.len() as u64
            },
            backup_sha256: if self.omit_backup {
                None
            } else {
                Some("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd".to_owned())
            },
            readback_sha256: Some(if self.corrupt_readback {
                "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_owned()
            } else {
                request.payload_sha256.clone()
            }),
            adapter_code: "OK".to_owned(),
            adapter_message: "memory adapter completed".to_owned(),
        })
    }
}

fn executor(adapter: MemoryAdapter) -> BoundedExecutor {
    let mut executor = BoundedExecutor::new(LeaseGuard::in_memory().unwrap());
    executor.register_adapter(Box::new(adapter)).unwrap();
    executor
}

fn policy_code(error: ExecutorError) -> String {
    match error {
        ExecutorError::Policy(code) => code,
        other => panic!("expected policy error, got {other}"),
    }
}

#[test]
fn exact_authority_executes_once_and_verifies_readback() {
    let mut executor = executor(MemoryAdapter::default());
    let result = executor
        .execute_authorized(
            &lease(),
            &lease_context(),
            &request(),
            &CancellationFlag::default(),
        )
        .unwrap();
    assert!(result.verified);
    assert_eq!(result.lease_id, LEASE_ID);
    assert_eq!(result.bytes_written, PAYLOAD.len() as u64);
    assert_eq!(
        result.readback_sha256.as_deref(),
        Some(payload_hash().as_str())
    );

    let replay = executor
        .execute_authorized(
            &lease(),
            &lease_context(),
            &request(),
            &CancellationFlag::default(),
        )
        .unwrap_err();
    assert!(matches!(replay, ExecutorError::Lease(_)));
}

#[test]
fn unregistered_adapter_fails_before_lease_claim() {
    let mut executor = BoundedExecutor::new(LeaseGuard::in_memory().unwrap());
    let error = executor
        .execute_authorized(
            &lease(),
            &lease_context(),
            &request(),
            &CancellationFlag::default(),
        )
        .unwrap_err();
    assert_eq!(policy_code(error), "ADAPTER_NOT_REGISTERED");
}

#[test]
fn request_mismatch_fails_before_adapter() {
    let fields = [
        "session",
        "stage",
        "partition",
        "adapter",
        "version",
        "mode",
        "range",
        "reboot",
    ];
    for field in fields {
        let mut executor = executor(MemoryAdapter::default());
        let mut request = request();
        let expected = match field {
            "session" => {
                request.physical_session_id = "99999999-9999-4999-8999-999999999999".to_owned();
                "EXECUTOR_SESSION_MISMATCH"
            }
            "stage" => {
                request.stage_id = "restore.branding".to_owned();
                "EXECUTOR_STAGE_MISMATCH"
            }
            "partition" => {
                request.partition = "version_a".to_owned();
                "EXECUTOR_PARTITION_MISMATCH"
            }
            "adapter" => {
                request.adapter_id = "other.adapter".to_owned();
                "EXECUTOR_ADAPTER_MISMATCH"
            }
            "version" => {
                request.adapter_version = "2.0.0".to_owned();
                "EXECUTOR_ADAPTER_VERSION_MISMATCH"
            }
            "mode" => {
                request.current_mode = "qualcomm_firehose".to_owned();
                "EXECUTOR_MODE_MISMATCH"
            }
            "range" => {
                request.range_manifest_sha256 =
                    "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_owned();
                "EXECUTOR_RANGE_MISMATCH"
            }
            "reboot" => {
                request.request_reboot = true;
                "EXECUTOR_REBOOT_REQUEST_MISMATCH"
            }
            _ => unreachable!(),
        };
        let error = executor
            .execute_authorized(
                &lease(),
                &lease_context(),
                &request,
                &CancellationFlag::default(),
            )
            .unwrap_err();
        assert_eq!(policy_code(error), expected);
    }
}

#[test]
fn payload_hash_size_and_artifact_authority_are_fail_closed() {
    let mut bad_hash = request();
    bad_hash.payload_sha256 =
        "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_owned();
    let mut executor = executor(MemoryAdapter::default());
    assert_eq!(
        policy_code(
            executor
                .execute_authorized(
                    &lease(),
                    &lease_context(),
                    &bad_hash,
                    &CancellationFlag::default()
                )
                .unwrap_err()
        ),
        "PAYLOAD_HASH_MISMATCH"
    );

    let mut wrong_size_context = lease_context();
    wrong_size_context.write_bytes += 1;
    let mut executor = executor(MemoryAdapter::default());
    assert_eq!(
        policy_code(
            executor
                .execute_authorized(
                    &lease(),
                    &wrong_size_context,
                    &request(),
                    &CancellationFlag::default()
                )
                .unwrap_err()
        ),
        "PAYLOAD_SIZE_MISMATCH"
    );

    let mut unauthorized = lease_context();
    unauthorized.artifact_hashes =
        vec!["eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee".to_owned()];
    let mut executor = executor(MemoryAdapter::default());
    assert_eq!(
        policy_code(
            executor
                .execute_authorized(
                    &lease(),
                    &unauthorized,
                    &request(),
                    &CancellationFlag::default()
                )
                .unwrap_err()
        ),
        "PAYLOAD_NOT_AUTHORIZED_ARTIFACT"
    );
}

#[test]
fn mandatory_backup_readback_and_write_count_are_verified() {
    for (adapter, expected) in [
        (
            MemoryAdapter {
                omit_backup: true,
                ..Default::default()
            },
            "MANDATORY_BACKUP_MISSING",
        ),
        (
            MemoryAdapter {
                corrupt_readback: true,
                ..Default::default()
            },
            "READBACK_HASH_MISMATCH",
        ),
        (
            MemoryAdapter {
                wrong_count: true,
                ..Default::default()
            },
            "ADAPTER_WRITE_COUNT_MISMATCH",
        ),
    ] {
        let mut executor = executor(adapter);
        let error = executor
            .execute_authorized(
                &lease(),
                &lease_context(),
                &request(),
                &CancellationFlag::default(),
            )
            .unwrap_err();
        assert_eq!(policy_code(error), expected);
    }
}

#[test]
fn cancellation_is_fail_closed_before_and_during_adapter() {
    let cancellation = CancellationFlag::default();
    cancellation.cancel();
    let mut executor = executor(MemoryAdapter::default());
    assert_eq!(
        policy_code(
            executor
                .execute_authorized(&lease(), &lease_context(), &request(), &cancellation)
                .unwrap_err()
        ),
        "EXECUTION_CANCELLED_BEFORE_CLAIM"
    );

    let mut executor = executor(MemoryAdapter {
        cancel_during: true,
        ..Default::default()
    });
    let error = executor
        .execute_authorized(
            &lease(),
            &lease_context(),
            &request(),
            &CancellationFlag::default(),
        )
        .unwrap_err();
    assert_eq!(policy_code(error), "EXECUTION_CANCELLED_DURING_ADAPTER");
}

#[test]
fn duplicate_adapter_identity_is_rejected() {
    let mut executor = BoundedExecutor::new(LeaseGuard::in_memory().unwrap());
    executor
        .register_adapter(Box::new(MemoryAdapter::default()))
        .unwrap();
    let error = executor
        .register_adapter(Box::new(MemoryAdapter::default()))
        .unwrap_err();
    assert_eq!(policy_code(error), "ADAPTER_ALREADY_REGISTERED");
}

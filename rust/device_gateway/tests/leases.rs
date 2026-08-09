use serde_json::{json, Value};
use std::collections::BTreeSet;
use techguy_device_gateway::{
    ExecutionLeaseContext, LeaseGuard, LeaseGuardError, ModeLeaseContext,
};
use tempfile::tempdir;

const SESSION: &str = "11111111-1111-4111-8111-111111111111";
const MODE_LEASE_ID: &str = "22222222-2222-4222-8222-222222222222";
const EXEC_LEASE_ID: &str = "33333333-3333-4333-8333-333333333333";
const RECIPE: &str = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const ARTIFACT: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const RANGE: &str = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
const NOW: &str = "2026-08-09T12:30:00Z";

fn envelope(contract_type: &str, authority: &str, single_use: bool, payload: Value) -> Value {
    json!({
        "schema_version": 1,
        "contract_type": contract_type,
        "contract_id": if contract_type == "mode_lease" {
            "44444444-4444-4444-8444-444444444444"
        } else {
            "55555555-5555-4555-8555-555555555555"
        },
        "producer": "repair.governor",
        "created_at": "2026-08-09T12:00:00Z",
        "physical_session_id": SESSION,
        "evidence_hashes": [],
        "confidence_bps": 10000,
        "expires_at": "2026-08-09T13:00:00Z",
        "authority": authority,
        "single_use": single_use,
        "consumed_at": null,
        "payload": payload
    })
}

fn mode_lease() -> Value {
    envelope(
        "mode_lease",
        "governance",
        false,
        json!({
            "lease_id": MODE_LEASE_ID,
            "mode": "board_service_fastboot",
            "reason_code": "MAIN_VERSION_REPAIR_ACTIVE",
            "reboot_allowed": false,
            "stock_fastboot_restore_allowed": false,
            "release_conditions": [
                "main_version_verified",
                "remaining_firmware_stages_completed",
                "target_boot_environment_ready"
            ],
            "released_at": null
        }),
    )
}

fn execution_lease() -> Value {
    envelope(
        "execution_lease",
        "execution",
        true,
        json!({
            "lease_id": EXEC_LEASE_ID,
            "recipe_hash": RECIPE,
            "adapter_id": "kirin.oeminfo.executor",
            "adapter_version": "1.0.0",
            "artifact_hashes": [ARTIFACT],
            "allowed_partitions": ["oeminfo", "version_a"],
            "range_manifest_sha256": RANGE,
            "max_write_bytes": 4096,
            "expected_mode": "board_service_fastboot",
            "stage_id": "restore.main-version",
            "reboot_allowed": false
        }),
    )
}

fn mode_context() -> ModeLeaseContext {
    ModeLeaseContext {
        physical_session_id: SESSION.to_owned(),
        current_mode: "board_service_fastboot".to_owned(),
        now: NOW.to_owned(),
        request_reboot: false,
        request_stock_fastboot_restore: false,
        satisfied_release_conditions: BTreeSet::new(),
    }
}

fn execution_context() -> ExecutionLeaseContext {
    ExecutionLeaseContext {
        physical_session_id: SESSION.to_owned(),
        recipe_hash: RECIPE.to_owned(),
        adapter_id: "kirin.oeminfo.executor".to_owned(),
        adapter_version: "1.0.0".to_owned(),
        artifact_hashes: vec![ARTIFACT.to_owned()],
        partition: "oeminfo".to_owned(),
        range_manifest_sha256: RANGE.to_owned(),
        write_bytes: 1024,
        current_mode: "board_service_fastboot".to_owned(),
        stage_id: "restore.main-version".to_owned(),
        request_reboot: false,
        now: NOW.to_owned(),
    }
}

fn assert_policy(error: LeaseGuardError, code: &str) {
    match error {
        LeaseGuardError::Policy(actual) => assert_eq!(actual, code),
        other => panic!("expected policy {code}, got {other}"),
    }
}

#[test]
fn active_mode_lease_preserves_service_fastboot() {
    let guard = LeaseGuard::in_memory().unwrap();
    let decision = guard.authorize_mode(&mode_lease(), &mode_context()).unwrap();
    assert_eq!(decision.lease_id, MODE_LEASE_ID);
    assert!(!decision.reboot_allowed);
    assert!(!decision.stock_fastboot_restore_allowed);
    assert!(!decision.release_ready);
}

#[test]
fn mode_lease_blocks_reboot() {
    let guard = LeaseGuard::in_memory().unwrap();
    let mut context = mode_context();
    context.request_reboot = true;
    assert_policy(
        guard.authorize_mode(&mode_lease(), &context).unwrap_err(),
        "REBOOT_BLOCKED_BY_ACTIVE_MODE_LEASE",
    );
}

#[test]
fn mode_lease_blocks_stock_fastboot_restore() {
    let guard = LeaseGuard::in_memory().unwrap();
    let mut context = mode_context();
    context.request_stock_fastboot_restore = true;
    assert_policy(
        guard.authorize_mode(&mode_lease(), &context).unwrap_err(),
        "STOCK_FASTBOOT_RESTORE_BLOCKED_BY_ACTIVE_MODE_LEASE",
    );
}

#[test]
fn mode_lease_rejects_wrong_mode_and_wrong_session() {
    let guard = LeaseGuard::in_memory().unwrap();
    let mut wrong_mode = mode_context();
    wrong_mode.current_mode = "normal_fastboot".to_owned();
    assert_policy(
        guard.authorize_mode(&mode_lease(), &wrong_mode).unwrap_err(),
        "MODE_MISMATCH",
    );

    let mut wrong_session = mode_context();
    wrong_session.physical_session_id = "99999999-9999-4999-8999-999999999999".to_owned();
    let error = guard.authorize_mode(&mode_lease(), &wrong_session).unwrap_err();
    assert!(matches!(error, LeaseGuardError::Contract(message) if message.contains("PHYSICAL_SESSION_MISMATCH")));
}

#[test]
fn mode_release_requires_every_condition() {
    let guard = LeaseGuard::in_memory().unwrap();
    let mut context = mode_context();
    context.satisfied_release_conditions.extend([
        "main_version_verified".to_owned(),
        "remaining_firmware_stages_completed".to_owned(),
    ]);
    assert!(!guard.authorize_mode(&mode_lease(), &context).unwrap().release_ready);
    context
        .satisfied_release_conditions
        .insert("target_boot_environment_ready".to_owned());
    assert!(guard.authorize_mode(&mode_lease(), &context).unwrap().release_ready);
}

#[test]
fn released_mode_lease_cannot_be_reused_as_active_authority() {
    let guard = LeaseGuard::in_memory().unwrap();
    let mut lease = mode_lease();
    lease["payload"]["released_at"] = json!("2026-08-09T12:20:00Z");
    assert_policy(
        guard.authorize_mode(&lease, &mode_context()).unwrap_err(),
        "MODE_LEASE_ALREADY_RELEASED",
    );
}

#[test]
fn execution_lease_claim_is_single_use_and_persistent() {
    let directory = tempdir().unwrap();
    let database = directory.path().join("leases.sqlite3");
    {
        let mut guard = LeaseGuard::open(&database).unwrap();
        let permit = guard
            .claim_execution(&execution_lease(), &execution_context())
            .unwrap();
        assert_eq!(permit.lease_id, EXEC_LEASE_ID);
        assert!(guard.is_execution_lease_consumed(EXEC_LEASE_ID).unwrap());
        assert_policy(
            guard
                .claim_execution(&execution_lease(), &execution_context())
                .unwrap_err(),
            "EXECUTION_LEASE_ALREADY_CONSUMED",
        );
    }
    let mut reopened = LeaseGuard::open(&database).unwrap();
    assert!(reopened.is_execution_lease_consumed(EXEC_LEASE_ID).unwrap());
    assert_policy(
        reopened
            .claim_execution(&execution_lease(), &execution_context())
            .unwrap_err(),
        "EXECUTION_LEASE_ALREADY_CONSUMED",
    );
}

#[test]
fn execution_lease_rejects_wrong_partition() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut context = execution_context();
    context.partition = "fastboot".to_owned();
    assert_policy(
        guard.claim_execution(&execution_lease(), &context).unwrap_err(),
        "PARTITION_NOT_AUTHORIZED",
    );
}

#[test]
fn execution_lease_rejects_wrong_mode() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut context = execution_context();
    context.current_mode = "qualcomm_firehose".to_owned();
    assert_policy(
        guard.claim_execution(&execution_lease(), &context).unwrap_err(),
        "MODE_MISMATCH",
    );
}

#[test]
fn execution_lease_rejects_oversized_and_zero_writes() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut oversized = execution_context();
    oversized.write_bytes = 4097;
    assert_policy(
        guard.claim_execution(&execution_lease(), &oversized).unwrap_err(),
        "WRITE_RANGE_EXCEEDS_LEASE",
    );
    let mut zero = execution_context();
    zero.write_bytes = 0;
    assert_policy(
        guard.claim_execution(&execution_lease(), &zero).unwrap_err(),
        "WRITE_RANGE_EXCEEDS_LEASE",
    );
}

#[test]
fn execution_lease_rejects_wrong_range_stage_adapter_and_version() {
    for (field, value, code) in [
        ("range", "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd", "RANGE_MANIFEST_MISMATCH"),
        ("stage", "restore.branding", "STAGE_MISMATCH"),
        ("adapter", "kirin.flash.executor", "ADAPTER_ID_MISMATCH"),
        ("version", "1.0.1", "ADAPTER_VERSION_MISMATCH"),
    ] {
        let mut guard = LeaseGuard::in_memory().unwrap();
        let mut context = execution_context();
        match field {
            "range" => context.range_manifest_sha256 = value.to_owned(),
            "stage" => context.stage_id = value.to_owned(),
            "adapter" => context.adapter_id = value.to_owned(),
            "version" => context.adapter_version = value.to_owned(),
            _ => unreachable!(),
        }
        assert_policy(guard.claim_execution(&execution_lease(), &context).unwrap_err(), code);
    }
}

#[test]
fn execution_lease_rejects_wrong_recipe_artifact_and_session() {
    let cases = ["recipe", "artifact", "session"];
    for case in cases {
        let mut guard = LeaseGuard::in_memory().unwrap();
        let mut context = execution_context();
        match case {
            "recipe" => context.recipe_hash = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd".to_owned(),
            "artifact" => context.artifact_hashes = vec!["dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd".to_owned()],
            "session" => context.physical_session_id = "99999999-9999-4999-8999-999999999999".to_owned(),
            _ => unreachable!(),
        }
        let error = guard.claim_execution(&execution_lease(), &context).unwrap_err();
        assert!(matches!(error, LeaseGuardError::Contract(_)));
    }
}

#[test]
fn execution_lease_rejects_unapproved_reboot() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut context = execution_context();
    context.request_reboot = true;
    assert_policy(
        guard.claim_execution(&execution_lease(), &context).unwrap_err(),
        "REBOOT_NOT_AUTHORIZED_BY_EXECUTION_LEASE",
    );
}

#[test]
fn execution_lease_rejects_expired_contract() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut lease = execution_lease();
    lease["expires_at"] = json!("2026-08-09T12:10:00Z");
    let error = guard.claim_execution(&lease, &execution_context()).unwrap_err();
    assert!(matches!(error, LeaseGuardError::Contract(message) if message.contains("CONTRACT_EXPIRED")));
}

#[test]
fn execution_context_rejects_unsorted_or_duplicate_artifacts() {
    let mut guard = LeaseGuard::in_memory().unwrap();
    let mut context = execution_context();
    context.artifact_hashes = vec![ARTIFACT.to_owned(), ARTIFACT.to_owned()];
    let error = guard.claim_execution(&execution_lease(), &context).unwrap_err();
    assert!(matches!(error, LeaseGuardError::InvalidContext(_)));
}

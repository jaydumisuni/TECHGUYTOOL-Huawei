from __future__ import annotations

import copy
from pathlib import Path

import pytest

from techguy_huawei.contracts import validate_contract
from techguy_huawei.decision_corps import (
    OFFICER_ORDER,
    DecisionError,
    OfficerDecision,
    build_operation_request,
    evaluate_decision,
    evaluate_replay_decision,
    govern_officer_decisions,
)
from techguy_huawei.kirin_xray import load_replay, render_replay

ROOT = Path(__file__).resolve().parents[1]
P10 = ROOT / "replay" / "kirin" / "p10_golden_workflow.json"
P30 = ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json"
RECIPE_HASH = "b" * 64
AUTH_HASH = "a" * 64


def _valid_decisions(*, recipe_hash: str | None = RECIPE_HASH) -> list[OfficerDecision]:
    return [
        OfficerDecision(officer_id, "allow_stage", f"{officer_id.replace('.', '_').upper()}_OK", False, recipe_hash)
        for officer_id in OFFICER_ORDER
    ]


def _operation_request_for_p30(*, physical_session_id: str | None = None) -> tuple[dict, object, dict]:
    replay = load_replay(P30)
    bundle = render_replay(replay)
    session_id = physical_session_id or bundle.physical_session_id
    request = build_operation_request(
        physical_session_id=session_id,
        operation="repair_main_version",
        requested_by="technician",
        authorization_reference_sha256=AUTH_HASH,
        target_profile_id="VOG-L29.C185",
        created_at=replay["clock"]["created_at"],
        expires_at=replay["clock"]["fresh_until"],
        evidence_hashes=[bundle.fixture_sha256],
    )
    return request, bundle, replay


def test_p30_exit_gate_blocks_premature_stock_fastboot_restore() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="restore_stock_fastboot",
        recipe_hash=RECIPE_HASH,
    )
    assert report.governor_decision.verdict == "block"
    assert report.governor_decision.veto is True
    by_officer = {decision.officer_id: decision for decision in report.officer_decisions}
    assert by_officer["safety.challenger"].verdict == "block"
    assert by_officer["safety.challenger"].veto is True
    assert by_officer["safety.challenger"].reason_code == "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED"


def test_p30_blocks_reboot_while_release_is_unresolved() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="reboot",
        recipe_hash=RECIPE_HASH,
    )
    assert report.governor_decision.verdict == "block"
    reasons = {decision.reason_code for decision in report.officer_decisions}
    assert "DEC_REBOOT_105_REBOOT_BLOCKED_BY_ACTIVE_MODE_REQUIREMENT" in reasons
    assert "SERVICE_ENVIRONMENT_RELEASE_NOT_PROVEN" in reasons
    assert "VERIFY_REQUIRED_BEFORE_RELEASE" in reasons


def test_p30_blocks_finalization_until_xray_certifies_release() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="finalize",
        recipe_hash=RECIPE_HASH,
    )
    assert report.governor_decision.verdict == "block"
    by_officer = {decision.officer_id: decision for decision in report.officer_decisions}
    assert by_officer["verification.judge"].veto is True
    assert by_officer["verification.judge"].reason_code == "VERIFY_REQUIRED_BEFORE_RELEASE"


def test_p30_allows_main_version_repair_stage_without_releasing_service_mode() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
        artifacts_ready=True,
    )
    assert report.governor_decision.verdict == "allow_stage"
    by_officer = {decision.officer_id: decision for decision in report.officer_decisions}
    assert by_officer["firmware.officer"].reason_code == "MAIN_VERSION_OEMINFO_REPAIR_REQUIRED"
    assert by_officer["route.planner"].reason_code == "SERVICE_ROUTE_SELECTED"
    assert by_officer["mode.officer"].reason_code == "SERVICE_ENTRY_EVIDENCE_AVAILABLE"


def test_p30_missing_artifact_stops_before_any_execution_authority() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
        artifacts_ready=False,
    )
    assert report.governor_decision.verdict == "need_artifact"
    assert report.governor_decision.reason_code == "DEC_ARTIFACT_104_COMPATIBLE_SERVICE_ARTIFACT_MISSING"
    assert report.to_dict()["execution_authority"] == "none"


def test_read_device_uses_observed_direct_read_route() -> None:
    report = evaluate_replay_decision(P30, operation="read_device", requested_action="inspect")
    assert report.governor_decision.verdict == "allow_stage"
    by_officer = {decision.officer_id: decision for decision in report.officer_decisions}
    assert by_officer["route.planner"].reason_code == "DIRECT_READ_ROUTE_AVAILABLE"


def test_p10_without_endpoint_needs_technician_for_read_route() -> None:
    report = evaluate_replay_decision(P10, operation="read_device", requested_action="inspect")
    assert report.governor_decision.verdict == "need_technician"
    assert report.governor_decision.reason_code == "DEC_DIRECT_101_DIRECT_ROUTE_UNAVAILABLE"


def test_p10_golden_replay_blocks_premature_finalization() -> None:
    report = evaluate_replay_decision(
        P10,
        operation="repair_oeminfo",
        requested_action="finalize",
        recipe_hash=RECIPE_HASH,
    )
    assert report.governor_decision.verdict == "block"
    assert report.governor_decision.veto is True


def test_unauthorized_service_endpoint_is_not_promoted_into_route_authority() -> None:
    replay = load_replay(P30)
    mutated = copy.deepcopy(replay)
    service = next(item for item in mutated["endpoints"] if item["transport"] == "huawei_usb_com_1_0")
    service["observed_state"] = "unauthorized"
    report = evaluate_replay_decision(
        mutated,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    assert report.governor_decision.verdict == "need_technician"
    by_officer = {decision.officer_id: decision for decision in report.officer_decisions}
    assert by_officer["mode.officer"].reason_code == "DEC_TESTPOINT_103_SERVICE_ENTRY_REQUIRED"
    assert by_officer["route.planner"].reason_code == "DEC_TESTPOINT_103_SERVICE_ENTRY_REQUIRED"


def test_majority_can_never_override_safety_veto() -> None:
    decisions = _valid_decisions()
    decisions[6] = OfficerDecision(
        "safety.challenger",
        "block",
        "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED",
        True,
        RECIPE_HASH,
    )
    governor = govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)
    assert governor.verdict == "block"
    assert governor.veto is True
    assert governor.reason_code == "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED"


def test_non_veto_officer_cannot_fabricate_hard_veto() -> None:
    decisions = _valid_decisions()
    decisions[5] = OfficerDecision("route.planner", "block", "ROUTE_BLOCK", True, RECIPE_HASH)
    with pytest.raises(DecisionError, match="UNAUTHORIZED_VETO"):
        govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)


def test_veto_must_be_a_block_verdict() -> None:
    decisions = _valid_decisions()
    decisions[6] = OfficerDecision("safety.challenger", "allow_stage", "BAD_VETO", True, RECIPE_HASH)
    with pytest.raises(DecisionError, match="INVALID_VETO_VERDICT"):
        govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)


def test_unknown_verdict_fails_closed_in_governor() -> None:
    decisions = _valid_decisions()
    decisions[2] = OfficerDecision("firmware.officer", "maybe", "UNKNOWN", False, RECIPE_HASH)
    with pytest.raises(DecisionError, match="UNKNOWN_VERDICT"):
        govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)


def test_incomplete_officer_set_fails_closed() -> None:
    with pytest.raises(DecisionError, match="OFFICER_SET_INVALID"):
        govern_officer_decisions(_valid_decisions()[:-1], recipe_hash=RECIPE_HASH)


def test_duplicate_or_reordered_officer_set_fails_closed() -> None:
    decisions = _valid_decisions()
    decisions[-1] = decisions[-2]
    with pytest.raises(DecisionError, match="OFFICER_ORDER_INVALID"):
        govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)


def test_officer_recipe_hash_must_match_governor_context() -> None:
    decisions = _valid_decisions()
    decisions[3] = OfficerDecision("artifact.officer", "allow_stage", "ARTIFACT_OK", False, "c" * 64)
    with pytest.raises(DecisionError, match="RECIPE_HASH_MISMATCH"):
        govern_officer_decisions(decisions, recipe_hash=RECIPE_HASH)


def test_decision_report_is_byte_deterministic() -> None:
    first = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    second = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    assert first.canonical == second.canonical
    assert first.sha256 == second.sha256


def test_every_officer_and_governor_output_is_a_valid_phase2_contract() -> None:
    replay = load_replay(P30)
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    for contract in (*report.decision_contracts, report.governor_contract):
        result = validate_contract(
            contract,
            context={
                "now": replay["clock"]["validation_now"],
                "expected_contract_type": "decision_verdict",
                "expected_physical_session_id": report.physical_session_id,
                "expected_authority": "governance",
            },
        )
        assert result.ok, result.as_dict()
        assert contract["authority"] == "governance"
        assert contract["producer"] == "repair.decision-corps"


def test_operation_request_is_bound_to_xray_physical_session() -> None:
    request, bundle, _ = _operation_request_for_p30()
    assert request["physical_session_id"] == bundle.physical_session_id
    assert request["authority"] == "planning"
    assert request["payload"]["request_state"] == "approved"


def test_mismatched_physical_session_fails_closed() -> None:
    request, bundle, replay = _operation_request_for_p30(
        physical_session_id="55555555-5555-4555-8555-555555555555"
    )
    with pytest.raises(DecisionError, match="INVALID_OPERATION_REQUEST"):
        evaluate_decision(
            operation_request=request,
            xray_bundle=bundle,
            requested_action="perform_operation",
            validation_now=replay["clock"]["validation_now"],
            expires_at=replay["clock"]["fresh_until"],
            recipe_hash=RECIPE_HASH,
        )


def test_unapproved_operation_request_fails_closed() -> None:
    request, bundle, replay = _operation_request_for_p30()
    request = copy.deepcopy(request)
    request["payload"]["request_state"] = "pending"
    with pytest.raises(DecisionError, match="OPERATION_NOT_APPROVED"):
        evaluate_decision(
            operation_request=request,
            xray_bundle=bundle,
            requested_action="perform_operation",
            validation_now=replay["clock"]["validation_now"],
            expires_at=replay["clock"]["fresh_until"],
            recipe_hash=RECIPE_HASH,
        )


def test_expired_operation_request_fails_closed() -> None:
    request, bundle, replay = _operation_request_for_p30()
    request = copy.deepcopy(request)
    request["expires_at"] = "2032-01-20T00:01:00Z"
    with pytest.raises(DecisionError, match="INVALID_OPERATION_REQUEST"):
        evaluate_decision(
            operation_request=request,
            xray_bundle=bundle,
            requested_action="perform_operation",
            validation_now=replay["clock"]["validation_now"],
            expires_at=replay["clock"]["fresh_until"],
            recipe_hash=RECIPE_HASH,
        )


def test_unknown_requested_action_fails_closed() -> None:
    with pytest.raises(DecisionError, match="UNSUPPORTED_REQUESTED_ACTION"):
        evaluate_replay_decision(
            P30,
            operation="repair_main_version",
            requested_action="magic_repair",
            recipe_hash=RECIPE_HASH,
        )


def test_unknown_operation_fails_closed() -> None:
    with pytest.raises(DecisionError, match="UNSUPPORTED_OPERATION"):
        evaluate_replay_decision(
            P30,
            operation="write_random_partition",
            requested_action="perform_operation",
        )


def test_phase5_report_explicitly_has_governance_only_authority() -> None:
    report = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    payload = report.to_dict()
    assert payload["decision_authority"] == "governance_only"
    assert payload["execution_authority"] == "none"
    assert payload["device_authority"] == "none"
    assert payload["touches_device"] is False


def test_decision_corps_source_has_no_device_execution_surface() -> None:
    source = (ROOT / "techguy_huawei" / "decision_corps.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "import subprocess",
        "fastboot flash",
        "fastboot erase",
        "adb reboot",
        "partition_write(",
        "write_oeminfo(",
        "serial.serial",
        "libusb",
        "execution_lease",
        "mode_lease",
    ):
        assert forbidden not in source

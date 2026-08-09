from __future__ import annotations

import copy
import hashlib
import uuid

import pytest

from techguy_huawei.contracts import validate_contract
from techguy_huawei.inquiry_governor import (
    LIFECYCLE,
    OFFICER_ORDER,
    REGISTERED_READ_ONLY_PROBES,
    InquiryError,
    evaluate_inquiry,
    plan_read_only_probes,
    validate_probe_ids,
)

SESSION = "11111111-1111-4111-8111-111111111111"
PREDICTION_ID = "22222222-2222-4222-8222-222222222222"
EXECUTOR_ID = "33333333-3333-4333-8333-333333333333"
VERIFICATION_ID = "44444444-4444-4444-8444-444444444444"
LEASE_ID = "55555555-5555-4555-8555-555555555555"
NOW = "2032-01-20T00:30:00Z"


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def executor(*, outcome: str = "accepted", readback: str | None = None, session: str = SESSION, stage: str = "restore_oeminfo_identity"):
    return {
        "schema_version": 1,
        "contract_type": "executor_result",
        "contract_id": EXECUTOR_ID,
        "producer": "bounded.executor",
        "created_at": NOW,
        "physical_session_id": session,
        "evidence_hashes": [h("executor-evidence")],
        "confidence_bps": 10000,
        "expires_at": None,
        "authority": "execution",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "lease_id": LEASE_ID,
            "stage_id": stage,
            "outcome": outcome,
            "raw_result_sha256": h("raw-result"),
            "readback_sha256": readback if readback is not None else h("readback"),
            "bytes_written": 4096 if outcome == "accepted" else 0,
        },
    }


def verification(*, verdict: str = "verified", readback_match: bool = True, subject: str = EXECUTOR_ID, session: str = SESSION):
    return {
        "schema_version": 1,
        "contract_type": "verification_result",
        "contract_id": VERIFICATION_ID,
        "producer": "xray.verifier",
        "created_at": NOW,
        "physical_session_id": session,
        "evidence_hashes": [h("verification-evidence")],
        "confidence_bps": 10000,
        "expires_at": None,
        "authority": "verification",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "subject_contract_id": subject,
            "verdict": verdict,
            "verification_code": "VERIFY_VERSION_302_MAIN_VERSION_RESTORED",
            "readback_match": readback_match,
            "observed_at": NOW,
        },
    }


def prediction(subject: str = "vog-l29-main-version"):
    return {
        "stage_id": "restore_oeminfo_identity",
        "expected_subjects": {subject: "observed"},
        "required_executor_outcome": "accepted",
        "require_readback_match": True,
    }


def evaluate(post, **kwargs):
    return evaluate_inquiry(
        physical_session_id=kwargs.pop("physical_session_id", SESSION),
        prediction_contract_id=kwargs.pop("prediction_contract_id", PREDICTION_ID),
        prediction=kwargs.pop("prediction", prediction()),
        executor_result=kwargs.pop("executor_result", executor()),
        verification_result=kwargs.pop("verification_result", verification()),
        post_evidence=post,
        created_at=NOW,
        source_evidence_hashes=[h("source-a"), h("source-b")],
        **kwargs,
    )


def test_verified_prediction_needs_no_gap_or_probe():
    report = evaluate({"vog-l29-main-version": "observed"})
    assert report.governor_status == "VERIFIED"
    assert report.knowledge_gap_contract is None
    assert report.learning_proposal_contract is None
    assert report.requested_probes == ()
    assert report.to_dict()["generic_retry_allowed"] is False


def test_p30_style_accepted_readback_but_main_version_missing_creates_gap():
    report = evaluate({"vog-l29-main-version": "missing"})
    assert report.governor_status == "KNOWLEDGE_GAP"
    assert report.knowledge_gap_contract["payload"]["gap_code"] == "EXPECTED_RESULT_NOT_OBSERVED"
    assert "xray.version.reread" in report.requested_probes
    assert "xray.identity.reread" in report.requested_probes


def test_missing_required_post_evidence_creates_structured_gap():
    report = evaluate({})
    assert report.knowledge_gap_contract["payload"]["gap_code"] == "REQUIRED_EVIDENCE_MISSING"
    assert report.governor_status == "KNOWLEDGE_GAP"


def test_contradiction_creates_explanation_gap_when_prediction_expects_coherent():
    pred = prediction("vog-l29-vendor-country-identity")
    pred["expected_subjects"] = {"vog-l29-vendor-country-identity": "coherent"}
    report = evaluate({"vog-l29-vendor-country-identity": "contradictory"}, prediction=pred)
    assert report.governor_status == "KNOWLEDGE_GAP"
    assert "xray.identity.reread" in report.requested_probes


def test_executor_rejection_stops_instead_of_creating_fake_learning_gap():
    result = executor(outcome="rejected", readback=None)
    result["payload"]["readback_sha256"] = None
    report = evaluate({"vog-l29-main-version": "missing"}, executor_result=result, verification_result=verification(verdict="failed", readback_match=False))
    assert report.governor_status == "STOP_EXECUTOR_RESULT"
    assert report.knowledge_gap_contract is None
    assert report.learning_proposal_contract is None


def test_failed_verification_after_accepted_executor_is_quarantined_gap():
    report = evaluate(
        {"vog-l29-main-version": "observed"},
        verification_result=verification(verdict="failed", readback_match=False),
    )
    assert report.governor_status == "KNOWLEDGE_GAP"
    assert report.knowledge_gap_contract is not None
    learning = next(item for item in report.officer_findings if item.officer_id == "learning.judge")
    assert learning.verdict == "quarantine_candidate"


def test_gap_contract_validates_against_frozen_phase2_contract():
    report = evaluate({"vog-l29-main-version": "missing"})
    result = validate_contract(
        report.knowledge_gap_contract,
        context={
            "now": NOW,
            "expected_contract_type": "knowledge_gap",
            "expected_physical_session_id": SESSION,
            "expected_authority": "learning",
        },
    )
    assert result.ok


def test_learning_proposal_is_quarantined_and_cannot_auto_promote():
    report = evaluate({"vog-l29-main-version": "missing"})
    proposal = report.learning_proposal_contract
    assert proposal["payload"]["status"] == "quarantined"
    assert proposal["payload"]["auto_promotion_allowed"] is False
    assert proposal["payload"]["change_kind"] == "diagnostic_rule"
    assert proposal["physical_session_id"] is None


def test_all_probe_registry_entries_are_read_only():
    assert REGISTERED_READ_ONLY_PROBES
    assert all(spec["write_allowed"] is False for spec in REGISTERED_READ_ONLY_PROBES.values())


def test_unknown_or_write_probe_cannot_be_requested():
    with pytest.raises(InquiryError, match="PROBE_NOT_REGISTERED"):
        validate_probe_ids(("xray.partition.write",))


def test_probe_plan_is_sorted_unique_and_deterministic():
    one = plan_read_only_probes(("main_version", "oeminfo_identity", "main_version"))
    two = plan_read_only_probes(("oeminfo_identity", "main_version"))
    assert one == two == tuple(sorted(set(one)))


def test_cross_session_executor_result_fails_closed():
    other = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    with pytest.raises(InquiryError, match="CONTRACT_INPUT_INVALID"):
        evaluate({"vog-l29-main-version": "observed"}, executor_result=executor(session=other))


def test_stage_mismatch_fails_closed():
    with pytest.raises(InquiryError, match="PREDICTION_STAGE_MISMATCH"):
        evaluate({"vog-l29-main-version": "observed"}, executor_result=executor(stage="continue_super"))


def test_verification_must_reference_executor_contract():
    with pytest.raises(InquiryError, match="VERIFICATION_SUBJECT_MISMATCH"):
        evaluate({"vog-l29-main-version": "observed"}, verification_result=verification(subject="66666666-6666-4666-8666-666666666666"))


def test_invalid_prediction_contract_id_fails_closed():
    with pytest.raises(InquiryError, match="PREDICTION_CONTRACT_ID_INVALID"):
        evaluate({"vog-l29-main-version": "observed"}, prediction_contract_id="not-a-uuid")


def test_officer_order_is_exact_and_complete():
    report = evaluate({"vog-l29-main-version": "missing"})
    assert tuple(item.officer_id for item in report.officer_findings) == OFFICER_ORDER


def test_report_is_deterministic():
    first = evaluate({"vog-l29-main-version": "missing"})
    second = evaluate({"vog-l29-main-version": "missing"})
    assert first.canonical == second.canonical
    assert first.sha256 == second.sha256


def test_lifecycle_order_is_monotonic_and_ttg_promotion_is_last():
    assert LIFECYCLE[0] == "observed"
    assert LIFECYCLE[1] == "questioned"
    assert LIFECYCLE[-1] == "ttg_promoted"

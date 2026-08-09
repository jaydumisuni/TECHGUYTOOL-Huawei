from __future__ import annotations

import hashlib
import uuid

import pytest

from techguy_huawei.knowledge_workshop import (
    DANGEROUS_CHANGE_KINDS,
    READ_ONLY_CHANGE_KINDS,
    WorkshopError,
    admit_learning_proposal,
    mark_ttg_promoted,
    promotion_candidate,
    record_canary,
    record_hardware_support,
    record_replay_support,
    reject,
    specialist_approve,
    validate_transition_path,
)

NOW = "2032-01-20T00:30:00Z"
GAP = "11111111-1111-4111-8111-111111111111"
PROPOSAL = "22222222-2222-4222-8222-222222222222"
CONTRACT = "33333333-3333-4333-8333-333333333333"


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def proposal(change_kind: str = "diagnostic_rule", *, auto: bool = False):
    return {
        "schema_version": 1,
        "contract_type": "learning_proposal",
        "contract_id": CONTRACT,
        "producer": "inquiry.governor",
        "created_at": NOW,
        "physical_session_id": None,
        "evidence_hashes": [h("gap")],
        "confidence_bps": None,
        "expires_at": None,
        "authority": "learning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "proposal_id": PROPOSAL,
            "gap_id": GAP,
            "change_kind": change_kind,
            "auto_promotion_allowed": auto,
            "replay_fixture_hashes": [h("origin-replay")],
            "status": "quarantined",
        },
    }


def replay(record):
    return record_replay_support(
        record,
        replay_fixture_hashes=[h("origin-replay"), h("challenge-replay")],
        regression_sha256=h("regression"),
        challenge_sha256=h("challenge"),
    )


def test_admission_is_quarantined_and_authority_free():
    record = admit_learning_proposal(proposal(), now=NOW)
    assert record.status == "quarantined"
    assert record.as_dict()["device_authority"] == "none"
    assert record.as_dict()["execution_authority"] == "none"


def test_diagnostic_rule_requires_replay_then_canary_before_hardware():
    admitted = admit_learning_proposal(proposal(), now=NOW)
    replayed = replay(admitted)
    with pytest.raises(WorkshopError, match="CANARY_REQUIRED"):
        record_hardware_support(replayed, hardware_proof_sha256=h("hardware"))
    canary = record_canary(replayed, canary_sha256=h("canary"))
    hardware = record_hardware_support(canary, hardware_proof_sha256=h("hardware"))
    approved = specialist_approve(hardware, approval_sha256=h("approval"))
    assert approved.status == "specialist_approved"


def test_read_only_parser_can_reach_specialist_after_replay_without_fake_hardware():
    admitted = admit_learning_proposal(proposal("read_only_parser", auto=True), now=NOW)
    replayed = replay(admitted)
    assert replayed.automatic_transition is True
    approved = specialist_approve(replayed, approval_sha256=h("approval"))
    assert approved.status == "specialist_approved"
    candidate = promotion_candidate(approved)
    assert candidate["includes_execution"] is False


def test_verification_requirement_needs_hardware_before_specialist_approval():
    admitted = admit_learning_proposal(proposal("verification_requirement"), now=NOW)
    replayed = replay(admitted)
    with pytest.raises(WorkshopError, match="WORKSHOP_STATUS_INVALID"):
        specialist_approve(replayed, approval_sha256=h("approval"))
    hardware = record_hardware_support(replayed, hardware_proof_sha256=h("hardware"))
    assert specialist_approve(hardware, approval_sha256=h("approval")).status == "specialist_approved"


@pytest.mark.parametrize("kind", sorted(DANGEROUS_CHANGE_KINDS))
def test_dangerous_change_classes_never_leave_quarantine(kind):
    admitted = admit_learning_proposal(proposal(kind), now=NOW)
    with pytest.raises(WorkshopError, match="DANGEROUS_CHANGE_QUARANTINED"):
        replay(admitted)


def test_phase2_contract_rejects_dangerous_auto_promotion():
    with pytest.raises(WorkshopError, match="LEARNING_PROPOSAL_INVALID"):
        admit_learning_proposal(proposal("write_target", auto=True), now=NOW)


def test_origin_replay_fixture_cannot_be_dropped():
    admitted = admit_learning_proposal(proposal("read_only_parser"), now=NOW)
    with pytest.raises(WorkshopError, match="ORIGIN_REPLAY_EVIDENCE_LOST"):
        record_replay_support(
            admitted,
            replay_fixture_hashes=[h("different")],
            regression_sha256=h("regression"),
            challenge_sha256=h("challenge"),
        )


def test_promotion_requires_specialist_approval():
    replayed = replay(admit_learning_proposal(proposal("read_only_parser"), now=NOW))
    with pytest.raises(WorkshopError, match="WORKSHOP_STATUS_INVALID"):
        mark_ttg_promoted(replayed, promotion_sha256=h("ttg"))


def test_ttg_promotion_remains_read_only():
    replayed = replay(admit_learning_proposal(proposal("read_only_parser"), now=NOW))
    approved = specialist_approve(replayed, approval_sha256=h("approval"))
    promoted = mark_ttg_promoted(approved, promotion_sha256=h("ttg"))
    assert promoted.status == "ttg_promoted"
    assert promoted.as_dict()["device_authority"] == "none"


def test_rejection_is_terminal_and_preserves_limitation():
    admitted = admit_learning_proposal(proposal(), now=NOW)
    rejected = reject(admitted, limitation="replay contradicted proposal")
    assert rejected.status == "rejected"
    assert rejected.evidence.limitations == ("replay contradicted proposal",)
    with pytest.raises(WorkshopError, match="TERMINAL_STATE"):
        reject(rejected, limitation="again")


def test_transition_history_rejects_identity_drift():
    admitted = admit_learning_proposal(proposal("read_only_parser"), now=NOW)
    replayed = replay(admitted)
    drifted = replayed.__class__(
        proposal_contract_id=str(uuid.uuid4()),
        gap_id=replayed.gap_id,
        change_kind=replayed.change_kind,
        status=replayed.status,
        evidence=replayed.evidence,
        automatic_transition=replayed.automatic_transition,
    )
    with pytest.raises(WorkshopError, match="WORKSHOP_IDENTITY_DRIFT"):
        validate_transition_path([admitted, drifted])


def test_read_only_change_set_and_dangerous_set_do_not_overlap():
    assert READ_ONLY_CHANGE_KINDS.isdisjoint(DANGEROUS_CHANGE_KINDS)


def test_records_are_deterministic():
    first = replay(admit_learning_proposal(proposal("read_only_parser"), now=NOW))
    second = replay(admit_learning_proposal(proposal("read_only_parser"), now=NOW))
    assert first.canonical == second.canonical
    assert first.sha256 == second.sha256

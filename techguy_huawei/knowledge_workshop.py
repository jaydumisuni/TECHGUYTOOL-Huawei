from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from .contracts import canonical_json, canonical_sha256, validate_contract

LIFECYCLE = (
    "quarantined",
    "replay_supported",
    "hardware_supported",
    "specialist_approved",
    "ttg_promoted",
    "rejected",
)
READ_ONLY_CHANGE_KINDS = frozenset({"read_only_parser", "diagnostic_rule", "verification_requirement"})
DANGEROUS_CHANGE_KINDS = frozenset({"write_target", "write_offset", "destructive_recipe", "expanded_authority"})


class WorkshopError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class WorkshopEvidence:
    replay_fixture_hashes: tuple[str, ...] = ()
    regression_sha256: str | None = None
    challenge_sha256: str | None = None
    canary_sha256: str | None = None
    hardware_proof_sha256: str | None = None
    specialist_approval_sha256: str | None = None
    ttg_promotion_sha256: str | None = None
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "replay_fixture_hashes": list(self.replay_fixture_hashes),
            "regression_sha256": self.regression_sha256,
            "challenge_sha256": self.challenge_sha256,
            "canary_sha256": self.canary_sha256,
            "hardware_proof_sha256": self.hardware_proof_sha256,
            "specialist_approval_sha256": self.specialist_approval_sha256,
            "ttg_promotion_sha256": self.ttg_promotion_sha256,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class WorkshopRecord:
    proposal_contract_id: str
    gap_id: str
    change_kind: str
    status: str
    evidence: WorkshopEvidence
    automatic_transition: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "techguytool-huawei.knowledge-workshop-record.v1",
            "proposal_contract_id": self.proposal_contract_id,
            "gap_id": self.gap_id,
            "change_kind": self.change_kind,
            "status": self.status,
            "automatic_transition": self.automatic_transition,
            "evidence": self.evidence.as_dict(),
            "authority": "read_only_learning",
            "execution_authority": "none",
            "device_authority": "none",
        }

    @property
    def canonical(self) -> str:
        return canonical_json(self.as_dict())

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.as_dict())


def admit_learning_proposal(contract: Mapping[str, Any], *, now: str) -> WorkshopRecord:
    result = validate_contract(
        contract,
        context={
            "now": now,
            "expected_contract_type": "learning_proposal",
            "expected_authority": "learning",
        },
    )
    if not result.ok:
        raise WorkshopError("LEARNING_PROPOSAL_INVALID", json.dumps(result.as_dict(), sort_keys=True))
    payload = contract["payload"]
    change_kind = str(payload["change_kind"])
    if change_kind not in READ_ONLY_CHANGE_KINDS | DANGEROUS_CHANGE_KINDS:
        raise WorkshopError("CHANGE_KIND_UNKNOWN", change_kind)
    if payload["status"] != "quarantined":
        raise WorkshopError("PROPOSAL_NOT_QUARANTINED", str(payload["status"]))
    if change_kind in DANGEROUS_CHANGE_KINDS and payload["auto_promotion_allowed"] is True:
        raise WorkshopError("DANGEROUS_AUTO_PROMOTION_FORBIDDEN", change_kind)
    replay = _hashes(payload["replay_fixture_hashes"], "replay_fixture_hashes")
    return WorkshopRecord(
        proposal_contract_id=str(contract["contract_id"]),
        gap_id=str(payload["gap_id"]),
        change_kind=change_kind,
        status="quarantined",
        evidence=WorkshopEvidence(replay_fixture_hashes=replay),
    )


def record_replay_support(
    record: WorkshopRecord,
    *,
    replay_fixture_hashes: Sequence[str],
    regression_sha256: str,
    challenge_sha256: str,
) -> WorkshopRecord:
    _require_status(record, "quarantined")
    if record.change_kind in DANGEROUS_CHANGE_KINDS:
        raise WorkshopError("DANGEROUS_CHANGE_QUARANTINED", record.change_kind)
    replay = _hashes(replay_fixture_hashes, "replay_fixture_hashes")
    if not replay:
        raise WorkshopError("REPLAY_PROOF_REQUIRED", "at least one replay fixture required")
    _sha(regression_sha256, "regression_sha256")
    _sha(challenge_sha256, "challenge_sha256")
    if not set(record.evidence.replay_fixture_hashes).issubset(replay):
        raise WorkshopError("ORIGIN_REPLAY_EVIDENCE_LOST", "admission fixtures must remain represented")
    return replace(
        record,
        status="replay_supported",
        evidence=replace(
            record.evidence,
            replay_fixture_hashes=replay,
            regression_sha256=regression_sha256,
            challenge_sha256=challenge_sha256,
        ),
        automatic_transition=record.change_kind == "read_only_parser",
    )


def record_canary(record: WorkshopRecord, *, canary_sha256: str) -> WorkshopRecord:
    _require_status(record, "replay_supported")
    if record.change_kind != "diagnostic_rule":
        raise WorkshopError("CANARY_NOT_APPLICABLE", record.change_kind)
    _sha(canary_sha256, "canary_sha256")
    return replace(record, evidence=replace(record.evidence, canary_sha256=canary_sha256), automatic_transition=False)


def record_hardware_support(record: WorkshopRecord, *, hardware_proof_sha256: str) -> WorkshopRecord:
    _require_status(record, "replay_supported")
    _sha(hardware_proof_sha256, "hardware_proof_sha256")
    if record.change_kind == "diagnostic_rule" and record.evidence.canary_sha256 is None:
        raise WorkshopError("CANARY_REQUIRED", record.change_kind)
    return replace(
        record,
        status="hardware_supported",
        evidence=replace(record.evidence, hardware_proof_sha256=hardware_proof_sha256),
        automatic_transition=False,
    )


def specialist_approve(record: WorkshopRecord, *, approval_sha256: str) -> WorkshopRecord:
    if record.change_kind == "read_only_parser":
        if record.status not in {"replay_supported", "hardware_supported"}:
            raise WorkshopError("SPECIALIST_APPROVAL_ORDER_INVALID", record.status)
    else:
        _require_status(record, "hardware_supported")
    _sha(approval_sha256, "specialist_approval_sha256")
    if record.change_kind in DANGEROUS_CHANGE_KINDS:
        raise WorkshopError("DANGEROUS_CHANGE_CANNOT_PROMOTE", record.change_kind)
    return replace(
        record,
        status="specialist_approved",
        evidence=replace(record.evidence, specialist_approval_sha256=approval_sha256),
        automatic_transition=False,
    )


def mark_ttg_promoted(record: WorkshopRecord, *, promotion_sha256: str) -> WorkshopRecord:
    _require_status(record, "specialist_approved")
    _sha(promotion_sha256, "ttg_promotion_sha256")
    if record.change_kind not in READ_ONLY_CHANGE_KINDS:
        raise WorkshopError("NON_READ_ONLY_PROMOTION_FORBIDDEN", record.change_kind)
    return replace(
        record,
        status="ttg_promoted",
        evidence=replace(record.evidence, ttg_promotion_sha256=promotion_sha256),
        automatic_transition=False,
    )


def reject(record: WorkshopRecord, *, limitation: str) -> WorkshopRecord:
    if record.status in {"ttg_promoted", "rejected"}:
        raise WorkshopError("TERMINAL_STATE", record.status)
    if not isinstance(limitation, str) or not limitation.strip():
        raise WorkshopError("LIMITATION_REQUIRED", repr(limitation))
    limitations = tuple(sorted(set(record.evidence.limitations + (limitation.strip(),))))
    return replace(record, status="rejected", evidence=replace(record.evidence, limitations=limitations), automatic_transition=False)


def promotion_candidate(record: WorkshopRecord) -> dict[str, Any]:
    _require_status(record, "specialist_approved")
    if record.change_kind not in READ_ONLY_CHANGE_KINDS:
        raise WorkshopError("NON_READ_ONLY_PROMOTION_FORBIDDEN", record.change_kind)
    return {
        "schema": "techguytool-huawei.xray-promotion-candidate.v1",
        "proposal_contract_id": record.proposal_contract_id,
        "gap_id": record.gap_id,
        "change_kind": record.change_kind,
        "workshop_record_sha256": record.sha256,
        "includes_execution": False,
        "device_authority": "none",
        "status": "SPECIALIST_APPROVED_PENDING_PHASE13",
    }


def validate_transition_path(records: Sequence[WorkshopRecord]) -> None:
    if not records:
        raise WorkshopError("WORKSHOP_HISTORY_EMPTY", "at least one record required")
    first = records[0]
    if first.status != "quarantined":
        raise WorkshopError("WORKSHOP_HISTORY_START_INVALID", first.status)
    for left, right in zip(records, records[1:]):
        if left.proposal_contract_id != right.proposal_contract_id or left.gap_id != right.gap_id or left.change_kind != right.change_kind:
            raise WorkshopError("WORKSHOP_IDENTITY_DRIFT", right.status)
        if right.status == left.status:
            continue
        allowed = {
            "quarantined": {"replay_supported", "rejected"},
            "replay_supported": {"hardware_supported", "specialist_approved", "rejected"},
            "hardware_supported": {"specialist_approved", "rejected"},
            "specialist_approved": {"ttg_promoted", "rejected"},
            "ttg_promoted": set(),
            "rejected": set(),
        }[left.status]
        if right.status not in allowed:
            raise WorkshopError("WORKSHOP_TRANSITION_INVALID", f"{left.status}->{right.status}")


def _require_status(record: WorkshopRecord, expected: str) -> None:
    if record.status != expected:
        raise WorkshopError("WORKSHOP_STATUS_INVALID", f"expected {expected}, got {record.status}")


def _sha(value: str, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise WorkshopError("EVIDENCE_HASH_INVALID", label)
    try:
        int(value, 16)
    except ValueError as exc:
        raise WorkshopError("EVIDENCE_HASH_INVALID", label) from exc
    if value.lower() != value:
        raise WorkshopError("EVIDENCE_HASH_INVALID", label)
    return value


def _hashes(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise WorkshopError("EVIDENCE_HASH_SET_INVALID", label)
    result = tuple(sorted(set(_sha(str(value), label) for value in values)))
    if len(result) != len(values):
        raise WorkshopError("EVIDENCE_HASH_SET_NONCANONICAL", label)
    return result

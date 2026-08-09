from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import canonical_json, canonical_sha256, validate_contract

PRODUCER = "inquiry.governor"
REPORT_SCHEMA = "techguytool-huawei.inquiry-report.v1"
LIFECYCLE = (
    "observed",
    "questioned",
    "candidate",
    "replay_supported",
    "hardware_supported",
    "specialist_approved",
    "ttg_promoted",
)
OFFICER_ORDER = (
    "prediction.auditor",
    "evidence.completeness",
    "contradiction.officer",
    "probe.planner",
    "hypothesis.officer",
    "challenger",
    "learning.judge",
    "inquiry.governor",
)
REGISTERED_READ_ONLY_PROBES: dict[str, dict[str, object]] = {
    "xray.branding.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.firmware.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.identity.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.partition_inventory.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.security.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.storage.reread": {"authority": "diagnosis", "write_allowed": False},
    "xray.transport.reread": {"authority": "observation", "write_allowed": False},
    "xray.version.reread": {"authority": "diagnosis", "write_allowed": False},
}
VALID_POST_VERDICTS = frozenset({"observed", "coherent", "contradictory", "missing", "unknown"})


class InquiryError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class InquiryPrediction:
    stage_id: str
    expected_subjects: tuple[tuple[str, str], ...]
    required_executor_outcome: str = "accepted"
    require_readback_match: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "InquiryPrediction":
        allowed = {
            "stage_id",
            "expected_subjects",
            "required_executor_outcome",
            "require_readback_match",
        }
        if set(value) - allowed:
            raise InquiryError("PREDICTION_FIELD_UNKNOWN", repr(sorted(set(value) - allowed)))
        stage_id = value.get("stage_id")
        subjects = value.get("expected_subjects")
        outcome = value.get("required_executor_outcome", "accepted")
        readback = value.get("require_readback_match", True)
        if not isinstance(stage_id, str) or not stage_id:
            raise InquiryError("PREDICTION_STAGE_INVALID", repr(stage_id))
        if not isinstance(subjects, Mapping) or not subjects:
            raise InquiryError("PREDICTION_SUBJECTS_INVALID", "non-empty mapping required")
        normalized: list[tuple[str, str]] = []
        for subject, verdict in subjects.items():
            if not isinstance(subject, str) or not subject:
                raise InquiryError("PREDICTION_SUBJECT_INVALID", repr(subject))
            if verdict not in {"observed", "coherent"}:
                raise InquiryError("PREDICTION_VERDICT_INVALID", f"{subject}={verdict!r}")
            normalized.append((subject, str(verdict)))
        if outcome not in {"accepted", "rejected", "interrupted", "failed"}:
            raise InquiryError("PREDICTION_EXECUTOR_OUTCOME_INVALID", repr(outcome))
        if not isinstance(readback, bool):
            raise InquiryError("PREDICTION_READBACK_POLICY_INVALID", repr(readback))
        return cls(stage_id, tuple(sorted(normalized)), str(outcome), readback)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "expected_subjects": dict(self.expected_subjects),
            "required_executor_outcome": self.required_executor_outcome,
            "require_readback_match": self.require_readback_match,
        }


@dataclass(frozen=True, slots=True)
class OfficerFinding:
    officer_id: str
    verdict: str
    reason_codes: tuple[str, ...]
    details: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "officer_id": self.officer_id,
            "verdict": self.verdict,
            "reason_codes": list(self.reason_codes),
            "details": list(self.details),
        }


@dataclass(frozen=True, slots=True)
class InquiryReport:
    physical_session_id: str
    prediction_contract_id: str
    prediction: InquiryPrediction
    executor_result: Mapping[str, Any]
    verification_result: Mapping[str, Any]
    post_evidence: Mapping[str, str]
    officer_findings: tuple[OfficerFinding, ...]
    governor_status: str
    requested_probes: tuple[str, ...]
    knowledge_gap_contract: Mapping[str, Any] | None
    learning_proposal_contract: Mapping[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "physical_session_id": self.physical_session_id,
            "prediction_contract_id": self.prediction_contract_id,
            "prediction": self.prediction.as_dict(),
            "executor_result_contract_id": self.executor_result["contract_id"],
            "verification_result_contract_id": self.verification_result["contract_id"],
            "post_evidence": dict(sorted(self.post_evidence.items())),
            "officer_findings": [item.as_dict() for item in self.officer_findings],
            "governor_status": self.governor_status,
            "requested_probes": list(self.requested_probes),
            "knowledge_gap_contract": dict(self.knowledge_gap_contract) if self.knowledge_gap_contract else None,
            "learning_proposal_contract": dict(self.learning_proposal_contract) if self.learning_proposal_contract else None,
            "probe_authority": "registered_read_only_only",
            "learning_authority": "quarantine_only",
            "execution_authority": "none",
            "device_authority": "none",
            "generic_retry_allowed": False,
            "touches_device": False,
        }

    @property
    def canonical(self) -> str:
        return canonical_json(self.to_dict())

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_dict())


def evaluate_inquiry(
    *,
    physical_session_id: str,
    prediction_contract_id: str,
    prediction: Mapping[str, Any],
    executor_result: Mapping[str, Any],
    verification_result: Mapping[str, Any],
    post_evidence: Mapping[str, str],
    created_at: str,
    source_evidence_hashes: Sequence[str] = (),
) -> InquiryReport:
    _require_uuid(physical_session_id, "PHYSICAL_SESSION_ID_INVALID")
    _require_uuid(prediction_contract_id, "PREDICTION_CONTRACT_ID_INVALID")
    pred = InquiryPrediction.from_mapping(prediction)
    _validate_contract_input(executor_result, "executor_result", physical_session_id, created_at)
    _validate_contract_input(verification_result, "verification_result", physical_session_id, created_at)
    if executor_result["payload"]["stage_id"] != pred.stage_id:
        raise InquiryError("PREDICTION_STAGE_MISMATCH", str(executor_result["payload"]["stage_id"]))
    if verification_result["payload"]["subject_contract_id"] != executor_result["contract_id"]:
        raise InquiryError("VERIFICATION_SUBJECT_MISMATCH", str(verification_result["payload"]["subject_contract_id"]))
    normalized_post = _normalize_post_evidence(post_evidence)

    missing_subjects = tuple(subject for subject, _ in pred.expected_subjects if subject not in normalized_post)
    mismatched_subjects = tuple(
        subject
        for subject, expected in pred.expected_subjects
        if subject in normalized_post and normalized_post[subject] != expected
    )
    contradictory_subjects = tuple(
        subject for subject, verdict in normalized_post.items() if verdict == "contradictory"
    )
    executor_outcome = executor_result["payload"]["outcome"]
    verification = verification_result["payload"]
    readback_ok = verification["readback_match"] is True and executor_result["payload"].get("readback_sha256") is not None

    findings: list[OfficerFinding] = []
    findings.append(
        _finding(
            "prediction.auditor",
            "match" if not mismatched_subjects and not missing_subjects else "question",
            () if not mismatched_subjects and not missing_subjects else ("INQ_PREDICTION_401_EXPECTED_RESULT_NOT_OBSERVED",),
            mismatched_subjects + missing_subjects,
        )
    )
    findings.append(
        _finding(
            "evidence.completeness",
            "complete" if not missing_subjects else "question",
            () if not missing_subjects else ("INQ_EVIDENCE_402_REQUIRED_EVIDENCE_MISSING",),
            missing_subjects,
        )
    )
    findings.append(
        _finding(
            "contradiction.officer",
            "coherent" if not contradictory_subjects else "question",
            () if not contradictory_subjects else ("INQ_KNOWLEDGE_403_XRAY_EXPLANATION_INCOMPLETE",),
            contradictory_subjects,
        )
    )

    probes = plan_read_only_probes(missing_subjects + mismatched_subjects + contradictory_subjects)
    findings.append(
        _finding(
            "probe.planner",
            "none_required" if not probes else "read_only_probe_plan",
            () if not probes else ("INQ_PROBE_404_ADDITIONAL_READ_ONLY_PROBE_REQUIRED",),
            probes,
        )
    )

    hypotheses = _hypotheses(missing_subjects, mismatched_subjects, contradictory_subjects, readback_ok)
    findings.append(_finding("hypothesis.officer", "none" if not hypotheses else "candidate", hypotheses))

    explained_executor_failure = executor_outcome != pred.required_executor_outcome
    unexplained_after_accepted = (
        executor_outcome == pred.required_executor_outcome
        and (not missing_subjects)
        and bool(mismatched_subjects or contradictory_subjects)
        and (not pred.require_readback_match or readback_ok)
    )
    findings.append(
        _finding(
            "challenger",
            "stop" if explained_executor_failure else ("gap" if unexplained_after_accepted else "satisfied"),
            ("EXECUTOR_OUTCOME_NOT_AS_PREDICTED",) if explained_executor_failure else (
                ("INQ_KNOWLEDGE_403_XRAY_EXPLANATION_INCOMPLETE",) if unexplained_after_accepted else ()
            ),
        )
    )

    needs_gap = bool(missing_subjects or mismatched_subjects or contradictory_subjects)
    if explained_executor_failure:
        needs_gap = False
    findings.append(
        _finding(
            "learning.judge",
            "quarantine_candidate" if needs_gap else "no_learning",
            ("LEARNING_QUARANTINE_REQUIRED",) if needs_gap else (),
        )
    )

    if explained_executor_failure:
        governor_status = "STOP_EXECUTOR_RESULT"
        gap_code = None
    elif missing_subjects:
        governor_status = "KNOWLEDGE_GAP"
        gap_code = "REQUIRED_EVIDENCE_MISSING"
    elif mismatched_subjects:
        governor_status = "KNOWLEDGE_GAP"
        gap_code = "EXPECTED_RESULT_NOT_OBSERVED"
    elif contradictory_subjects:
        governor_status = "KNOWLEDGE_GAP"
        gap_code = "XRAY_EXPLANATION_INCOMPLETE"
    elif verification["verdict"] != "verified" or (pred.require_readback_match and not readback_ok):
        governor_status = "KNOWLEDGE_GAP"
        gap_code = "EXPECTED_RESULT_NOT_OBSERVED"
        probes = plan_read_only_probes(tuple(subject for subject, _ in pred.expected_subjects))
    else:
        governor_status = "VERIFIED"
        gap_code = None

    findings.append(
        _finding(
            "inquiry.governor",
            governor_status.lower(),
            () if gap_code is None else (gap_code,),
            probes,
        )
    )
    if tuple(item.officer_id for item in findings) != OFFICER_ORDER:
        raise InquiryError("OFFICER_ORDER_INVALID", repr([item.officer_id for item in findings]))

    gap_contract = None
    proposal_contract = None
    if gap_code is not None:
        if not probes:
            probes = ("xray.transport.reread",)
        validate_probe_ids(probes)
        gap_contract = _knowledge_gap_contract(
            physical_session_id=physical_session_id,
            prediction_contract_id=prediction_contract_id,
            executor_result_contract_id=str(executor_result["contract_id"]),
            verification_contract_id=str(verification_result["contract_id"]),
            gap_code=gap_code,
            requested_probes=probes,
            created_at=created_at,
            evidence_hashes=source_evidence_hashes,
        )
        snapshot_hash = canonical_sha256(
            {
                "prediction": pred.as_dict(),
                "executor_result": executor_result,
                "verification_result": verification_result,
                "post_evidence": normalized_post,
            }
        )
        proposal_contract = _learning_proposal_contract(
            gap_id=str(gap_contract["payload"]["gap_id"]),
            snapshot_hash=snapshot_hash,
            created_at=created_at,
            evidence_hashes=(canonical_sha256(gap_contract),),
        )

    return InquiryReport(
        physical_session_id=physical_session_id,
        prediction_contract_id=prediction_contract_id,
        prediction=pred,
        executor_result=dict(executor_result),
        verification_result=dict(verification_result),
        post_evidence=normalized_post,
        officer_findings=tuple(findings),
        governor_status=governor_status,
        requested_probes=tuple(probes),
        knowledge_gap_contract=gap_contract,
        learning_proposal_contract=proposal_contract,
    )


def plan_read_only_probes(subjects: Sequence[str]) -> tuple[str, ...]:
    probes: set[str] = set()
    for subject in subjects:
        lowered = subject.lower()
        if any(token in lowered for token in ("version", "verlist", "main_version")):
            probes.update({"xray.version.reread", "xray.identity.reread"})
        if any(token in lowered for token in ("identity", "oeminfo", "vendor", "country")):
            probes.update({"xray.identity.reread", "xray.version.reread"})
        if any(token in lowered for token in ("partition", "storage", "super")):
            probes.update({"xray.partition_inventory.reread", "xray.storage.reread"})
        if any(token in lowered for token in ("branding", "model")):
            probes.update({"xray.branding.reread", "xray.identity.reread"})
        if any(token in lowered for token in ("security", "lock", "bootloader")):
            probes.update({"xray.security.reread", "xray.transport.reread"})
        if any(token in lowered for token in ("firmware", "cust", "preload", "base")):
            probes.add("xray.firmware.reread")
    if subjects and not probes:
        probes.update({"xray.identity.reread", "xray.transport.reread"})
    result = tuple(sorted(probes))
    validate_probe_ids(result)
    return result


def validate_probe_ids(probes: Sequence[str]) -> None:
    if len(probes) != len(set(probes)) or tuple(probes) != tuple(sorted(probes)):
        raise InquiryError("PROBE_SET_NONCANONICAL", repr(probes))
    for probe in probes:
        spec = REGISTERED_READ_ONLY_PROBES.get(probe)
        if spec is None:
            raise InquiryError("PROBE_NOT_REGISTERED", probe)
        if spec.get("write_allowed") is not False:
            raise InquiryError("WRITE_PROBE_FORBIDDEN", probe)


def _knowledge_gap_contract(
    *,
    physical_session_id: str,
    prediction_contract_id: str,
    executor_result_contract_id: str,
    verification_contract_id: str,
    gap_code: str,
    requested_probes: Sequence[str],
    created_at: str,
    evidence_hashes: Sequence[str],
) -> dict[str, Any]:
    namespace = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"urn:thetechguy:inquiry:{physical_session_id}:{prediction_contract_id}:{executor_result_contract_id}:{verification_contract_id}:{gap_code}",
    )
    gap_id = str(uuid.uuid5(namespace, "gap"))
    contract = {
        "schema_version": 1,
        "contract_type": "knowledge_gap",
        "contract_id": str(uuid.uuid5(namespace, "contract")),
        "producer": PRODUCER,
        "created_at": created_at,
        "physical_session_id": physical_session_id,
        "evidence_hashes": sorted(set(evidence_hashes)),
        "confidence_bps": 10000,
        "expires_at": None,
        "authority": "learning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "gap_id": gap_id,
            "prediction_contract_id": prediction_contract_id,
            "executor_result_contract_id": executor_result_contract_id,
            "verification_contract_id": verification_contract_id,
            "gap_code": gap_code,
            "requested_probes": list(requested_probes),
            "lifecycle_status": "questioned",
        },
    }
    _require_valid_contract(contract, "knowledge_gap", physical_session_id, created_at)
    return contract


def _learning_proposal_contract(
    *,
    gap_id: str,
    snapshot_hash: str,
    created_at: str,
    evidence_hashes: Sequence[str],
) -> dict[str, Any]:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"urn:thetechguy:learning-proposal:{gap_id}:{snapshot_hash}")
    contract = {
        "schema_version": 1,
        "contract_type": "learning_proposal",
        "contract_id": str(uuid.uuid5(namespace, "contract")),
        "producer": PRODUCER,
        "created_at": created_at,
        "physical_session_id": None,
        "evidence_hashes": sorted(set(evidence_hashes)),
        "confidence_bps": None,
        "expires_at": None,
        "authority": "learning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "proposal_id": str(uuid.uuid5(namespace, "proposal")),
            "gap_id": gap_id,
            "change_kind": "diagnostic_rule",
            "auto_promotion_allowed": False,
            "replay_fixture_hashes": [snapshot_hash],
            "status": "quarantined",
        },
    }
    result = validate_contract(
        contract,
        context={"now": created_at, "expected_contract_type": "learning_proposal", "expected_authority": "learning"},
    )
    if not result.ok:
        raise InquiryError("LEARNING_PROPOSAL_INVALID", json.dumps(result.as_dict(), sort_keys=True))
    return contract


def _validate_contract_input(contract: Mapping[str, Any], contract_type: str, session_id: str, now: str) -> None:
    _require_valid_contract(contract, contract_type, session_id, now)


def _require_valid_contract(contract: Mapping[str, Any], contract_type: str, session_id: str, now: str) -> None:
    result = validate_contract(
        contract,
        context={
            "now": now,
            "expected_contract_type": contract_type,
            "expected_physical_session_id": session_id,
        },
    )
    if not result.ok:
        raise InquiryError("CONTRACT_INPUT_INVALID", json.dumps(result.as_dict(), sort_keys=True))


def _normalize_post_evidence(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise InquiryError("POST_EVIDENCE_INVALID", "mapping required")
    result: dict[str, str] = {}
    for subject, verdict in value.items():
        if not isinstance(subject, str) or not subject:
            raise InquiryError("POST_EVIDENCE_SUBJECT_INVALID", repr(subject))
        if verdict not in VALID_POST_VERDICTS:
            raise InquiryError("POST_EVIDENCE_VERDICT_INVALID", f"{subject}={verdict!r}")
        result[subject] = verdict
    return result


def _hypotheses(
    missing: Sequence[str], mismatched: Sequence[str], contradictory: Sequence[str], readback_ok: bool
) -> tuple[str, ...]:
    values: set[str] = set()
    if missing:
        values.add("POST_READ_EVIDENCE_INCOMPLETE")
    if mismatched and readback_ok:
        values.update({"STATE_LOCATION_ASSUMPTION_UNPROVEN", "TARGET_RECORD_DEPENDENCY_INCOMPLETE"})
    if contradictory:
        values.add("XRAY_EXPLANATION_CONTRADICTORY")
    return tuple(sorted(values))


def _finding(
    officer_id: str,
    verdict: str,
    reason_codes: Sequence[str] = (),
    details: Sequence[str] = (),
) -> OfficerFinding:
    return OfficerFinding(officer_id, verdict, tuple(reason_codes), tuple(details))


def _require_uuid(value: str, code: str) -> None:
    try:
        parsed = uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InquiryError(code, repr(value)) from exc
    if str(parsed) != str(value).lower():
        raise InquiryError(code, repr(value))

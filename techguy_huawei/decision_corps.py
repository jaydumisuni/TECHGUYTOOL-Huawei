from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import canonical_json, canonical_sha256, validate_contract
from .kirin_xray import ReplayBundle, load_replay, render_replay

PRODUCER_ID = "repair.decision-corps"
REPORT_SCHEMA = "techguytool-huawei.repair-decision-report.v1"

OFFICER_ORDER = (
    "identity.officer",
    "mode.officer",
    "firmware.officer",
    "artifact.officer",
    "recovery.officer",
    "route.planner",
    "safety.challenger",
    "verification.judge",
)
VETO_OFFICERS = frozenset(
    {
        "identity.officer",
        "recovery.officer",
        "safety.challenger",
        "verification.judge",
    }
)
ALLOWED_VERDICTS = frozenset(
    {"allow_stage", "block", "investigate", "need_artifact", "need_technician"}
)
REQUESTED_ACTIONS = frozenset(
    {"inspect", "perform_operation", "reboot", "restore_stock_fastboot", "finalize"}
)
RELEASE_ACTIONS = frozenset({"reboot", "restore_stock_fastboot", "finalize"})
SUPPORTED_OPERATIONS = frozenset(
    {
        "read_device",
        "repair_main_version",
        "restore_branding",
        "repair_oeminfo",
        "backup",
        "restore",
        "flash_retail",
        "flash_board",
    }
)
USABLE_ENDPOINT_STATES = frozenset({"available", "authorized", "recovery", "service"})
SERVICE_ENDPOINT_STATES = frozenset({"authorized", "service"})


class DecisionError(ValueError):
    """Fail-closed Decision Corps input, authority, or aggregation error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class EndpointEvidence:
    """Normalized read-only endpoint evidence supplied by Xray."""

    transport: str
    observed_state: str
    capability_ids: frozenset[str]

    @property
    def usable(self) -> bool:
        return self.observed_state in USABLE_ENDPOINT_STATES

    @property
    def service_ready(self) -> bool:
        return self.observed_state in SERVICE_ENDPOINT_STATES


@dataclass(frozen=True, slots=True)
class DecisionEvidence:
    """One immutable evidence snapshot shared by every deterministic officer."""

    evidence: Mapping[str, str]
    endpoints: tuple[EndpointEvidence, ...]
    twin: Mapping[str, Any]
    safety: Mapping[str, Any]

    def endpoints_for(self, transport: str) -> tuple[EndpointEvidence, ...]:
        return tuple(item for item in self.endpoints if item.transport == transport)

    def has_usable_endpoint(self) -> bool:
        return any(item.usable for item in self.endpoints)

    def has_service_entry(self) -> bool:
        return any(
            item.transport in {"huawei_usb_com_1_0", "board_service_fastboot"}
            and item.service_ready
            for item in self.endpoints
        )


@dataclass(frozen=True, slots=True)
class OfficerDecision:
    """One deterministic officer verdict before Governor aggregation."""

    officer_id: str
    verdict: str
    reason_code: str
    veto: bool
    recipe_hash: str | None

    def payload(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "officer_id": self.officer_id,
            "reason_code": self.reason_code,
            "veto": self.veto,
            "recipe_hash": self.recipe_hash,
        }


@dataclass(frozen=True, slots=True)
class DecisionReport:
    """Deterministic Phase 5 report; it carries governance but no device authority."""

    scenario_id: str
    physical_session_id: str
    requested_action: str
    operation_request: dict[str, Any]
    officer_decisions: tuple[OfficerDecision, ...]
    decision_contracts: tuple[dict[str, Any], ...]
    governor_decision: OfficerDecision
    governor_contract: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "scenario_id": self.scenario_id,
            "physical_session_id": self.physical_session_id,
            "requested_action": self.requested_action,
            "operation_request": dict(self.operation_request),
            "officer_decisions": [decision.payload() for decision in self.officer_decisions],
            "decision_contracts": [dict(contract) for contract in self.decision_contracts],
            "governor_decision": self.governor_decision.payload(),
            "governor_contract": dict(self.governor_contract),
            "decision_authority": "governance_only",
            "execution_authority": "none",
            "device_authority": "none",
            "touches_device": False,
        }

    @property
    def canonical(self) -> str:
        return canonical_json(self.to_dict())

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_dict())


def build_operation_request(
    *,
    physical_session_id: str,
    operation: str,
    requested_by: str,
    authorization_reference_sha256: str,
    target_profile_id: str,
    created_at: str,
    expires_at: str,
    evidence_hashes: Sequence[str] = (),
) -> dict[str, Any]:
    """Build one deterministic approved Phase 2 operation_request contract."""

    if operation not in SUPPORTED_OPERATIONS:
        raise DecisionError("UNSUPPORTED_OPERATION", f"unsupported operation {operation!r}")
    namespace = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"urn:thetechguy:operation-request:{physical_session_id}:{operation}:{target_profile_id}",
    )
    contract = {
        "schema_version": 1,
        "contract_type": "operation_request",
        "contract_id": str(uuid.uuid5(namespace, authorization_reference_sha256)),
        "producer": "technician.intent",
        "created_at": created_at,
        "physical_session_id": physical_session_id,
        "evidence_hashes": sorted(set(evidence_hashes)),
        "confidence_bps": 10000,
        "expires_at": expires_at,
        "authority": "planning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "operation": operation,
            "requested_by": requested_by,
            "authorization_reference_sha256": authorization_reference_sha256,
            "target_profile_id": target_profile_id,
            "request_state": "approved",
        },
    }
    result = validate_contract(
        contract,
        context={
            "now": created_at,
            "expected_contract_type": "operation_request",
            "expected_physical_session_id": physical_session_id,
            "expected_authority": "planning",
        },
    )
    if not result.ok:
        raise DecisionError("INVALID_OPERATION_REQUEST", json.dumps(result.as_dict(), sort_keys=True))
    return contract


def evaluate_replay_decision(
    source: Mapping[str, Any] | str | Path,
    *,
    operation: str,
    requested_action: str,
    target_profile_id: str = "VOG-L29.C185",
    requested_by: str = "technician",
    authorization_reference_sha256: str = "a" * 64,
    recipe_hash: str | None = None,
    artifacts_ready: bool = True,
) -> DecisionReport:
    """Evaluate one historical replay with deterministic technician intent."""

    replay = load_replay(source)
    bundle = render_replay(replay)
    clock = replay["clock"]
    request = build_operation_request(
        physical_session_id=bundle.physical_session_id,
        operation=operation,
        requested_by=requested_by,
        authorization_reference_sha256=authorization_reference_sha256,
        target_profile_id=target_profile_id,
        created_at=clock["created_at"],
        expires_at=clock["fresh_until"],
        evidence_hashes=_bundle_evidence_hashes(bundle),
    )
    return evaluate_decision(
        operation_request=request,
        xray_bundle=bundle,
        requested_action=requested_action,
        validation_now=clock["validation_now"],
        expires_at=clock["fresh_until"],
        recipe_hash=recipe_hash,
        artifacts_ready=artifacts_ready,
    )


def evaluate_decision(
    *,
    operation_request: Mapping[str, Any],
    xray_bundle: ReplayBundle,
    requested_action: str,
    validation_now: str,
    expires_at: str,
    recipe_hash: str | None = None,
    artifacts_ready: bool = True,
) -> DecisionReport:
    """Run all eight officers and the veto-first Repair Governor."""

    if requested_action not in REQUESTED_ACTIONS:
        raise DecisionError("UNSUPPORTED_REQUESTED_ACTION", requested_action)
    _validate_operation_request(operation_request, xray_bundle.physical_session_id, validation_now)
    operation = str(operation_request["payload"]["operation"])
    if operation not in SUPPORTED_OPERATIONS:
        raise DecisionError("UNSUPPORTED_OPERATION", operation)

    snapshot = _decision_evidence(xray_bundle)
    decisions = (
        _identity_officer(operation, requested_action, snapshot, recipe_hash),
        _mode_officer(operation, requested_action, snapshot, recipe_hash),
        _firmware_officer(operation, requested_action, snapshot, recipe_hash),
        _artifact_officer(operation, requested_action, artifacts_ready, recipe_hash),
        _recovery_officer(requested_action, snapshot, recipe_hash),
        _route_planner(operation, requested_action, snapshot, recipe_hash),
        _safety_challenger(requested_action, snapshot, recipe_hash),
        _verification_judge(requested_action, snapshot, recipe_hash),
    )
    governor = govern_officer_decisions(decisions, recipe_hash=recipe_hash)

    evidence_hashes = _bundle_evidence_hashes(xray_bundle)
    namespace = uuid.uuid5(
        uuid.NAMESPACE_URL,
        (
            f"urn:thetechguy:decision:{xray_bundle.scenario_id}:"
            f"{xray_bundle.physical_session_id}:{operation}:{requested_action}:"
            f"{recipe_hash or 'none'}"
        ),
    )
    contracts = tuple(
        _decision_contract(
            namespace=namespace,
            role=decision.officer_id,
            decision=decision,
            physical_session_id=xray_bundle.physical_session_id,
            evidence_hashes=evidence_hashes,
            created_at=validation_now,
            expires_at=expires_at,
            validation_now=validation_now,
        )
        for decision in decisions
    )
    governor_contract = _decision_contract(
        namespace=namespace,
        role="repair.governor",
        decision=governor,
        physical_session_id=xray_bundle.physical_session_id,
        evidence_hashes=evidence_hashes,
        created_at=validation_now,
        expires_at=expires_at,
        validation_now=validation_now,
    )
    return DecisionReport(
        scenario_id=xray_bundle.scenario_id,
        physical_session_id=xray_bundle.physical_session_id,
        requested_action=requested_action,
        operation_request=dict(operation_request),
        officer_decisions=decisions,
        decision_contracts=contracts,
        governor_decision=governor,
        governor_contract=governor_contract,
    )


def govern_officer_decisions(
    decisions: Sequence[OfficerDecision], *, recipe_hash: str | None
) -> OfficerDecision:
    """Aggregate exactly eight valid officer verdicts; hard veto always wins."""

    if len(decisions) != len(OFFICER_ORDER):
        raise DecisionError("OFFICER_SET_INVALID", "all eight officers must report exactly once")
    actual_order = tuple(decision.officer_id for decision in decisions)
    if actual_order != OFFICER_ORDER:
        raise DecisionError("OFFICER_ORDER_INVALID", f"unexpected officer order {actual_order!r}")

    for decision in decisions:
        if decision.verdict not in ALLOWED_VERDICTS:
            raise DecisionError("UNKNOWN_VERDICT", decision.verdict)
        if decision.recipe_hash != recipe_hash:
            raise DecisionError("RECIPE_HASH_MISMATCH", decision.officer_id)
        if decision.veto and decision.officer_id not in VETO_OFFICERS:
            raise DecisionError("UNAUTHORIZED_VETO", decision.officer_id)
        if decision.veto and decision.verdict != "block":
            raise DecisionError("INVALID_VETO_VERDICT", decision.officer_id)

    for decision in decisions:
        if decision.veto:
            return OfficerDecision(
                officer_id="repair.governor",
                verdict="block",
                reason_code=decision.reason_code,
                veto=True,
                recipe_hash=recipe_hash,
            )

    for verdict in ("block", "need_artifact", "need_technician", "investigate"):
        for decision in decisions:
            if decision.verdict == verdict:
                return OfficerDecision(
                    officer_id="repair.governor",
                    verdict=verdict,
                    reason_code=decision.reason_code,
                    veto=False,
                    recipe_hash=recipe_hash,
                )

    return OfficerDecision(
        officer_id="repair.governor",
        verdict="allow_stage",
        reason_code="DECISION_CORPS_ALLOW_STAGE",
        veto=False,
        recipe_hash=recipe_hash,
    )


def _identity_officer(
    operation: str,
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if snapshot.twin.get("verification_status") == "unsafe":
        return _d("identity.officer", "block", "IDENTITY_SESSION_UNSAFE", True, recipe_hash)
    contradiction = any(
        verdict == "contradictory"
        for subject, verdict in snapshot.evidence.items()
        if "identity" in subject or "vendor-country" in subject or "branding" in subject
    )
    if contradiction and requested_action in RELEASE_ACTIONS:
        return _d(
            "identity.officer",
            "block",
            "IDENTITY_EVIDENCE_CONTRADICTORY",
            True,
            recipe_hash,
        )
    if contradiction:
        repair_context = operation in {
            "repair_main_version",
            "repair_oeminfo",
            "restore_branding",
        }
        return _d(
            "identity.officer",
            "allow_stage" if repair_context else "investigate",
            "IDENTITY_CONTRADICTION_REPAIR_CONTEXT"
            if repair_context
            else "IDENTITY_EVIDENCE_CONTRADICTORY",
            False,
            recipe_hash,
        )
    return _d("identity.officer", "allow_stage", "IDENTITY_EVIDENCE_COHERENT", False, recipe_hash)


def _mode_officer(
    operation: str,
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if snapshot.safety.get("release_blocked") is True and requested_action in RELEASE_ACTIONS:
        return _d(
            "mode.officer",
            "block",
            "DEC_REBOOT_105_REBOOT_BLOCKED_BY_ACTIVE_MODE_REQUIREMENT",
            False,
            recipe_hash,
        )
    if operation == "repair_main_version" and requested_action == "perform_operation":
        if snapshot.has_service_entry():
            return _d(
                "mode.officer",
                "allow_stage",
                "SERVICE_ENTRY_EVIDENCE_AVAILABLE",
                False,
                recipe_hash,
            )
        return _d(
            "mode.officer",
            "need_technician",
            "DEC_TESTPOINT_103_SERVICE_ENTRY_REQUIRED",
            False,
            recipe_hash,
        )
    return _d(
        "mode.officer",
        "allow_stage",
        "CURRENT_MODE_ACCEPTABLE_FOR_REQUEST",
        False,
        recipe_hash,
    )


def _firmware_officer(
    operation: str,
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    main_version = snapshot.evidence.get("vog-l29-main-version")
    oeminfo_version = snapshot.evidence.get("vog-l29-oeminfo-version-identity")
    if operation == "repair_main_version" and requested_action == "perform_operation":
        if main_version == "missing" and oeminfo_version == "missing":
            return _d(
                "firmware.officer",
                "allow_stage",
                "MAIN_VERSION_OEMINFO_REPAIR_REQUIRED",
                False,
                recipe_hash,
            )
    if requested_action == "finalize" and (main_version == "missing" or oeminfo_version == "missing"):
        return _d(
            "firmware.officer",
            "block",
            "MAIN_VERSION_NOT_VERIFIED",
            False,
            recipe_hash,
        )
    return _d(
        "firmware.officer",
        "allow_stage",
        "FIRMWARE_EVIDENCE_ACCEPTABLE_FOR_STAGE",
        False,
        recipe_hash,
    )


def _artifact_officer(
    operation: str,
    requested_action: str,
    artifacts_ready: bool,
    recipe_hash: str | None,
) -> OfficerDecision:
    artifact_operations = {
        "repair_main_version",
        "repair_oeminfo",
        "restore_branding",
        "restore",
        "flash_retail",
        "flash_board",
    }
    if requested_action == "perform_operation" and operation in artifact_operations and not artifacts_ready:
        return _d(
            "artifact.officer",
            "need_artifact",
            "DEC_ARTIFACT_104_COMPATIBLE_SERVICE_ARTIFACT_MISSING",
            False,
            recipe_hash,
        )
    return _d(
        "artifact.officer",
        "allow_stage",
        "ARTIFACT_REQUIREMENT_SATISFIED",
        False,
        recipe_hash,
    )


def _recovery_officer(
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if snapshot.safety.get("release_blocked") is True and requested_action in RELEASE_ACTIONS:
        return _d(
            "recovery.officer",
            "block",
            "SERVICE_ENVIRONMENT_RELEASE_NOT_PROVEN",
            True,
            recipe_hash,
        )
    return _d(
        "recovery.officer",
        "allow_stage",
        "RECOVERY_INVARIANTS_PRESERVED",
        False,
        recipe_hash,
    )


def _route_planner(
    operation: str,
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if requested_action == "inspect" or operation == "read_device":
        if snapshot.has_usable_endpoint():
            return _d(
                "route.planner",
                "allow_stage",
                "DIRECT_READ_ROUTE_AVAILABLE",
                False,
                recipe_hash,
            )
        return _d(
            "route.planner",
            "need_technician",
            "DEC_DIRECT_101_DIRECT_ROUTE_UNAVAILABLE",
            False,
            recipe_hash,
        )

    if operation == "repair_main_version" and requested_action == "perform_operation":
        # Xray is read-only, so its transport observation is never promoted into write authority.
        if snapshot.has_service_entry():
            return _d(
                "route.planner",
                "allow_stage",
                "SERVICE_ROUTE_SELECTED",
                False,
                recipe_hash,
            )
        return _d(
            "route.planner",
            "need_technician",
            "DEC_TESTPOINT_103_SERVICE_ENTRY_REQUIRED",
            False,
            recipe_hash,
        )

    if requested_action == "perform_operation":
        return _d(
            "route.planner",
            "investigate",
            "DEC_DIRECT_101_DIRECT_ROUTE_UNAVAILABLE",
            False,
            recipe_hash,
        )
    return _d(
        "route.planner",
        "allow_stage",
        "ROUTE_DEFERRED_TO_APPROVED_RECIPE",
        False,
        recipe_hash,
    )


def _safety_challenger(
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if requested_action in RELEASE_ACTIONS:
        reasons = set(snapshot.safety.get("reason_codes", ()))
        hazard = (
            snapshot.safety.get("release_blocked") is True
            or "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED" in reasons
            or snapshot.evidence.get("vog-l29-premature-stock-fastboot-hazard") == "observed"
        )
        if hazard:
            return _d(
                "safety.challenger",
                "block",
                "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED",
                True,
                recipe_hash,
            )
    return _d(
        "safety.challenger",
        "allow_stage",
        "NO_HARD_SAFETY_VETO_FOR_STAGE",
        False,
        recipe_hash,
    )


def _verification_judge(
    requested_action: str,
    snapshot: DecisionEvidence,
    recipe_hash: str | None,
) -> OfficerDecision:
    if requested_action in RELEASE_ACTIONS:
        if (
            snapshot.twin.get("verification_status") != "certified"
            or snapshot.safety.get("release_blocked") is True
        ):
            return _d(
                "verification.judge",
                "block",
                "VERIFY_REQUIRED_BEFORE_RELEASE",
                True,
                recipe_hash,
            )
    return _d(
        "verification.judge",
        "allow_stage",
        "VERIFICATION_GATE_SATISFIED_FOR_STAGE",
        False,
        recipe_hash,
    )


def _decision_contract(
    *,
    namespace: uuid.UUID,
    role: str,
    decision: OfficerDecision,
    physical_session_id: str,
    evidence_hashes: Sequence[str],
    created_at: str,
    expires_at: str,
    validation_now: str,
) -> dict[str, Any]:
    contract = {
        "schema_version": 1,
        "contract_type": "decision_verdict",
        "contract_id": str(uuid.uuid5(namespace, role)),
        "producer": PRODUCER_ID,
        "created_at": created_at,
        "physical_session_id": physical_session_id,
        "evidence_hashes": sorted(set(evidence_hashes)),
        "confidence_bps": 10000,
        "expires_at": expires_at,
        "authority": "governance",
        "single_use": False,
        "consumed_at": None,
        "payload": decision.payload(),
    }
    result = validate_contract(
        contract,
        context={
            "now": validation_now,
            "expected_contract_type": "decision_verdict",
            "expected_physical_session_id": physical_session_id,
            "expected_authority": "governance",
        },
    )
    if not result.ok:
        raise DecisionError("INVALID_DECISION_CONTRACT", json.dumps(result.as_dict(), sort_keys=True))
    return contract


def _validate_operation_request(
    contract: Mapping[str, Any], physical_session_id: str, validation_now: str
) -> None:
    result = validate_contract(
        contract,
        context={
            "now": validation_now,
            "expected_contract_type": "operation_request",
            "expected_physical_session_id": physical_session_id,
            "expected_authority": "planning",
        },
    )
    if not result.ok:
        raise DecisionError("INVALID_OPERATION_REQUEST", json.dumps(result.as_dict(), sort_keys=True))
    if contract.get("payload", {}).get("request_state") != "approved":
        raise DecisionError("OPERATION_NOT_APPROVED", "technician intent is not approved")


def _decision_evidence(bundle: ReplayBundle) -> DecisionEvidence:
    evidence: dict[str, str] = {}
    endpoints: list[EndpointEvidence] = []
    twins: list[dict[str, Any]] = []
    for contract in bundle.contracts:
        contract_type = contract.get("contract_type")
        payload = contract.get("payload", {})
        if contract_type == "device_evidence":
            subject = str(payload["subject_id"])
            if subject in evidence:
                raise DecisionError("DUPLICATE_EVIDENCE_SUBJECT", subject)
            evidence[subject] = str(payload["verdict"])
        elif contract_type == "endpoint_observation":
            endpoints.append(
                EndpointEvidence(
                    transport=str(payload["transport"]),
                    observed_state=str(payload["observed_state"]),
                    capability_ids=frozenset(str(value) for value in payload["capability_ids"]),
                )
            )
        elif contract_type == "device_twin":
            twins.append(dict(payload))
    if len(twins) != 1:
        raise DecisionError("DEVICE_TWIN_CARDINALITY_INVALID", f"expected one twin, found {len(twins)}")
    return DecisionEvidence(
        evidence=evidence,
        endpoints=tuple(endpoints),
        twin=twins[0],
        safety=dict(bundle.safety),
    )


def _bundle_evidence_hashes(bundle: ReplayBundle) -> list[str]:
    hashes: set[str] = {bundle.fixture_sha256, bundle.continuity_token_sha256}
    for contract in bundle.contracts:
        hashes.update(str(value) for value in contract.get("evidence_hashes", ()))
    return sorted(hashes)


def _d(
    officer_id: str,
    verdict: str,
    reason_code: str,
    veto: bool,
    recipe_hash: str | None,
) -> OfficerDecision:
    if officer_id not in OFFICER_ORDER:
        raise DecisionError("UNKNOWN_OFFICER", officer_id)
    if verdict not in ALLOWED_VERDICTS:
        raise DecisionError("UNKNOWN_VERDICT", verdict)
    if veto and officer_id not in VETO_OFFICERS:
        raise DecisionError("UNAUTHORIZED_VETO", officer_id)
    if veto and verdict != "block":
        raise DecisionError("INVALID_VETO_VERDICT", officer_id)
    return OfficerDecision(
        officer_id=officer_id,
        verdict=verdict,
        reason_code=reason_code,
        veto=veto,
        recipe_hash=recipe_hash,
    )

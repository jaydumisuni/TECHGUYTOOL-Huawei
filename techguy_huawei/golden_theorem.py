from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
THEOREM_PATH = ROOT / "manifests" / "huawei_revive_golden_theorem.json"


class TheoremError(ValueError):
    """Fail-closed golden-theorem validation error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class WorkflowStage:
    stage_id: str
    artifact_family: str | None = None
    artifact_region: str | None = None
    artifact_role: str | None = None
    metadata_only: bool = False
    treated_as_partition_authority: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowPlan:
    target_family: str
    target_region: str
    stages: tuple[WorkflowStage, ...]
    service_release_evidence: frozenset[str]


@dataclass(frozen=True, slots=True)
class TheoremVerdict:
    ok: bool
    reason_codes: tuple[str, ...]
    theorem_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "techguytool-huawei.golden-theorem-verdict.v1",
            "theorem_id": self.theorem_id,
            "ok": self.ok,
            "reason_codes": list(self.reason_codes),
            "authority": "governance_only",
            "execution_authority": "none",
            "device_authority": "none",
            "touches_device": False,
        }


def load_theorem(path: Path = THEOREM_PATH) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema",
        "theorem_id",
        "authority",
        "device_authority",
        "execution_authority",
        "donor",
        "invariants",
        "required_stage_order",
        "service_release_conditions",
        "donor_only_markers",
        "forbidden_inheritance",
        "truth_boundary",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise TheoremError("THEOREM_SCHEMA_INCOMPLETE", f"missing theorem fields: {missing}")
    if payload["authority"] != "governance_only":
        raise TheoremError("THEOREM_AUTHORITY_INVALID", "theorem authority must remain governance_only")
    if payload["device_authority"] != "none" or payload["execution_authority"] != "none":
        raise TheoremError("THEOREM_AUTHORITY_ESCALATION", "theorem cannot carry device or execution authority")
    return payload


def evaluate_workflow(plan: WorkflowPlan, theorem: Mapping[str, Any] | None = None) -> TheoremVerdict:
    theorem = theorem or load_theorem()
    reasons: list[str] = []
    stages = tuple(plan.stages)
    stage_ids = tuple(stage.stage_id for stage in stages)

    if len(stage_ids) != len(set(stage_ids)):
        reasons.append("GT_DUPLICATE_STAGE")

    required_order = tuple(str(value) for value in theorem["required_stage_order"])
    positions = {stage_id: index for index, stage_id in enumerate(stage_ids)}
    missing_required = [stage_id for stage_id in required_order if stage_id not in positions]
    if missing_required:
        reasons.append("GT_REQUIRED_STAGE_MISSING")
    else:
        ordered = [positions[stage_id] for stage_id in required_order]
        if ordered != sorted(ordered):
            reasons.append("GT_STAGE_ORDER_INVALID")

    donor = theorem["donor"]
    donor_family = str(donor["family"]).upper()
    donor_region = str(donor["regional_identity"]).upper()
    target_family = plan.target_family.upper()
    target_region = plan.target_region.upper()

    for stage in stages:
        artifact_family = (stage.artifact_family or "").upper()
        artifact_region = (stage.artifact_region or "").upper()
        artifact_role = stage.artifact_role or ""

        if stage.metadata_only and stage.treated_as_partition_authority:
            reasons.append("GT_METADATA_NOT_PARTITION_AUTHORITY")

        if target_family != donor_family and artifact_family == donor_family:
            reasons.append("GT_DONOR_FAMILY_ARTIFACT_FORBIDDEN")

        if target_region != donor_region and artifact_region == donor_region:
            reasons.append("GT_DONOR_REGION_IDENTITY_FORBIDDEN")

        if artifact_role in set(theorem["forbidden_inheritance"]):
            reasons.append("GT_DONOR_SPECIFIC_INHERITANCE_FORBIDDEN")

        if artifact_family and artifact_family != target_family:
            reasons.append("GT_TARGET_FAMILY_MISMATCH")

        if artifact_region and artifact_region != target_region:
            reasons.append("GT_TARGET_REGION_MISMATCH")

    release_conditions = frozenset(str(value) for value in theorem["service_release_conditions"])
    if "stock_environment_restored" in positions and not release_conditions.issubset(plan.service_release_evidence):
        reasons.append("GT_SERVICE_RELEASE_NOT_PROVEN")

    if "regional_firmware_continued" in positions and "target_identity_verified" in positions:
        if positions["regional_firmware_continued"] < positions["target_identity_verified"]:
            reasons.append("GT_IDENTITY_VERIFICATION_REQUIRED_BEFORE_FIRMWARE_CONTINUATION")

    if "stock_environment_restored" in positions:
        finalization_index = positions["stock_environment_restored"]
        protected = {
            "target_identity_restored",
            "target_identity_verified",
            "regional_firmware_continued",
        }
        if any(positions.get(stage_id, finalization_index + 1) > finalization_index for stage_id in protected):
            reasons.append("GT_STOCK_ENVIRONMENT_FINALIZATION_ONLY")

    unique_reasons = tuple(sorted(set(reasons)))
    return TheoremVerdict(
        ok=not unique_reasons,
        reason_codes=unique_reasons,
        theorem_id=str(theorem["theorem_id"]),
    )


def workflow_plan_from_mapping(source: Mapping[str, Any]) -> WorkflowPlan:
    stages_raw = source.get("stages")
    if not isinstance(stages_raw, Sequence) or isinstance(stages_raw, (str, bytes)):
        raise TheoremError("PLAN_STAGES_INVALID", "stages must be an ordered sequence")
    stages: list[WorkflowStage] = []
    for index, item in enumerate(stages_raw):
        if not isinstance(item, Mapping):
            raise TheoremError("PLAN_STAGE_INVALID", f"stage {index} must be an object")
        stage_id = item.get("stage_id")
        if not isinstance(stage_id, str) or not stage_id:
            raise TheoremError("PLAN_STAGE_ID_INVALID", f"stage {index} requires a non-empty stage_id")
        stages.append(
            WorkflowStage(
                stage_id=stage_id,
                artifact_family=_optional_text(item.get("artifact_family"), "artifact_family"),
                artifact_region=_optional_text(item.get("artifact_region"), "artifact_region"),
                artifact_role=_optional_text(item.get("artifact_role"), "artifact_role"),
                metadata_only=_strict_bool(item.get("metadata_only", False), "metadata_only"),
                treated_as_partition_authority=_strict_bool(
                    item.get("treated_as_partition_authority", False),
                    "treated_as_partition_authority",
                ),
            )
        )

    target_family = source.get("target_family")
    target_region = source.get("target_region")
    if not isinstance(target_family, str) or not target_family:
        raise TheoremError("PLAN_TARGET_FAMILY_INVALID", "target_family must be non-empty text")
    if not isinstance(target_region, str) or not target_region:
        raise TheoremError("PLAN_TARGET_REGION_INVALID", "target_region must be non-empty text")

    evidence = source.get("service_release_evidence", [])
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        raise TheoremError("PLAN_RELEASE_EVIDENCE_INVALID", "service_release_evidence must be a sequence")
    normalized_evidence: set[str] = set()
    for value in evidence:
        if not isinstance(value, str) or not value:
            raise TheoremError("PLAN_RELEASE_EVIDENCE_INVALID", "release evidence values must be non-empty text")
        normalized_evidence.add(value)

    return WorkflowPlan(
        target_family=target_family,
        target_region=target_region,
        stages=tuple(stages),
        service_release_evidence=frozenset(normalized_evidence),
    )


def _optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise TheoremError("PLAN_FIELD_INVALID", f"{name} must be non-empty text when present")
    return value


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise TheoremError("PLAN_FIELD_INVALID", f"{name} must be boolean")
    return value

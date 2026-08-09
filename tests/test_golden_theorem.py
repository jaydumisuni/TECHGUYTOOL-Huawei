from __future__ import annotations

import copy

import pytest

from techguy_huawei.golden_theorem import (
    TheoremError,
    evaluate_workflow,
    load_theorem,
    workflow_plan_from_mapping,
)


RELEASE = [
    "target_identity_verified",
    "remaining_firmware_completed",
    "target_boot_environment_ready",
]


def _vog_plan() -> dict:
    return {
        "target_family": "VOG",
        "target_region": "C185",
        "service_release_evidence": RELEASE,
        "stages": [
            {"stage_id": "service_environment_acquired"},
            {
                "stage_id": "target_identity_restored",
                "artifact_family": "VOG",
                "artifact_region": "C185",
            },
            {"stage_id": "target_identity_verified"},
            {
                "stage_id": "regional_firmware_continued",
                "artifact_family": "VOG",
                "artifact_region": "C185",
            },
            {"stage_id": "stock_environment_restored"},
        ],
    }


def test_vog_inherits_workflow_order_without_vtr_artifacts() -> None:
    verdict = evaluate_workflow(workflow_plan_from_mapping(_vog_plan()))
    assert verdict.ok is True
    assert verdict.reason_codes == ()
    assert verdict.to_dict()["device_authority"] == "none"
    assert verdict.to_dict()["execution_authority"] == "none"


def test_vtr_artifact_cannot_cross_into_vog_target() -> None:
    source = _vog_plan()
    source["stages"][1]["artifact_family"] = "VTR"
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_DONOR_FAMILY_ARTIFACT_FORBIDDEN" in verdict.reason_codes
    assert "GT_TARGET_FAMILY_MISMATCH" in verdict.reason_codes


def test_c432_identity_cannot_cross_into_c185_target() -> None:
    source = _vog_plan()
    source["stages"][1]["artifact_region"] = "C432"
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_DONOR_REGION_IDENTITY_FORBIDDEN" in verdict.reason_codes
    assert "GT_TARGET_REGION_MISMATCH" in verdict.reason_codes


def test_explicit_donor_binary_role_is_always_rejected() -> None:
    source = _vog_plan()
    source["stages"][1]["artifact_role"] = "donor_binary"
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_DONOR_SPECIFIC_INHERITANCE_FORBIDDEN" in verdict.reason_codes


def test_metadata_name_never_grants_partition_authority() -> None:
    source = _vog_plan()
    source["stages"].insert(
        3,
        {
            "stage_id": "package_metadata_observed",
            "metadata_only": True,
            "treated_as_partition_authority": True,
        },
    )
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_METADATA_NOT_PARTITION_AUTHORITY" in verdict.reason_codes


def test_identity_verification_must_precede_firmware_continuation() -> None:
    source = _vog_plan()
    source["stages"][2], source["stages"][3] = source["stages"][3], source["stages"][2]
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_STAGE_ORDER_INVALID" in verdict.reason_codes
    assert "GT_IDENTITY_VERIFICATION_REQUIRED_BEFORE_FIRMWARE_CONTINUATION" in verdict.reason_codes


def test_stock_environment_cannot_be_restored_without_release_evidence() -> None:
    source = _vog_plan()
    source["service_release_evidence"] = ["target_identity_verified"]
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_SERVICE_RELEASE_NOT_PROVEN" in verdict.reason_codes


def test_stock_environment_is_finalization_only() -> None:
    source = _vog_plan()
    source["stages"][1], source["stages"][4] = source["stages"][4], source["stages"][1]
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_STOCK_ENVIRONMENT_FINALIZATION_ONLY" in verdict.reason_codes


def test_missing_required_stage_fails_closed() -> None:
    source = _vog_plan()
    source["stages"] = [stage for stage in source["stages"] if stage["stage_id"] != "target_identity_verified"]
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_REQUIRED_STAGE_MISSING" in verdict.reason_codes


def test_duplicate_stage_fails_closed() -> None:
    source = _vog_plan()
    source["stages"].append(copy.deepcopy(source["stages"][-1]))
    verdict = evaluate_workflow(workflow_plan_from_mapping(source))
    assert verdict.ok is False
    assert "GT_DUPLICATE_STAGE" in verdict.reason_codes


def test_theorem_manifest_cannot_escalate_authority(tmp_path) -> None:
    source = dict(load_theorem())
    source["device_authority"] = "write"
    path = tmp_path / "theorem.json"
    import json

    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(TheoremError, match="THEOREM_AUTHORITY_ESCALATION"):
        load_theorem(path)


def test_plan_rejects_non_boolean_metadata_flag() -> None:
    source = _vog_plan()
    source["stages"][1]["metadata_only"] = 1
    with pytest.raises(TheoremError, match="PLAN_FIELD_INVALID"):
        workflow_plan_from_mapping(source)

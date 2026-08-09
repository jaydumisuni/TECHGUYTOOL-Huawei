from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from techguy_huawei.vog_recipe import (
    HARDWARE_PENDING,
    RELEASE_CONDITIONS,
    RecipeError,
    compile_recipe_plan,
    production_enabled,
    recipe_hash,
    service_release_allowed,
    validate_artifact_bindings,
    validate_preflight_evidence,
    validate_recipe,
)

ROOT = Path(__file__).resolve().parents[1]
RECIPE = json.loads((ROOT / "recipes" / "vog_l29_c185.json").read_text(encoding="utf-8"))


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def bindings():
    result = {}
    for i, requirement in enumerate(RECIPE["artifact_requirements"], 1):
        result[requirement["role"]] = {
            "sha256": h(f"artifact-{i}"),
            "size_bytes": 4096 + i,
            "target_profile_id": "VOG-L29.C185",
            "kind": requirement["kind"],
            "executable": requirement["executable"],
            "custody": "approved_workstation",
            "provenance_uri_sha256": h(f"provenance-{i}"),
        }
    return result


def ranges():
    return {
        stage["id"]: h(f"range-{stage['id']}")
        for stage in RECIPE["stages"]
        if stage.get("range_manifest_required") is True
    }


def preflight():
    return {
        "physical_session_id": "11111111-1111-4111-8111-111111111111",
        "device_continuity_certified": True,
        "xray_bundle_sha256": h("xray"),
        "storage_inventory_sha256": h("storage"),
        "board_identity_sha256": h("board"),
        "board_identity_verified": True,
        "mode_lease_id": "22222222-2222-4222-8222-222222222222",
        "mode": "board_service_fastboot",
        "mode_lease_reboot_allowed": False,
        "service_mode_certified": True,
        "target_profile_id": "VOG-L29.C185",
        "model": "VOG-L29",
        "soc": "Kirin980",
        "region": "C185",
        "vendor": "hw",
        "country": "meafnaf",
        "package_manifest_sha256": h("package"),
        "base_cust_preload_relationship": "verified",
        "anti_rollback_state": "compatible",
    }


def test_recipe_is_valid_and_hardware_pending():
    validate_recipe(RECIPE)
    assert RECIPE["production_enablement"] == HARDWARE_PENDING
    assert production_enabled(RECIPE) is False


def test_recipe_hash_is_deterministic():
    assert recipe_hash(RECIPE) == recipe_hash(copy.deepcopy(RECIPE))


def test_no_vtr_or_c432_donor_data_is_inherited():
    text = json.dumps(RECIPE, sort_keys=True)
    assert "VTR" not in text
    assert "C432" not in text


def test_oeminfo_layout_is_exactly_two_48_mib_copies():
    oem = RECIPE["oeminfo"]
    assert oem["total_size_bytes"] == 96 * 1024 * 1024
    assert oem["copy_count"] == 2
    assert oem["copy_size_bytes"] == 48 * 1024 * 1024
    assert oem["hardcoded_record_offsets_allowed"] is False


def test_stock_finalization_requires_all_release_conditions():
    for stage_id in ("restore_stock_recovery", "restore_stock_fastboot", "release_service_mode"):
        stage = next(stage for stage in RECIPE["stages"] if stage["id"] == stage_id)
        assert RELEASE_CONDITIONS.issubset(set(stage["requires"]))


def test_super_chunk_count_must_be_derived():
    stage = next(stage for stage in RECIPE["stages"] if stage["id"] == "derive_super_sparse_plan")
    assert stage["hardcoded_chunk_count_allowed"] is False


def test_branding_is_separate_after_boot_verification():
    ids = [stage["id"] for stage in RECIPE["stages"]]
    assert ids.index("verify_normal_boot") < ids.index("normalize_branding_if_required")
    branding = next(stage for stage in RECIPE["stages"] if stage["id"] == "normalize_branding_if_required")
    assert branding["scope"] == "reviewed_branding_fields_only"


def test_artifacts_require_exact_hashes_and_target():
    valid = validate_artifact_bindings(RECIPE, bindings())
    assert set(valid) == {item["role"] for item in RECIPE["artifact_requirements"]}


def test_missing_artifact_fails_closed():
    value = bindings()
    value.pop("target_cust")
    with pytest.raises(RecipeError, match="ARTIFACT_BINDING_MISSING"):
        validate_artifact_bindings(RECIPE, value)


def test_wrong_region_artifact_fails_closed():
    value = bindings()
    value["target_base"]["target_profile_id"] = "VOG-L29.C432"
    with pytest.raises(RecipeError, match="ARTIFACT_TARGET_MISMATCH"):
        validate_artifact_bindings(RECIPE, value)


def test_preflight_requires_certified_no_reboot_service_mode():
    value = preflight()
    value["mode_lease_reboot_allowed"] = True
    with pytest.raises(RecipeError, match="NO_REBOOT_LEASE_REQUIRED"):
        validate_preflight_evidence(RECIPE, value)


def test_preflight_rejects_unresolved_anti_rollback():
    value = preflight()
    value["anti_rollback_state"] = "unknown"
    with pytest.raises(RecipeError, match="ANTI_ROLLBACK_CONSTRAINT_UNRESOLVED"):
        validate_preflight_evidence(RECIPE, value)


def test_compile_requires_exact_service_mode():
    with pytest.raises(RecipeError, match="SERVICE_MODE_REQUIRED"):
        compile_recipe_plan(
            RECIPE,
            source_profile="VOG-AL00.board_service",
            current_mode="normal_fastboot",
            artifact_bindings=bindings(),
            range_manifests=ranges(),
            preflight_evidence=preflight(),
        )


def test_compile_produces_simulation_plan_not_production_authority():
    plan = compile_recipe_plan(
        RECIPE,
        source_profile="VOG-AL00.board_service",
        current_mode="board_service_fastboot",
        artifact_bindings=bindings(),
        range_manifests=ranges(),
        preflight_evidence=preflight(),
    )
    assert plan["simulation_status"] == "READY"
    assert plan["physical_certification"] == HARDWARE_PENDING
    assert plan["production_enabled"] is False
    assert plan["device_authority"] == "none"
    assert plan["recipe_hash"] == recipe_hash(RECIPE)
    assert all(
        stage["lease_required"]
        for stage in plan["stages"]
        if stage["kind"] in {"bounded_write", "conditional_bounded_write", "reboot"}
    )


def test_missing_range_authority_fails_closed():
    value = ranges()
    value.pop("restore_oeminfo_identity")
    with pytest.raises(RecipeError, match="RANGE_MANIFEST_MISSING"):
        compile_recipe_plan(
            RECIPE,
            source_profile="VOG-L29.board_service",
            current_mode="board_service_fastboot",
            artifact_bindings=bindings(),
            range_manifests=value,
            preflight_evidence=preflight(),
        )


def test_release_gate_is_exact():
    assert service_release_allowed(set(RELEASE_CONDITIONS))
    assert not service_release_allowed({"target_identity_verified", "remaining_firmware_completed"})


def test_recipe_rejects_donor_leakage():
    value = copy.deepcopy(RECIPE)
    value["truth_boundary"] += " C432"
    with pytest.raises(RecipeError, match="DONOR_DATA_LEAK"):
        validate_recipe(value)


def test_recipe_rejects_premature_fastboot_finalization():
    value = copy.deepcopy(RECIPE)
    stage = next(stage for stage in value["stages"] if stage["id"] == "restore_stock_fastboot")
    stage["requires"] = ["stock_recovery_restored"]
    with pytest.raises(RecipeError, match="PREMATURE_FINALIZATION_POSSIBLE"):
        validate_recipe(value)

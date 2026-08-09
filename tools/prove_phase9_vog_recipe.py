from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.vog_recipe import (  # noqa: E402
    HARDWARE_PENDING,
    RELEASE_CONDITIONS,
    compile_recipe_plan,
    load_recipe,
    recipe_hash,
    service_release_allowed,
)

REPLAY = ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json"


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def bindings(recipe: dict[str, object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for index, requirement in enumerate(recipe["artifact_requirements"], 1):  # type: ignore[index]
        role = requirement["role"]  # type: ignore[index]
        result[role] = {
            "sha256": h(f"phase9-simulation-artifact-{index}"),
            "size_bytes": 8192 + index,
            "target_profile_id": "VOG-L29.C185",
            "kind": requirement["kind"],  # type: ignore[index]
            "executable": requirement["executable"],  # type: ignore[index]
            "custody": "ephemeral_runtime",
            "provenance_uri_sha256": h(f"phase9-simulation-provenance-{index}"),
        }
    return result


def range_manifests(recipe: dict[str, object]) -> dict[str, str]:
    return {
        stage["id"]: h(f"phase9-range-{stage['id']}")
        for stage in recipe["stages"]  # type: ignore[index]
        if stage.get("range_manifest_required") is True
    }


def preflight() -> dict[str, object]:
    return {
        "physical_session_id": "11111111-1111-4111-8111-111111111111",
        "device_continuity_certified": True,
        "xray_bundle_sha256": h("phase9-xray"),
        "storage_inventory_sha256": h("phase9-storage"),
        "board_identity_sha256": h("phase9-board"),
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
        "package_manifest_sha256": h("phase9-package"),
        "base_cust_preload_relationship": "verified",
        "anti_rollback_state": "compatible",
    }


def main() -> int:
    recipe = load_recipe()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    expected_sources = set(recipe["provenance"]["replay_source_hashes"])
    actual_sources = {source["sha256"] for source in replay["sources"]}
    if expected_sources != actual_sources:
        raise SystemExit("Phase 9 replay provenance does not match frozen P30 evidence")
    if replay["twin"]["identity_material"]["device_model"] != "VOG-L29":
        raise SystemExit("P30 replay no longer identifies VOG-L29")
    if replay["twin"]["storage_material"]["main_version_state_location"] != "oeminfo":
        raise SystemExit("P30 replay no longer supports OEMINFO main-version state")
    if replay["safety"]["release_blocked"] is not True:
        raise SystemExit("P30 replay no longer records the premature-release hazard")

    plan = compile_recipe_plan(
        recipe,
        source_profile="VOG-AL00.board_service",
        current_mode="board_service_fastboot",
        artifact_bindings=bindings(recipe),
        range_manifests=range_manifests(recipe),
        preflight_evidence=preflight(),
    )
    if plan["recipe_hash"] != recipe_hash(recipe):
        raise SystemExit("compiled recipe hash mismatch")
    if plan["physical_certification"] != HARDWARE_PENDING or plan["production_enabled"] is not False:
        raise SystemExit("software proof must not certify physical VOG production")
    if not service_release_allowed(set(RELEASE_CONDITIONS)):
        raise SystemExit("exact release-condition set should satisfy the release theorem")
    if service_release_allowed({"target_identity_verified", "remaining_firmware_completed"}):
        raise SystemExit("release gate accepted incomplete evidence")

    stage_ids = [stage["stage_id"] for stage in plan["stages"]]
    if stage_ids.index("verify_oeminfo_readback") >= stage_ids.index("continue_base_cust_preload"):
        raise SystemExit("firmware continuation precedes target identity verification")
    if stage_ids.index("verify_target_boot_environment") >= stage_ids.index("restore_stock_fastboot"):
        raise SystemExit("stock Fastboot can be restored before target boot readiness")
    if stage_ids.index("verify_normal_boot") >= stage_ids.index("normalize_branding_if_required"):
        raise SystemExit("branding normalization is not separated from core recovery")

    result = {
        "schema": "techguytool-huawei.phase9-proof.v1",
        "status": "PASS",
        "recipe_hash": recipe_hash(recipe),
        "simulation": "PASS",
        "historical_replay": "PASS",
        "artifact_binding": "HASH_BOUND",
        "range_authority": "HASH_BOUND",
        "service_release": "FAIL_CLOSED",
        "hardware_certification": HARDWARE_PENDING,
        "production_enabled": False,
        "device_authority": "none",
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

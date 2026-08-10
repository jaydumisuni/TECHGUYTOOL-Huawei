from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "manifests" / "phase15_windows_release_policy.json"
MATRIX_PATH = ROOT / "manifests" / "phase15_physical_proof_matrix.json"
BUILD_SCRIPT = ROOT / "build_windows.ps1"
DEPLOY_SPEC = ROOT / "pysidedeploy.spec"
POLICY_SCHEMA = "techguytool-huawei.phase15-windows-release-policy.v1"
MATRIX_SCHEMA = "techguytool-huawei.phase15-physical-proof-matrix.v1"

REQUIRED_MATRIX_IDS = frozenset(
    {
        "vog_kirin980_full_recovery_branding",
        "historical_p10_vtr_regression",
        "mtp_direct_route",
        "authorized_adb_direct_route",
        "normal_fastboot_direct_route",
        "recovery_detection",
        "upgrade_mode_detection_recipe_eligibility",
        "kirin_testpoint_usb_com_1_0",
        "loader_factory_board_service_fastboot",
        "active_mode_lease_blocks_reboot",
        "wrong_loader_rejection",
        "wrong_firmware_region_rejection",
        "multiple_device_rejection",
        "interrupted_oeminfo_recovery",
        "interrupted_super_recovery",
        "stock_finalization_after_release_conditions",
        "ui_restart_recovery",
        "gateway_restart_recovery",
        "qualcomm_9008_read_only",
        "mediatek_brom_preloader_read_only",
        "clean_windows_driver_install",
    }
)
ALLOWED_NONPHYSICAL_STATUS = frozenset(
    {
        "HARDWARE_PENDING",
        "REPLAY_PROVEN_PHYSICAL_PENDING",
        "SOFTWARE_PROVEN_PHYSICAL_PENDING",
        "WINDOWS_CI_PENDING_PHYSICAL_DRIVER_PROOF",
    }
)


class WindowsReleaseError(ValueError):
    pass


def load_release_policy() -> dict[str, Any]:
    payload = _load_json(POLICY_PATH)
    validate_release_policy(payload)
    return payload


def load_physical_matrix() -> dict[str, Any]:
    payload = _load_json(MATRIX_PATH)
    validate_physical_matrix(payload)
    return payload


def validate_release_policy(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != POLICY_SCHEMA:
        raise WindowsReleaseError("Windows release policy schema mismatch")
    if payload.get("release_filename") != "TECHGUYTOOL_Huawei.exe":
        raise WindowsReleaseError("Windows release filename mismatch")
    if payload.get("platform") != "windows":
        raise WindowsReleaseError("Windows release platform mismatch")
    packaging = _mapping(payload.get("packaging"), "packaging")
    expected_packaging = {
        "mode": "onefile",
        "builder": "pyside6-deploy",
        "engine": "nuitka",
        "runtime_extraction_required": True,
        "restart_after_forced_close_required": True,
        "sha256_required": True,
    }
    for key, expected in expected_packaging.items():
        if packaging.get(key) != expected:
            raise WindowsReleaseError(f"Windows packaging policy {key} mismatch")

    signing = _mapping(payload.get("signing"), "signing")
    if signing.get("authenticode_required_for_production") is not True:
        raise WindowsReleaseError("Production Authenticode requirement removed")
    if signing.get("ci_test_signing_allowed") is not True:
        raise WindowsReleaseError("CI signing-path proof must remain explicit")
    if signing.get("production_certificate_may_not_be_committed") is not True:
        raise WindowsReleaseError("Production certificate storage boundary weakened")
    if signing.get("production_signing_status") != "EXTERNAL_CERTIFICATE_REQUIRED":
        raise WindowsReleaseError("Production signing status overstated")

    clean = _mapping(payload.get("clean_windows"), "clean_windows")
    for field in ("github_windows_runner_required", "pnputil_presence_required", "pnp_inventory_presence_required"):
        if clean.get(field) is not True:
            raise WindowsReleaseError(f"Clean Windows requirement {field} removed")
    if clean.get("physical_driver_install_status") != "HARDWARE_PENDING":
        raise WindowsReleaseError("Physical driver proof overstated")

    external = payload.get("external_data")
    required_external = {
        "firmware",
        "SUPER images",
        "customer backups",
        "testpoint catalogue images",
        "operation journals",
        "registration/license data",
        "downloaded artifacts",
    }
    if not isinstance(external, list) or set(external) != required_external:
        raise WindowsReleaseError("External-data release boundary mismatch")
    if payload.get("production_enabled") is not False:
        raise WindowsReleaseError("Production enablement forbidden before external certification")
    if payload.get("production_release_status") != "EXTERNAL_CERTIFICATION_PENDING":
        raise WindowsReleaseError("Production release status overstated")


def validate_physical_matrix(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != MATRIX_SCHEMA:
        raise WindowsReleaseError("Physical matrix schema mismatch")
    if payload.get("overall_status") != "INCOMPLETE":
        raise WindowsReleaseError("Physical matrix may not be marked complete without physical evidence")
    if payload.get("production_enabled") is not False:
        raise WindowsReleaseError("Physical matrix cannot enable production")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise WindowsReleaseError("Physical matrix entries missing")
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WindowsReleaseError("Physical matrix entry must be an object")
        entry_id = entry.get("id")
        status = entry.get("status")
        if not isinstance(entry_id, str) or not entry_id:
            raise WindowsReleaseError("Physical matrix id invalid")
        if status not in ALLOWED_NONPHYSICAL_STATUS:
            raise WindowsReleaseError(f"Physical matrix status is unsupported or overstated: {entry_id}={status}")
        ids.append(entry_id)
    if len(ids) != len(set(ids)):
        raise WindowsReleaseError("Physical matrix ids must be unique")
    if set(ids) != REQUIRED_MATRIX_IDS:
        raise WindowsReleaseError("Physical matrix does not match the frozen plan")
    rule = payload.get("rule")
    if not isinstance(rule, str) or "Only PHYSICAL_PASS" not in rule:
        raise WindowsReleaseError("Physical matrix proof rule missing")


def validate_windows_release_sources() -> dict[str, Any]:
    policy = load_release_policy()
    matrix = load_physical_matrix()
    build = BUILD_SCRIPT.read_text(encoding="utf-8")
    spec = DEPLOY_SPEC.read_text(encoding="utf-8")

    build_requirements = {
        "one-file deploy": "pyside6-deploy -c pysidedeploy.spec -f",
        "PySide title intermediate": 'Filter "TECHGUY TOOL Huawei.exe"',
        "fallback main executable": 'Filter "main.exe"',
        "target directory precreated": "New-Item -ItemType Directory -Force $TargetDirectory",
        "exact executable": '"TECHGUYTOOL_Huawei.exe"',
        "deterministic rename": "Move-Item",
        "tests": "python -m pytest",
        "independent review": "review_20_for_2.py --strict",
        "rust health core": 'rust\\health_core\\Cargo.toml',
        "signature tool": "signtool.exe",
        "sha256": "Get-FileHash -Algorithm SHA256",
        "checksum output": '"SHA256SUMS.txt"',
    }
    missing_build = [name for name, token in build_requirements.items() if token not in build]
    if missing_build:
        raise WindowsReleaseError(f"Windows build script missing requirements: {missing_build}")

    spec_requirements = {
        "onefile": "mode = onefile",
        "application title": "title = TECHGUY TOOL Huawei",
        "msvc": "--msvc=latest",
        "noninteractive helper downloads": "--assume-yes-for-downloads",
        "runtime data": "--include-data-dir=runtime=runtime",
        "application data": "--include-data-dir=data=data",
        "brand assets": "--include-data-dir=assets=assets",
        "console disabled": "--windows-console-mode=disable",
    }
    missing_spec = [name for name, token in spec_requirements.items() if token not in spec]
    if missing_spec:
        raise WindowsReleaseError(f"PySide deploy spec missing requirements: {missing_spec}")
    if "--output-filename=" in spec:
        raise WindowsReleaseError("PySide deploy spec may not override the wrapper-owned final executable name")

    lower_spec = spec.lower()
    forbidden_bundles = ("firmware=firmware", "super=super", "backups=", "testpoints=")
    present_forbidden = [item for item in forbidden_bundles if item in lower_spec]
    if present_forbidden:
        raise WindowsReleaseError(f"External-data boundary violated by deploy spec: {present_forbidden}")

    return {
        "schema": "techguytool-huawei.phase15-software-release-readiness.v1",
        "status": "PASS",
        "release_filename": policy["release_filename"],
        "packaging": "ONEFILE_READY",
        "signing_path": "AUTHENTICODE_REQUIRED_CI_TESTABLE",
        "checksums": "SHA256_REQUIRED",
        "clean_windows_ci": "REQUIRED",
        "physical_matrix": matrix["overall_status"],
        "production_release_status": policy["production_release_status"],
        "production_enabled": False,
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WindowsReleaseError(str(exc)) from exc
    if not isinstance(payload, dict):
        raise WindowsReleaseError(f"JSON root must be object: {path}")
    return payload


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WindowsReleaseError(f"Windows release {name} must be an object")
    return value

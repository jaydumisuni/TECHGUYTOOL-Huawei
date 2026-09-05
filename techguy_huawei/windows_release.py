from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "manifests" / "phase15_windows_release_policy.json"
MATRIX_PATH = ROOT / "manifests" / "phase15_physical_proof_matrix.json"
RECEIPT_PATH = ROOT / "manifests" / "phase15_windows_release.receipt.json"
SOURCE_INVENTORY_PATH = ROOT / "manifests" / "source_inventory.json"
BUILD_SCRIPT = ROOT / "build_windows.ps1"
DEPLOY_SPEC = ROOT / "pysidedeploy.spec"
POLICY_SCHEMA = "techguytool-huawei.phase15-windows-release-policy.v1"
MATRIX_SCHEMA = "techguytool-huawei.phase15-physical-proof-matrix.v1"
RECEIPT_SCHEMA = "techguytool-huawei.phase15-receipt.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
INCLUDE_DATA_RE = re.compile(r"--include-data-dir=(?:\"([^\"]+)\"|'([^']+)'|([^\s]+))", re.IGNORECASE)
PHYSICAL_EVIDENCE_FIELDS = frozenset(
    {
        "evidence_id",
        "evidence_sha256",
        "evidence_refs",
        "subject_identity_hash",
        "verified_at",
        "verifier",
    }
)

REQUIRED_MATRIX_IDS = frozenset(
    {
        "vog_kirin980_full_recovery_branding",
        "historical_p10_vtr_regression",
        "mtp_direct_route",
        "dead_screen_pre_service_usb_discovery",
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


def load_release_receipt() -> dict[str, Any]:
    payload = _load_json(RECEIPT_PATH)
    validate_release_receipt(payload)
    return payload


def source_inventory_sha256() -> str:
    try:
        return hashlib.sha256(SOURCE_INVENTORY_PATH.read_bytes()).hexdigest()
    except OSError as exc:
        raise WindowsReleaseError(str(exc)) from exc


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


def validate_release_receipt(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != RECEIPT_SCHEMA or payload.get("phase") != 15:
        raise WindowsReleaseError("Phase 15 receipt schema mismatch")
    if payload.get("release_filename") != "TECHGUYTOOL_Huawei.exe":
        raise WindowsReleaseError("Phase 15 receipt filename mismatch")
    if payload.get("production_signing") != "EXTERNAL_CERTIFICATE_REQUIRED":
        raise WindowsReleaseError("Phase 15 receipt production signing boundary mismatch")
    if payload.get("production_release_status") != "EXTERNAL_CERTIFICATION_PENDING":
        raise WindowsReleaseError("Phase 15 receipt production status overstated")
    if payload.get("production_enabled") is not False:
        raise WindowsReleaseError("Phase 15 receipt may not enable production")
    if payload.get("physical_proof_matrix") not in {"INCOMPLETE", "COMPLETE"}:
        raise WindowsReleaseError("Phase 15 receipt physical matrix status invalid")

    status = payload.get("status")
    if status == "UNFROZEN":
        if payload.get("windows_ci") != "PENDING" or payload.get("ci_test_signing") != "PENDING":
            raise WindowsReleaseError("Unfrozen Phase 15 receipt must keep CI evidence pending")
        return
    if status != "FROZEN":
        raise WindowsReleaseError("Phase 15 receipt status invalid")
    if payload.get("windows_ci") != "PASS" or payload.get("ci_test_signing") != "PASS":
        raise WindowsReleaseError("Frozen Phase 15 receipt requires passing Windows CI and test signing")
    required = {
        "tested_revision": REVISION_RE,
        "source_inventory_sha256": SHA256_RE,
        "executable_sha256": SHA256_RE,
    }
    for field, pattern in required.items():
        value = payload.get(field)
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise WindowsReleaseError(f"Frozen Phase 15 receipt {field} invalid")
    for field in ("windows_run_id", "software_proof_run_id", "artifact_id"):
        value = payload.get(field)
        if not isinstance(value, int) or value <= 0:
            raise WindowsReleaseError(f"Frozen Phase 15 receipt {field} invalid")
    artifact_name = payload.get("artifact_name")
    if not isinstance(artifact_name, str) or not artifact_name.strip():
        raise WindowsReleaseError("Frozen Phase 15 receipt artifact_name invalid")


def validate_receipt_matrix_alignment(receipt: Mapping[str, Any], matrix: Mapping[str, Any]) -> None:
    if receipt.get("physical_proof_matrix") != matrix.get("overall_status"):
        raise WindowsReleaseError("Phase 15 receipt physical matrix status does not match the physical proof matrix")


def validate_physical_matrix(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != MATRIX_SCHEMA:
        raise WindowsReleaseError("Physical matrix schema mismatch")
    if payload.get("production_enabled") is not False:
        raise WindowsReleaseError("Physical matrix cannot enable production")
    requirements = _mapping(payload.get("physical_pass_evidence_requirements"), "physical pass evidence requirements")
    fields = requirements.get("required_fields")
    if not isinstance(fields, list) or set(fields) != PHYSICAL_EVIDENCE_FIELDS:
        raise WindowsReleaseError("Physical-pass evidence requirements mismatch")
    if requirements.get("hash_algorithm") != "sha256" or requirements.get("timestamp_format") != "RFC3339_UTC":
        raise WindowsReleaseError("Physical-pass evidence encoding requirements mismatch")

    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise WindowsReleaseError("Physical matrix entries missing")
    ids: list[str] = []
    pass_count = 0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WindowsReleaseError("Physical matrix entry must be an object")
        entry_id = entry.get("id")
        status = entry.get("status")
        if not isinstance(entry_id, str) or not entry_id:
            raise WindowsReleaseError("Physical matrix id invalid")
        if status == "PHYSICAL_PASS":
            _validate_physical_evidence(entry_id, entry.get("evidence"))
            pass_count += 1
        elif status in ALLOWED_NONPHYSICAL_STATUS:
            if "evidence" in entry:
                raise WindowsReleaseError(f"Pending physical matrix entry may not carry pass evidence: {entry_id}")
        else:
            raise WindowsReleaseError(f"Physical matrix status is unsupported or overstated: {entry_id}={status}")
        ids.append(entry_id)
    if len(ids) != len(set(ids)):
        raise WindowsReleaseError("Physical matrix ids must be unique")
    if set(ids) != REQUIRED_MATRIX_IDS:
        raise WindowsReleaseError("Physical matrix does not match the frozen plan")
    expected_status = "COMPLETE" if pass_count == len(entries) else "INCOMPLETE"
    if payload.get("overall_status") != expected_status:
        raise WindowsReleaseError("Physical matrix overall status does not match validated evidence")
    rule = payload.get("rule")
    if not isinstance(rule, str) or "Only PHYSICAL_PASS" not in rule:
        raise WindowsReleaseError("Physical matrix proof rule missing")


def find_prohibited_external_data_sources(spec: str) -> list[str]:
    prohibited_tokens = ("firmware", "super", "backup", "testpoint", "journal", "registration", "license", "download")
    hits: list[str] = []
    for match in INCLUDE_DATA_RE.finditer(spec):
        mapping = next((group for group in match.groups() if group is not None), "")
        source = mapping.rsplit("=", 1)[0].replace("\\", "/").strip('"\'')
        normalized_parts = [re.sub(r"[^a-z0-9]", "", part.lower()) for part in source.split("/") if part]
        if any(any(token in part for token in prohibited_tokens) for part in normalized_parts):
            hits.append(source)
    return sorted(set(hits))


def receipt_matches_active_source(receipt: Mapping[str, Any]) -> bool:
    if receipt.get("status") != "FROZEN":
        return False
    if receipt.get("source_inventory_sha256") != source_inventory_sha256():
        return False
    tested_revision = receipt.get("tested_revision")
    if not isinstance(tested_revision, str) or not REVISION_RE.fullmatch(tested_revision):
        return False

    inventory = _load_json(SOURCE_INVENTORY_PATH)
    excluded = inventory.get("excluded_from_recursive_hashing")
    if not isinstance(excluded, list) or any(not isinstance(path, str) for path in excluded):
        return False
    allowed_authority_paths = {path.replace("\\", "/") for path in excluded}

    git_executable = shutil.which("git")
    if not git_executable:
        return False
    try:
        ancestry = subprocess.run(
            [git_executable, "merge-base", "--is-ancestor", tested_revision, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if ancestry.returncode != 0:
            return False
        tracked_clean = subprocess.run(
            [git_executable, "diff", "--quiet", "HEAD", "--"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if tracked_clean.returncode != 0:
            return False
        completed = subprocess.run(
            [git_executable, "diff", "--name-only", f"{tested_revision}..HEAD"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if completed.returncode != 0:
        return False
    changed_paths = {line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()}
    return changed_paths <= allowed_authority_paths


def validate_windows_release_sources() -> dict[str, Any]:
    policy = load_release_policy()
    matrix = load_physical_matrix()
    receipt = load_release_receipt()
    validate_receipt_matrix_alignment(receipt, matrix)
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

    present_forbidden = find_prohibited_external_data_sources(spec)
    if present_forbidden:
        raise WindowsReleaseError(f"External-data boundary violated by deploy spec: {present_forbidden}")

    ci_proven = receipt_matches_active_source(receipt)
    status = "CI_PROVEN" if ci_proven else "SOURCES_ONLY_PENDING_CI"
    return {
        "schema": "techguytool-huawei.phase15-software-release-readiness.v1",
        "status": status,
        "release_filename": policy["release_filename"],
        "packaging": "ONEFILE_READY",
        "signing_path": "CI_AUTHENTICODE_PROVEN" if ci_proven else "AUTHENTICODE_REQUIRED_CI_TESTABLE",
        "checksums": "SHA256_PROVEN" if ci_proven else "SHA256_REQUIRED",
        "clean_windows_ci": "PASS" if ci_proven else "PENDING",
        "physical_matrix": matrix["overall_status"],
        "production_release_status": policy["production_release_status"],
        "production_enabled": False,
    }


def _validate_physical_evidence(entry_id: str, value: Any) -> None:
    evidence = _mapping(value, f"physical evidence for {entry_id}")
    if set(evidence) != PHYSICAL_EVIDENCE_FIELDS:
        raise WindowsReleaseError(f"Physical evidence fields invalid: {entry_id}")
    for field in ("evidence_id", "verifier"):
        item = evidence.get(field)
        if not isinstance(item, str) or not item.strip():
            raise WindowsReleaseError(f"Physical evidence {field} invalid: {entry_id}")
    for field in ("evidence_sha256", "subject_identity_hash"):
        item = evidence.get(field)
        if not isinstance(item, str) or not SHA256_RE.fullmatch(item):
            raise WindowsReleaseError(f"Physical evidence {field} invalid: {entry_id}")
    refs = evidence.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise WindowsReleaseError(f"Physical evidence references invalid: {entry_id}")
    timestamp = evidence.get("verified_at")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise WindowsReleaseError(f"Physical evidence verified_at invalid: {entry_id}")
    try:
        parsed = datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError as exc:
        raise WindowsReleaseError(f"Physical evidence verified_at invalid: {entry_id}") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise WindowsReleaseError(f"Physical evidence verified_at must be UTC: {entry_id}")


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

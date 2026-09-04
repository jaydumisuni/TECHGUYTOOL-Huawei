from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifests" / "source_inventory.json"
SOFTWARE_PHASE_SOURCES = ROOT / "manifests" / "software_phase_sources.json"
EXCLUDED = {
    "manifests/phase3_gateway.receipt.json",
    "manifests/phase4_kirin_xray.receipt.json",
    "manifests/phase5_decision_corps.receipt.json",
    "manifests/phase6_leases.receipt.json",
    "manifests/phase7_executor.receipt.json",
    "manifests/phase8_golden_theorem.receipt.json",
    "manifests/phase9_vog_recipe.receipt.json",
    "manifests/phase10_inquiry_governor.receipt.json",
    "manifests/phase11_knowledge_workshop.receipt.json",
    "manifests/phase12_kirin_packs.receipt.json",
    "manifests/phase13_ttg_xray_promotion.receipt.json",
    "manifests/phase14_qcom_mtk.receipt.json",
    "manifests/phase15_windows_release.receipt.json",
    "manifests/source_inventory.json",
    "manifests/source_inventory.receipt.json",
}
IGNORED_ROOTS = {"build", "dist", "proof", "wheelhouse"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "venv", "target"}
IGNORED_EXACT = {"techguy_huawei/resources_rc.py"}
PHASE1_PREFIXES = ("manifests/",)
PHASE1_PATHS = {
    ".github/workflows/proof.yml",
    "FULL_PLAN.md",
    "docs/LEGACY_AUTHORITY_REVIEW.md",
    "docs/PHASE_1_SOURCE_FREEZE.md",
    "tests/test_source_freeze.py",
}
PHASE2_PREFIXES = ("contracts/", "rust/contracts_core/")
PHASE2_PATHS = {
    ".github/workflows/phase2-contracts.yml",
    ".gitignore",
    "docs/PHASE_2_SHARED_CONTRACTS.md",
    "techguy_huawei/contract_fields.py",
    "techguy_huawei/contract_models.py",
    "techguy_huawei/contract_support.py",
    "techguy_huawei/contract_validation.py",
    "techguy_huawei/contracts.py",
    "tests/test_shared_contracts.py",
    "tools/prove_context_equivalence.py",
    "tools/prove_contract_equivalence.py",
}
PHASE3_PREFIXES = ("rust/device_gateway/",)
PHASE3_PATHS = {
    ".github/workflows/phase3-gateway.yml",
    "README.md",
    "docs/PHASE_3_DEVICE_GATEWAY.md",
    "techguy_huawei/gateway_client.py",
    "tests/test_gateway_client.py",
    "tools/build_phase2_receipt.py",
    "tools/build_phase3_receipt.py",
    "tools/prove_gateway_reconnect.py",
    "tools/verify_source_freeze.py",
}
PHASE4_PREFIXES = ("replay/kirin/",)
PHASE4_PATHS = {
    ".github/workflows/phase4-authority.yml",
    ".github/workflows/phase4-kirin-xray.yml",
    "docs/PHASE_4_KIRIN_XRAY.md",
    "manifests/kirin_xray_sources.json",
    "techguy_huawei/kirin_xray.py",
    "techguy_huawei/kirin_xray_authority.py",
    "tests/test_kirin_xray.py",
    "tests/test_kirin_xray_authority.py",
    "tools/build_phase4_receipt.py",
    "tools/prove_kirin_xray_replay.py",
}
PHASE5_PATHS = {
    ".github/workflows/phase5-authority.yml",
    ".github/workflows/phase5-decision-corps.yml",
    "docs/PHASE_5_REPAIR_DECISION_CORPS.md",
    "techguy_huawei/decision_corps.py",
    "tests/test_decision_corps.py",
    "tools/build_phase5_receipt.py",
    "tools/prove_decision_corps.py",
}
PHASE6_PATHS = {
    ".github/workflows/phase6-authority.yml",
    ".github/workflows/phase6-leases.yml",
    "docs/PHASE_6_MODE_EXECUTION_LEASES.md",
    "rust/device_gateway/src/lease.rs",
    "rust/device_gateway/src/lib.rs",
    "rust/device_gateway/tests/leases.rs",
    "tools/build_phase6_receipt.py",
    "tools/prove_phase6_leases.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_phase_receipt(rel: str) -> bool:
    return rel.startswith("manifests/phase") and rel.endswith(".receipt.json")


def is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = path.relative_to(ROOT).parts
    return (
        rel.startswith(".git/")
        or rel in EXCLUDED
        or is_phase_receipt(rel)
        or rel in IGNORED_EXACT
        or bool(parts and parts[0] in IGNORED_ROOTS)
        or any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in parts)
    )


GENERATED_SOURCE_PATHS = {
    "rust/device_gateway/Cargo.lock",
}


def source_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("git ls-files failed while building source inventory")

    files: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8")
        if path.is_file() and not is_ignored(path):
            files.append(path)
    for rel in GENERATED_SOURCE_PATHS:
        path = ROOT / rel
        if path.is_file() and not is_ignored(path) and path not in files:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def software_origin_map() -> dict[str, str]:
    if not SOFTWARE_PHASE_SOURCES.is_file():
        return {}
    payload = json.loads(SOFTWARE_PHASE_SOURCES.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("software phase source map must be an object")
    result: dict[str, str] = {}
    for origin, paths in payload.items():
        if not isinstance(origin, str) or not isinstance(paths, list):
            raise SystemExit("software phase source map is malformed")
        for rel in paths:
            if not isinstance(rel, str):
                raise SystemExit("software phase source path must be a string")
            if rel in result and result[rel] != origin:
                raise SystemExit(f"source path belongs to multiple software phases: {rel}")
            result[rel] = origin
    return result


def origin_for(rel: str, software_origins: dict[str, str]) -> str:
    if rel in software_origins:
        return software_origins[rel]
    if rel in PHASE6_PATHS:
        return "phase6_mode_execution_leases"
    if rel in PHASE5_PATHS:
        return "phase5_repair_decision_corps"
    if rel in PHASE4_PATHS or rel.startswith(PHASE4_PREFIXES):
        return "phase4_kirin_xray"
    if rel in PHASE3_PATHS or rel.startswith(PHASE3_PREFIXES):
        return "phase3_device_gateway"
    if rel in PHASE2_PATHS or rel.startswith(PHASE2_PREFIXES):
        return "phase2_shared_contracts"
    if rel in PHASE1_PATHS or rel.startswith(PHASE1_PREFIXES):
        return "phase1_recovery_and_freeze"
    return "github_actions:huawei-source-workspace:8833608382"


def build() -> dict[str, object]:
    software_origins = software_origin_map()
    records = []
    for path in source_files():
        rel = path.relative_to(ROOT).as_posix()
        records.append(
            {
                "origin": origin_for(rel, software_origins),
                "path": rel,
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        "base_provenance": {
            "artifact_id": 8833608382,
            "artifact_name": "huawei-source-workspace",
            "artifact_sha256": "dbbb3b430f3ea595f4c4f01bc18670770059deec2c2700809085333fa6d645bc",
            "github_actions_run_id": 30748347340,
            "source_branch": "build/huawei-ui-v0.1",
        },
        "excluded_from_recursive_hashing": sorted(EXCLUDED),
        "file_count": len(records),
        "files": records,
        "inventory_definition_date": "2026-08-09",
        "private_recovery_authority": {
            "archive_sha256": "d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4",
            "copied_into_public_source": False,
            "drive_file_id": "1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs",
        },
        "schema": "techguytool-huawei.source-inventory.v1",
        "self_provenance": (
            "Generated authority files are excluded from recursive hashing. The source inventory "
            "proves listed source contents; hosted proof revision and run identity are recorded "
            "in the phase-specific receipts."
        ),
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

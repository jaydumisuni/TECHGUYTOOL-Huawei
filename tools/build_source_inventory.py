from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "manifests" / "source_inventory.json"
EXCLUDED = {
    "manifests/source_inventory.json",
    "manifests/source_inventory.receipt.json",
}
IGNORED_ROOTS = {"build", "dist", "proof", "wheelhouse"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "venv"}
IGNORED_EXACT = {"techguy_huawei/resources_rc.py"}
PHASE1_PREFIXES = (
    "docs/",
    "manifests/",
)
PHASE1_PATHS = {
    ".github/workflows/proof.yml",
    ".gitignore",
    "FULL_PLAN.md",
    "README.md",
    "tests/test_source_freeze.py",
    "tools/build_source_inventory.py",
    "tools/verify_source_freeze.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = path.relative_to(ROOT).parts
    return (
        rel.startswith(".git/")
        or rel in EXCLUDED
        or rel in IGNORED_EXACT
        or bool(parts and parts[0] in IGNORED_ROOTS)
        or any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in parts)
    )


def source_files() -> list[Path]:
    files = [path for path in ROOT.rglob("*") if path.is_file() and not is_ignored(path)]
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def origin_for(rel: str) -> str:
    if rel in PHASE1_PATHS or rel.startswith(PHASE1_PREFIXES):
        return "phase1_recovery_and_freeze"
    return "github_actions:huawei-source-workspace:8833608382"


def build() -> dict[str, object]:
    records = []
    for path in source_files():
        rel = path.relative_to(ROOT).as_posix()
        records.append(
            {
                "origin": origin_for(rel),
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
        "prepared_at": "2026-08-04T11:30:00Z",
        "private_recovery_authority": {
            "archive_sha256": "d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4",
            "copied_into_public_source": False,
            "drive_file_id": "1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs",
        },
        "schema": "techguytool-huawei.source-inventory.v1",
        "self_provenance": (
            "This manifest and its receipt are bound by the exact Git commit recorded in "
            "manifests/source_inventory.receipt.json."
        ),
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

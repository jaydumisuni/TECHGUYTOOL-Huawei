from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "source_inventory.json"
PRIVATE = ROOT / "manifests" / "private_source_archive.json"
EXTERNAL = ROOT / "manifests" / "external_artifacts.json"

FORBIDDEN_ROOTS = {
    "workspace-import",
    "final-patch-v1",
    "runtime-import",
    "runtime-export",
    "firmware",
    "backups",
    "logs",
    "work",
    "operation-journals",
}
FORBIDDEN_SUFFIXES = {
    ".img", ".mbn", ".bin", ".app", ".cpio", ".pyz", ".zip", ".7z",
    ".rar", ".exe", ".dll", ".so", ".b64",
}
SELF_EXCLUDED = {
    "manifests/source_inventory.json",
    "manifests/source_inventory.receipt.json",
}
IGNORED_ROOTS = {"build", "dist", "proof", "wheelhouse"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "venv"}
IGNORED_EXACT = {"techguy_huawei/resources_rc.py"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    parts = path.relative_to(ROOT).parts
    return (
        rel.startswith(".git/")
        or rel in SELF_EXCLUDED
        or rel in IGNORED_EXACT
        or bool(parts and parts[0] in IGNORED_ROOTS)
        or any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in parts)
    )


def _git_tracked_files() -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    paths = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8")
        if path.is_file() and not is_ignored(path):
            paths.append(path)
    return paths


def tracked_files() -> list[Path]:
    git_paths = _git_tracked_files()
    if git_paths is not None:
        files = git_paths
    else:
        files = [path for path in ROOT.rglob("*") if path.is_file() and not is_ignored(path)]
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def verify() -> list[str]:
    errors: list[str] = []
    for required in (ROOT / "FULL_PLAN.md", INVENTORY, PRIVATE, EXTERNAL):
        if not required.is_file():
            errors.append(f"missing required authority file: {required.relative_to(ROOT)}")

    for root in FORBIDDEN_ROOTS:
        if (ROOT / root).exists():
            errors.append(f"forbidden source-control root exists: {root}")

    actual_files = tracked_files()
    for path in actual_files:
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden runtime/binary file tracked: {rel}")
        if path.name.startswith("transfer-probe-") or path.name.startswith("transfer-test"):
            errors.append(f"temporary transfer file tracked: {rel}")

    if not INVENTORY.is_file():
        return errors
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if inventory.get("schema") != "techguytool-huawei.source-inventory.v1":
        errors.append("unexpected source inventory schema")
        return errors

    declared = {item["path"]: item for item in inventory.get("files", [])}
    actual_paths = {path.relative_to(ROOT).as_posix(): path for path in actual_files}

    missing = sorted(set(declared) - set(actual_paths))
    undeclared = sorted(set(actual_paths) - set(declared))
    for rel in missing:
        errors.append(f"declared source file missing: {rel}")
    for rel in undeclared:
        errors.append(f"source/proof file absent from inventory: {rel}")

    for rel in sorted(set(declared) & set(actual_paths)):
        item = declared[rel]
        path = actual_paths[rel]
        if item.get("size_bytes") != path.stat().st_size:
            errors.append(f"size mismatch: {rel}")
        if item.get("sha256") != digest(path):
            errors.append(f"sha256 mismatch: {rel}")

    private = json.loads(PRIVATE.read_text(encoding="utf-8"))
    authority = private.get("authority", {})
    if authority.get("sha256") != "d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4":
        errors.append("private archive authority hash changed")
    if authority.get("visibility") != "private":
        errors.append("private archive visibility is not fail-closed")

    external = json.loads(EXTERNAL.read_text(encoding="utf-8"))
    omitted = {item.get("id") for item in external.get("intentionally_omitted_inputs", [])}
    required_omitted = {
        "vog-l29-c185-base", "vog-l29-c185-cust", "vog-l29-c185-preload",
        "vog-al00-board-software", "vog-l29-merged-super",
    }
    if not required_omitted <= omitted:
        errors.append("external artifact manifest does not declare every intentionally omitted required input")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify TECHGUYTOOL Huawei Phase 1 source freeze")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = verify()
    payload = {"schema": "techguytool-huawei.source-freeze-verification.v1", "status": "PASS" if not errors else "FAIL", "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
    else:
        print("PASS: Phase 1 source freeze and external-artifact authority are coherent.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

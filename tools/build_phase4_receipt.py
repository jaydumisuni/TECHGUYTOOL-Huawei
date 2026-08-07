from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "source_inventory.json"
OUTPUT = ROOT / "manifests" / "phase4_kirin_xray.receipt.json"
EXPECTED_REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"
EXPECTED_WORKFLOW_NAME = "Phase 4 Harden Kirin Xray"
PRELIMINARY_STATUS = "PHASE4_KIRIN_XRAY_PROVEN_PENDING_OWNER"
FROZEN_STATUS = "PHASE4_KIRIN_XRAY_FROZEN"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_ALLOWED_POST_PROOF_CHANGES = {
    "manifests/phase4_kirin_xray.receipt.json",
    "manifests/source_inventory.json",
    "rust/device_gateway/Cargo.lock",
}
_REQUIRED_PROOF = {
    "phase4_python_compile",
    "phase4_unit_and_authority_tests",
    "p10_deterministic_replay",
    "p30_deterministic_replay",
    "phase2_contract_validation",
    "real_gateway_publication",
    "gateway_journal_verification",
    "gateway_restart_recovery",
    "provider_read_only_boundary",
    "forbidden_write_authority_rejection",
    "phase2_regression",
    "phase3_regression",
    "complete_python_regression",
    "source_freeze_verifier",
    "srg_20_for_2",
    "rust_toolchain",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _validate_proof_identity(
    tested_revision: str,
    proof_run_id: str,
    generated_at: str,
    proof_run_url: str,
) -> None:
    if _SHA_RE.fullmatch(tested_revision) is None:
        raise ValueError("tested revision must be a full lowercase Git commit SHA")
    if not proof_run_id.isdigit() or int(proof_run_id) <= 0:
        raise ValueError("proof run identifier must be a positive integer")
    if _TIMESTAMP_RE.fullmatch(generated_at) is None:
        raise ValueError("generation timestamp must use YYYY-MM-DDTHH:MM:SSZ")
    expected_url = (
        f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{proof_run_id}"
    )
    if proof_run_url != expected_url:
        raise ValueError("proof run URL does not identify the canonical repository/run")


def _load_hosted_run(proof_run_id: str) -> dict[str, Any]:
    url = (
        f"https://api.github.com/repos/{EXPECTED_REPOSITORY}/actions/runs/"
        f"{proof_run_id}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TECHGUYTOOL-Huawei-phase4-verifier",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def verify_hosted_run(proof_run_id: str, tested_revision: str) -> None:
    run = _load_hosted_run(proof_run_id)
    repository = run.get("repository")
    full_name = repository.get("full_name") if isinstance(repository, dict) else None
    if full_name != EXPECTED_REPOSITORY:
        raise ValueError("hosted proof run belongs to a different repository")
    if run.get("head_sha") != tested_revision:
        raise ValueError("hosted proof run head SHA does not match tested_revision")
    if run.get("name") != EXPECTED_WORKFLOW_NAME:
        raise ValueError("hosted proof run is not the Phase 4 workflow")
    if str(run.get("id")) != proof_run_id:
        raise ValueError("hosted proof run ID does not match the receipt")


def build(
    *,
    tested_revision: str,
    proof_run_id: str,
    generated_at: str,
    proof_run_url: str,
) -> dict[str, object]:
    _validate_proof_identity(tested_revision, proof_run_id, generated_at, proof_run_url)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    phase4_files = [
        item
        for item in inventory.get("files", [])
        if item.get("origin") == "phase4_kirin_xray"
    ]
    required_paths = {
        ".github/workflows/phase4-kirin-xray.yml",
        "docs/PHASE_4_KIRIN_XRAY.md",
        "manifests/kirin_xray_sources.json",
        "replay/kirin/p10_golden_workflow.json",
        "replay/kirin/p30_main_version_mode_hazard.json",
        "techguy_huawei/kirin_xray.py",
        "techguy_huawei/kirin_xray_authority.py",
        "tests/test_kirin_xray.py",
        "tests/test_kirin_xray_authority.py",
        "tools/build_phase4_receipt.py",
        "tools/prove_kirin_xray_replay.py",
    }
    actual_paths = {str(item.get("path")) for item in phase4_files}
    missing = sorted(required_paths - actual_paths)
    if missing:
        raise ValueError("source inventory is missing Phase 4 proof/source files: " + ", ".join(missing))

    return {
        "schema": "techguytool-huawei.phase4-kirin-xray-receipt.v1",
        "status": PRELIMINARY_STATUS,
        "generated_at": generated_at,
        "phase3_merge_commit": "40bb352f3f2ea2da1f7ec6cc977a30ba4dc2d3dd",
        "hosted_proof": {
            "repository": EXPECTED_REPOSITORY,
            "workflow": EXPECTED_WORKFLOW_NAME,
            "tested_revision": tested_revision,
            "run_id": int(proof_run_id),
            "run_url": proof_run_url,
        },
        "phase4": {
            "branch": "phase4/harden-kirin-xray",
            "provider_id": "kirin.xray",
            "provider_version": "0.2.0",
            "specialist_donor_commit": "d26152d38c197ba0bf98f41a66bed7ceb0575ce1",
            "replay_cases": 2,
            "phase4_unit_tests": 15,
            "device_authority": "none",
            "xray_authority": "read_only",
            "phase4_file_count": len(phase4_files),
        },
        "proof": {
            "phase4_python_compile": "PASS",
            "phase4_unit_and_authority_tests": "PASS",
            "p10_deterministic_replay": "PASS",
            "p30_deterministic_replay": "PASS",
            "phase2_contract_validation": "PASS",
            "real_gateway_publication": "PASS",
            "gateway_journal_verification": "PASS",
            "gateway_restart_recovery": "PASS",
            "provider_read_only_boundary": "PASS",
            "forbidden_write_authority_rejection": "PASS",
            "phase2_regression": "PASS",
            "phase3_regression": "PASS",
            "complete_python_regression": "PASS",
            "source_freeze_verifier": "PASS",
            "srg_20_for_2": "40/40 PASS",
            "rust_toolchain": "1.75.0",
        },
        "source_inventory": {
            "path": "manifests/source_inventory.json",
            "file_count": inventory.get("file_count"),
            "sha256": sha256(INVENTORY),
        },
        "truth_boundary": (
            "This receipt proves only Phase 4 deterministic read-only Kirin Xray replay, "
            "provider authority, frozen Phase 2 contract emission, real Gateway publication, "
            "journal integrity and restart recovery. It does not prove live Huawei USB discovery, "
            "loader compatibility, OEMINFO construction or modification, partition writes, "
            "flashing, reboot, unlock/relock, physical VOG recovery, Windows packaging or signing."
        ),
    }


def verify(*, verify_run: bool = False) -> None:
    receipt = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "techguytool-huawei.phase4-kirin-xray-receipt.v1":
        raise ValueError("unsupported Phase 4 receipt schema")
    status = receipt.get("status")
    if status not in {PRELIMINARY_STATUS, FROZEN_STATUS}:
        raise ValueError("unsupported Phase 4 receipt status")

    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise ValueError("Phase 4 receipt is missing hosted proof identity")
    if hosted.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("Phase 4 receipt repository identity changed")
    if hosted.get("workflow") != EXPECTED_WORKFLOW_NAME:
        raise ValueError("Phase 4 receipt workflow identity changed")
    tested_revision = str(hosted.get("tested_revision"))
    run_id = str(hosted.get("run_id"))
    run_url = str(hosted.get("run_url"))
    generated_at = str(receipt.get("generated_at"))
    _validate_proof_identity(tested_revision, run_id, generated_at, run_url)
    if verify_run:
        verify_hosted_run(run_id, tested_revision)

    phase4 = receipt.get("phase4")
    if not isinstance(phase4, dict):
        raise ValueError("Phase 4 receipt is missing phase metadata")
    if phase4.get("device_authority") != "none":
        raise ValueError("Phase 4 may not carry device authority")
    if phase4.get("xray_authority") != "read_only":
        raise ValueError("Phase 4 Xray authority must remain read_only")

    proof = receipt.get("proof")
    if not isinstance(proof, dict):
        raise ValueError("Phase 4 receipt is missing proof results")
    proof_keys = set(proof)
    missing_keys = sorted(_REQUIRED_PROOF - proof_keys)
    unknown_keys = sorted(proof_keys - _REQUIRED_PROOF)
    if missing_keys or unknown_keys:
        raise ValueError(
            f"Phase 4 proof key mismatch; missing={missing_keys} unknown={unknown_keys}"
        )
    failed = [
        name
        for name, value in proof.items()
        if name not in {"rust_toolchain", "srg_20_for_2"} and value != "PASS"
    ]
    if failed:
        raise ValueError("Phase 4 receipt contains non-PASS proof fields: " + ", ".join(failed))
    if proof["rust_toolchain"] != "1.75.0":
        raise ValueError("Phase 4 receipt records an unsupported Rust toolchain")
    if proof["srg_20_for_2"] != "40/40 PASS":
        raise ValueError("Phase 4 receipt does not prove the SRG 20-for-2 gate")

    inventory = receipt.get("source_inventory")
    if not isinstance(inventory, dict):
        raise ValueError("Phase 4 receipt is missing source inventory identity")

    owner = receipt.get("owner_verification")
    if status == FROZEN_STATUS:
        if not isinstance(owner, dict) or owner.get("status") != "CONFIRMED":
            raise ValueError("frozen Phase 4 receipt requires confirmed owner verification")
        authority_commit = str(owner.get("authority_commit"))
        source_revision = str(owner.get("source_revision"))
        source_run_id = str(owner.get("source_proof_run_id"))
        if _SHA_RE.fullmatch(authority_commit) is None:
            raise ValueError("owner verification authority_commit is invalid")
        if source_revision != tested_revision or source_run_id != run_id:
            raise ValueError("owner verification does not match hosted proof identity")
        _require_ancestor(tested_revision, authority_commit)
        _require_ancestor(authority_commit, "HEAD")
        inventory_bytes = _git_file_bytes(authority_commit, "manifests/source_inventory.json")
        if inventory.get("sha256") != sha256_bytes(inventory_bytes):
            raise ValueError("Phase 4 receipt does not match its authority inventory")
        changed = _changed_files(tested_revision, authority_commit)
    else:
        if owner is not None:
            raise ValueError("preliminary Phase 4 receipt must not claim owner verification")
        _require_ancestor(tested_revision, "HEAD")
        if inventory.get("sha256") != sha256(INVENTORY):
            raise ValueError("Phase 4 receipt does not match the committed source inventory")
        changed = _changed_files(tested_revision, "HEAD")

    unexpected = sorted(set(changed) - _ALLOWED_POST_PROOF_CHANGES)
    if unexpected:
        raise ValueError("source changed after hosted proof: " + ", ".join(unexpected))


def _require_ancestor(ancestor: str, descendant: str) -> None:
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )


def _changed_files(base: str, head: str) -> list[str]:
    return subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).stdout.splitlines()


def _git_file_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the Phase 4 proof receipt")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-hosted-run", action="store_true")
    parser.add_argument("--tested-revision")
    parser.add_argument("--proof-run-id")
    parser.add_argument("--generated-at")
    parser.add_argument("--proof-run-url")
    args = parser.parse_args()

    if not INVENTORY.is_file():
        raise SystemExit("source inventory must be generated first")
    if args.verify:
        verify(verify_run=args.verify_hosted_run)
        print(f"VERIFIED {OUTPUT.relative_to(ROOT)}")
        return 0

    required = {
        "--tested-revision": args.tested_revision,
        "--proof-run-id": args.proof_run_id,
        "--generated-at": args.generated_at,
        "--proof-run-url": args.proof_run_url,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise SystemExit("missing required hosted proof arguments: " + ", ".join(missing))

    _validate_proof_identity(
        str(args.tested_revision),
        str(args.proof_run_id),
        str(args.generated_at),
        str(args.proof_run_url),
    )
    if args.verify_hosted_run:
        verify_hosted_run(str(args.proof_run_id), str(args.tested_revision))
    payload = build(
        tested_revision=str(args.tested_revision),
        proof_run_id=str(args.proof_run_id),
        generated_at=str(args.generated_at),
        proof_run_url=str(args.proof_run_url),
    )
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

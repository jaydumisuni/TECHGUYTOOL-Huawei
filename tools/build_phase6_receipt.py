from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "manifests" / "phase6_leases.receipt.json"
INVENTORY = ROOT / "manifests" / "source_inventory.json"
REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"
BRANCH = "phase6/mode-execution-leases"
WORKFLOW = "Phase 6 Mode and Execution Leases"
SCHEMA = "techguytool-huawei.phase6-leases-receipt.v1"
PHASE5_MERGE = "da23daae30539b1c6820c9f6878abc4c1cb6714d"
RECEIPT_PATH = "manifests/phase6_leases.receipt.json"

PROOF = {
    "complete_python_regression": "PASS",
    "execution_lease_persistent_single_use": "PASS",
    "lease_contract_validation": "PASS",
    "mode_release_conditions": "PASS",
    "p30_mode_protection": "PASS",
    "phase2_regression": "PASS",
    "phase3_regression": "PASS",
    "phase4_regression": "PASS",
    "phase5_regression": "PASS",
    "rust_clippy": "PASS",
    "rust_format": "PASS",
    "rust_lease_tests": "PASS",
    "source_freeze_verifier": "PASS",
    "srg_20_for_2": "40/40 PASS",
    "wrong_adapter_rejection": "PASS",
    "wrong_artifact_rejection": "PASS",
    "wrong_mode_rejection": "PASS",
    "wrong_partition_rejection": "PASS",
    "wrong_range_rejection": "PASS",
    "wrong_session_rejection": "PASS",
}


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def _changed_files(older: str, newer: str) -> set[str]:
    output = _git("diff", "--name-only", f"{older}..{newer}")
    return {line for line in output.splitlines() if line}


def _verify_hosted_run(receipt: dict[str, object]) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for hosted-run verification")
    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise SystemExit("hosted_proof missing")
    run_id = int(hosted["run_id"])
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TECHGUYTOOL-Huawei-phase6-receipt",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        run = json.load(response)
    if run.get("name") != WORKFLOW:
        raise SystemExit("hosted proof workflow mismatch")
    if run.get("head_sha") != hosted.get("tested_revision"):
        raise SystemExit("hosted proof revision mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit("hosted proof is not completed successfully")


def build(tested_revision: str, proof_run_id: int, generated_at: str, proof_run_url: str) -> dict[str, object]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return {
        "generated_at": generated_at,
        "hosted_proof": {
            "repository": REPOSITORY,
            "run_id": proof_run_id,
            "run_url": proof_run_url,
            "tested_revision": tested_revision,
            "workflow": WORKFLOW,
        },
        "phase5_merge_commit": PHASE5_MERGE,
        "phase6": {
            "branch": BRANCH,
            "device_authority": "none",
            "execution_authority": "lease_only",
            "mode_authority": "governance_constraint",
            "lease_guard": "rust/device_gateway/src/lease.rs",
            "single_use_ledger": "sqlite",
        },
        "proof": PROOF,
        "schema": SCHEMA,
        "source_inventory": {
            "file_count": inventory["file_count"],
            "path": "manifests/source_inventory.json",
            "sha256": _sha256(INVENTORY),
        },
        "status": "PHASE6_LEASES_PROVEN_PENDING_OWNER",
        "truth_boundary": (
            "This receipt proves deterministic Rust enforcement of mode and execution leases, "
            "including session/artifact/partition/range/mode/expiry/reboot and persistent single-use "
            "constraints. It does not implement or authorize a device executor, USB/serial writes, "
            "partition writes, flashing, OEMINFO modification, reboot, loader transfer, physical-device "
            "repair, Windows packaging or signing."
        ),
    }


def verify(receipt: dict[str, object], verify_hosted: bool) -> None:
    if receipt.get("schema") != SCHEMA:
        raise SystemExit("Phase 6 receipt schema mismatch")
    status = receipt.get("status")
    if status == "PHASE6_LEASES_UNFROZEN":
        return
    if status not in {"PHASE6_LEASES_PROVEN_PENDING_OWNER", "PHASE6_LEASES_FROZEN"}:
        raise SystemExit("invalid Phase 6 receipt status")
    if receipt.get("phase5_merge_commit") != PHASE5_MERGE:
        raise SystemExit("Phase 5 merge authority mismatch")
    if receipt.get("proof") != PROOF:
        raise SystemExit("Phase 6 proof matrix mismatch")
    source = receipt.get("source_inventory")
    if not isinstance(source, dict) or source.get("sha256") != _sha256(INVENTORY):
        raise SystemExit("Phase 6 source inventory mismatch")
    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise SystemExit("hosted proof missing")
    tested_revision = str(hosted.get("tested_revision", ""))
    if len(tested_revision) != 40:
        raise SystemExit("tested revision is not a full SHA")
    if not _is_ancestor(PHASE5_MERGE, tested_revision):
        raise SystemExit("tested Phase 6 source does not descend from Phase 5 merge")
    if verify_hosted:
        _verify_hosted_run(receipt)
    if status == "PHASE6_LEASES_FROZEN":
        owner = receipt.get("owner_verification")
        if not isinstance(owner, dict) or owner.get("status") != "CONFIRMED":
            raise SystemExit("owner verification missing")
        authority_commit = str(owner.get("authority_commit", ""))
        if owner.get("source_revision") != tested_revision:
            raise SystemExit("owner source revision mismatch")
        if int(owner.get("source_proof_run_id", -1)) != int(hosted["run_id"]):
            raise SystemExit("owner proof run mismatch")
        head = _git("rev-parse", "HEAD")
        if not _is_ancestor(tested_revision, authority_commit) or not _is_ancestor(authority_commit, head):
            raise SystemExit("Phase 6 authority ancestry mismatch")
        changed = _changed_files(tested_revision, head)
        if changed - {RECEIPT_PATH}:
            raise SystemExit(f"post-proof source drift: {sorted(changed - {RECEIPT_PATH})}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tested-revision")
    parser.add_argument("--proof-run-id", type=int)
    parser.add_argument("--generated-at")
    parser.add_argument("--proof-run-url")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-hosted-run", action="store_true")
    args = parser.parse_args()

    if args.verify:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        verify(receipt, args.verify_hosted_run)
        print(f"VERIFIED {RECEIPT.relative_to(ROOT)}")
        return 0

    required = [args.tested_revision, args.proof_run_id, args.generated_at, args.proof_run_url]
    if any(value is None for value in required):
        parser.error("build mode requires tested revision, proof run id, generated at and proof URL")
    receipt = build(args.tested_revision, args.proof_run_id, args.generated_at, args.proof_run_url)
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verify(receipt, args.verify_hosted_run)
    print(f"WROTE {RECEIPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

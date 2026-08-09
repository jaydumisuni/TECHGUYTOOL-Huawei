from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "manifests" / "phase6_leases.receipt.json"
REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"
EXPECTED_SCHEMA = "techguytool-huawei.phase6-leases-receipt.v1"
EXPECTED_STATUS = "PHASE6_LEASES_FROZEN"
EXPECTED_WORKFLOW = "Phase 6 Mode and Execution Leases"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def verify_hosted_run(hosted: dict[str, object]) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for historical Phase 6 proof verification")
    run_id = int(hosted["run_id"])
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TECHGUYTOOL-Huawei-historical-phase6",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        run = json.load(response)
    if run.get("name") != EXPECTED_WORKFLOW:
        raise SystemExit("historical Phase 6 workflow mismatch")
    if run.get("head_sha") != hosted.get("tested_revision"):
        raise SystemExit("historical Phase 6 tested revision mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit("historical Phase 6 hosted proof is not successful")


def main() -> int:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("schema") != EXPECTED_SCHEMA or receipt.get("status") != EXPECTED_STATUS:
        raise SystemExit("historical Phase 6 receipt is not frozen authority")

    proof = receipt.get("proof")
    if not isinstance(proof, dict) or proof.get("srg_20_for_2") != "40/40 PASS":
        raise SystemExit("historical Phase 6 SRG authority missing")
    if any(value != "PASS" and key != "srg_20_for_2" for key, value in proof.items()):
        raise SystemExit("historical Phase 6 proof matrix contains a non-PASS result")

    source = receipt.get("source_inventory")
    if not isinstance(source, dict):
        raise SystemExit("historical Phase 6 source inventory record missing")
    source_hash = str(source.get("sha256", ""))
    if len(source_hash) != 64 or any(char not in "0123456789abcdef" for char in source_hash):
        raise SystemExit("historical Phase 6 source inventory hash is malformed")

    hosted = receipt.get("hosted_proof")
    owner = receipt.get("owner_verification")
    if not isinstance(hosted, dict) or not isinstance(owner, dict):
        raise SystemExit("historical Phase 6 hosted or owner authority missing")
    if owner.get("status") != "CONFIRMED":
        raise SystemExit("historical Phase 6 owner verification is not confirmed")

    tested = str(hosted.get("tested_revision", ""))
    authority = str(owner.get("authority_commit", ""))
    predecessor = str(receipt.get("phase5_merge_commit", ""))
    head = git("rev-parse", "HEAD")
    for name, value in (("tested", tested), ("authority", authority), ("predecessor", predecessor)):
        if len(value) != 40:
            raise SystemExit(f"historical Phase 6 {name} revision is not a full SHA")
    if owner.get("source_revision") != tested:
        raise SystemExit("historical Phase 6 owner source revision mismatch")
    if int(owner.get("source_proof_run_id", -1)) != int(hosted.get("run_id", -2)):
        raise SystemExit("historical Phase 6 owner proof run mismatch")
    if not is_ancestor(predecessor, tested):
        raise SystemExit("historical Phase 6 tested source does not descend from Phase 5")
    if not is_ancestor(tested, authority):
        raise SystemExit("historical Phase 6 authority commit does not descend from tested source")
    if not is_ancestor(authority, head):
        raise SystemExit("current source does not descend from frozen Phase 6 authority")

    verify_hosted_run(hosted)
    print(
        "HISTORICAL PHASE 6 AUTHORITY PASS "
        f"tested={tested} run={hosted['run_id']} frozen_inventory={source_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

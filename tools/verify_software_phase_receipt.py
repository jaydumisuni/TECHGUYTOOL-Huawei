from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "manifests" / "active_software_phase.json"
INVENTORY = ROOT / "manifests" / "source_inventory.json"
REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def verify_hosted(receipt: dict[str, object]) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for hosted proof verification")
    hosted = receipt["hosted_proof"]
    assert isinstance(hosted, dict)
    run_id = int(hosted["run_id"])
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TECHGUYTOOL-Huawei-software-phase",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        run = json.load(response)
    if run.get("name") != "Software Phase Proof":
        raise SystemExit("hosted proof workflow mismatch")
    if run.get("head_sha") != hosted.get("tested_revision"):
        raise SystemExit("hosted proof revision mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit("hosted proof is not successful")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-hosted-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    phase = int(config["phase"])
    receipt_path = ROOT / str(config["receipt_path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") == "UNFROZEN":
        print(f"UNFROZEN phase={phase}")
        return 0
    expected_schema = f"techguytool-huawei.phase{phase}-receipt.v1"
    if receipt.get("schema") != expected_schema:
        raise SystemExit("software phase receipt schema mismatch")
    if receipt.get("phase") != phase:
        raise SystemExit("software phase number mismatch")
    if receipt.get("predecessor_merge") != config.get("predecessor_merge"):
        raise SystemExit("software phase predecessor mismatch")
    inventory = receipt.get("source_inventory")
    if not isinstance(inventory, dict) or inventory.get("sha256") != sha256(INVENTORY):
        raise SystemExit("software phase source inventory mismatch")
    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise SystemExit("hosted proof missing")
    tested_revision = str(hosted.get("tested_revision", ""))
    if len(tested_revision) != 40:
        raise SystemExit("tested revision must be a full SHA")
    predecessor = str(config["predecessor_merge"])
    if not is_ancestor(predecessor, tested_revision):
        raise SystemExit("tested source does not descend from predecessor merge")
    if args.verify_hosted_run:
        verify_hosted(receipt)
    if receipt.get("status") == "FROZEN":
        owner = receipt.get("owner_verification")
        if not isinstance(owner, dict) or owner.get("status") != "CONFIRMED":
            raise SystemExit("owner verification missing")
        if owner.get("source_revision") != tested_revision:
            raise SystemExit("owner source revision mismatch")
        if int(owner.get("source_proof_run_id", -1)) != int(hosted["run_id"]):
            raise SystemExit("owner proof run mismatch")
        authority_commit = str(owner.get("authority_commit", ""))
        head = git("rev-parse", "HEAD")
        if not is_ancestor(tested_revision, authority_commit) or not is_ancestor(authority_commit, head):
            raise SystemExit("owner authority ancestry mismatch")
        changed = set(git("diff", "--name-only", f"{tested_revision}..{head}").splitlines())
        allowed = {str(config["receipt_path"]), "manifests/active_software_phase.json"}
        if changed - allowed:
            raise SystemExit(f"post-proof source drift: {sorted(changed - allowed)}")
    print(f"VERIFIED phase={phase} status={receipt['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

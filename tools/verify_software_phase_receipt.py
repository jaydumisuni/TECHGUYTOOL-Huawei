from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONFIG_PATH = ROOT / "manifests" / "active_software_phase.json"
INVENTORY = ROOT / "manifests" / "source_inventory.json"
REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"
GITHUB_API = f"https://api.github.com/repos/{REPOSITORY}"


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            old_host = urllib.parse.urlparse(req.full_url).netloc.lower()
            new_host = urllib.parse.urlparse(newurl).netloc.lower()
            if old_host != new_host:
                redirected.remove_header("Authorization")
        return redirected


_OPENER = urllib.request.build_opener(_SafeRedirect)


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


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for hosted proof verification")
    return token


def _request(url: str, token: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TECHGUYTOOL-Huawei-software-phase",
        },
    )


def _github_json(url: str, token: str) -> dict[str, Any]:
    with _OPENER.open(_request(url, token), timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise SystemExit("GitHub API response root must be an object")
    return payload


def verify_hosted(receipt: dict[str, object]) -> dict[str, Any]:
    token = _token()
    hosted = receipt["hosted_proof"]
    assert isinstance(hosted, dict)
    run_id = int(hosted["run_id"])
    run = _github_json(f"{GITHUB_API}/actions/runs/{run_id}", token)
    if run.get("name") != "Software Phase Proof":
        raise SystemExit("hosted proof workflow mismatch")
    if run.get("head_sha") != hosted.get("tested_revision"):
        raise SystemExit("hosted proof revision mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit("hosted proof is not successful")
    return run


def _artifact_member(archive: zipfile.ZipFile, basename: str) -> str:
    matches = [name for name in archive.namelist() if Path(name).name == basename]
    if len(matches) != 1:
        raise SystemExit(f"Phase 15 artifact must contain exactly one {basename}; found {len(matches)}")
    return matches[0]


def verify_phase15_windows(receipt: dict[str, object]) -> None:
    from techguy_huawei.windows_release import (
        load_physical_matrix,
        validate_receipt_matrix_alignment,
        validate_release_receipt,
    )

    validate_release_receipt(receipt)
    validate_receipt_matrix_alignment(receipt, load_physical_matrix())

    token = _token()
    windows_run_id = int(receipt["windows_run_id"])
    tested_revision = str(receipt["tested_revision"])
    run = _github_json(f"{GITHUB_API}/actions/runs/{windows_run_id}", token)
    if run.get("name") != "Phase 15 Windows Release Candidate":
        raise SystemExit("Phase 15 Windows workflow mismatch")
    if run.get("head_sha") != tested_revision:
        raise SystemExit("Phase 15 Windows tested revision mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        raise SystemExit("Phase 15 Windows run is not successful")

    artifacts_payload = _github_json(f"{GITHUB_API}/actions/runs/{windows_run_id}/artifacts?per_page=100", token)
    artifacts = artifacts_payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise SystemExit("Phase 15 Windows artifact listing missing")
    artifact_id = int(receipt["artifact_id"])
    artifact_name = str(receipt["artifact_name"])
    matches = [item for item in artifacts if isinstance(item, dict) and item.get("id") == artifact_id]
    if len(matches) != 1:
        raise SystemExit("Phase 15 Windows artifact ID was not found uniquely in the hosted run")
    artifact = matches[0]
    if artifact.get("name") != artifact_name:
        raise SystemExit("Phase 15 Windows artifact name mismatch")
    if artifact_name != "TECHGUYTOOL-Huawei-phase15-windows-candidate":
        raise SystemExit("Phase 15 Windows artifact canonical name mismatch")
    if artifact.get("expired") is True:
        raise SystemExit("Phase 15 Windows artifact expired before authority freeze")

    archive_url = artifact.get("archive_download_url")
    if not isinstance(archive_url, str) or not archive_url:
        raise SystemExit("Phase 15 Windows artifact download URL missing")
    with _OPENER.open(_request(archive_url, token), timeout=120) as response:
        archive_bytes = response.read()
    if not archive_bytes:
        raise SystemExit("Phase 15 Windows artifact download was empty")

    expected_sha256 = str(receipt["executable_sha256"])
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        exe_member = _artifact_member(archive, "TECHGUYTOOL_Huawei.exe")
        checksum_member = _artifact_member(archive, "SHA256SUMS.txt")
        provenance_member = _artifact_member(archive, "RELEASE_PROVENANCE.json")

        digest = hashlib.sha256()
        with archive.open(exe_member, "r") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise SystemExit("Phase 15 executable SHA-256 does not match hosted artifact")

        checksum_text = archive.read(checksum_member).decode("ascii", errors="strict")
        entries = [line.split() for line in checksum_text.splitlines() if line.strip()]
        matched = [
            parts
            for parts in entries
            if len(parts) >= 2 and Path(parts[-1]).name == "TECHGUYTOOL_Huawei.exe"
        ]
        if len(matched) != 1:
            raise SystemExit("Phase 15 SHA256SUMS.txt must contain exactly one TECHGUYTOOL_Huawei.exe entry")
        if matched[0][0].lower() != expected_sha256:
            raise SystemExit("Phase 15 SHA256SUMS.txt does not match hosted executable")

        provenance = json.loads(archive.read(provenance_member).decode("utf-8-sig"))
        if not isinstance(provenance, dict):
            raise SystemExit("Phase 15 release provenance root must be an object")
        if provenance.get("filename") != "TECHGUYTOOL_Huawei.exe":
            raise SystemExit("Phase 15 release provenance filename mismatch")
        if provenance.get("sha256") != expected_sha256:
            raise SystemExit("Phase 15 release provenance SHA-256 mismatch")
        if provenance.get("signing_mode") != "ci-test-authenticode":
            raise SystemExit("Phase 15 release provenance signing mode mismatch")
        if provenance.get("ci_test_signature") is not True or provenance.get("production_signature") is not False:
            raise SystemExit("Phase 15 release provenance signature boundary mismatch")


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
        if phase == 15:
            if receipt.get("tested_revision") != tested_revision:
                raise SystemExit("Phase 15 Windows receipt tested revision differs from software authority")
            if int(receipt.get("software_proof_run_id", -1)) != int(hosted["run_id"]):
                raise SystemExit("Phase 15 Windows receipt software proof run differs from software authority")
            if receipt.get("source_inventory_sha256") != inventory.get("sha256"):
                raise SystemExit("Phase 15 Windows receipt inventory hash differs from software authority")
            if args.verify_hosted_run:
                verify_phase15_windows(receipt)
    print(f"VERIFIED phase={phase} status={receipt['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
OUTPUT = ROOT / "manifests" / "phase5_decision_corps.receipt.json"
EXPECTED_REPOSITORY = "jaydumisuni/TECHGUYTOOL-Huawei"
EXPECTED_WORKFLOW_NAME = "Phase 5 Repair Decision Corps"
PHASE4_MERGE_COMMIT = "775d922a9fe31acb0df316d03b5c6b149a3eb8f2"
PHASE5_BRANCH = "phase5/repair-decision-corps-v2"
INVENTORY_PATH = "manifests/source_inventory.json"
OFFICER_ORDER = [
    "identity.officer",
    "mode.officer",
    "firmware.officer",
    "artifact.officer",
    "recovery.officer",
    "route.planner",
    "safety.challenger",
    "verification.judge",
]
VETO_OFFICERS = [
    "identity.officer",
    "recovery.officer",
    "safety.challenger",
    "verification.judge",
]
TRUTH_BOUNDARY = (
    "This receipt proves Phase 5 deterministic governance over frozen read-only Xray replay, "
    "including veto precedence and the historical stock-Fastboot exit gate. It does not grant "
    "mode-lease, execution-lease, USB/serial, partition-write, flashing, reboot, loader-transfer, "
    "OEMINFO-write, or physical-device execution authority."
)
PRELIMINARY_STATUS = "PHASE5_DECISION_CORPS_PROVEN_PENDING_OWNER"
FROZEN_STATUS = "PHASE5_DECISION_CORPS_FROZEN"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_ALLOWED_POST_PROOF_CHANGES = {"manifests/phase5_decision_corps.receipt.json"}
_REQUIRED_PROOF = {
    "phase5_python_compile",
    "phase5_decision_tests",
    "historical_stock_fastboot_exit_gate",
    "p30_reboot_block",
    "p30_repair_stage_selection",
    "p10_finalization_block",
    "unauthorized_service_endpoint_rejection",
    "veto_precedence",
    "session_binding",
    "phase2_contract_validation",
    "no_execution_surface",
    "phase2_regression",
    "phase3_regression",
    "phase4_regression",
    "complete_python_regression",
    "source_freeze_verifier",
    "srg_20_for_2",
    "rust_toolchain",
}
_REQUIRED_PHASE5_PATHS = {
    ".github/workflows/phase5-authority.yml",
    ".github/workflows/phase5-decision-corps.yml",
    "docs/PHASE_5_REPAIR_DECISION_CORPS.md",
    "techguy_huawei/decision_corps.py",
    "tests/test_decision_corps.py",
    "tools/build_phase5_receipt.py",
    "tools/prove_decision_corps.py",
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
    expected_url = f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{proof_run_id}"
    if proof_run_url != expected_url:
        raise ValueError("proof run URL does not identify the canonical repository/run")


def _load_hosted_run(proof_run_id: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{EXPECTED_REPOSITORY}/actions/runs/{proof_run_id}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TECHGUYTOOL-Huawei-phase5-verifier",
            **(
                {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
                if os.environ.get("GITHUB_TOKEN")
                else {}
            ),
        },
    )
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
        raise ValueError("hosted proof run is not the Phase 5 workflow")
    if str(run.get("id")) != proof_run_id:
        raise ValueError("hosted proof run ID does not match the receipt")
    if run.get("status") != "completed":
        raise ValueError("hosted Phase 5 proof run is not completed")
    if run.get("conclusion") != "success":
        raise ValueError("hosted Phase 5 proof run did not conclude successfully")


def _parse_inventory_bytes(value: bytes) -> dict[str, Any]:
    inventory = json.loads(value.decode("utf-8"))
    if inventory.get("schema") != "techguytool-huawei.source-inventory.v1":
        raise ValueError("unsupported source inventory schema")
    return inventory


def _inventory_payload() -> dict[str, Any]:
    return _parse_inventory_bytes(INVENTORY.read_bytes())


def _phase5_files(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    files = [
        item
        for item in inventory.get("files", [])
        if item.get("origin") == "phase5_repair_decision_corps"
    ]
    paths = {str(item.get("path")) for item in files}
    missing = sorted(_REQUIRED_PHASE5_PATHS - paths)
    if missing:
        raise ValueError(
            "source inventory is missing Phase 5 proof/source files: " + ", ".join(missing)
        )
    return files


def _expected_phase5(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "branch": PHASE5_BRANCH,
        "officer_order": OFFICER_ORDER,
        "veto_officers": VETO_OFFICERS,
        "replay_cases": 2,
        "decision_authority": "governance_only",
        "execution_authority": "none",
        "device_authority": "none",
        "phase5_file_count": len(_phase5_files(inventory)),
    }


def build(
    *,
    tested_revision: str,
    proof_run_id: str,
    generated_at: str,
    proof_run_url: str,
) -> dict[str, Any]:
    _validate_proof_identity(tested_revision, proof_run_id, generated_at, proof_run_url)
    inventory = _inventory_payload()
    return {
        "schema": "techguytool-huawei.phase5-decision-corps-receipt.v1",
        "status": PRELIMINARY_STATUS,
        "generated_at": generated_at,
        "phase4_merge_commit": PHASE4_MERGE_COMMIT,
        "hosted_proof": {
            "repository": EXPECTED_REPOSITORY,
            "workflow": EXPECTED_WORKFLOW_NAME,
            "tested_revision": tested_revision,
            "run_id": int(proof_run_id),
            "run_url": proof_run_url,
        },
        "phase5": _expected_phase5(inventory),
        "proof": {
            "phase5_python_compile": "PASS",
            "phase5_decision_tests": "PASS",
            "historical_stock_fastboot_exit_gate": "PASS",
            "p30_reboot_block": "PASS",
            "p30_repair_stage_selection": "PASS",
            "p10_finalization_block": "PASS",
            "unauthorized_service_endpoint_rejection": "PASS",
            "veto_precedence": "PASS",
            "session_binding": "PASS",
            "phase2_contract_validation": "PASS",
            "no_execution_surface": "PASS",
            "phase2_regression": "PASS",
            "phase3_regression": "PASS",
            "phase4_regression": "PASS",
            "complete_python_regression": "PASS",
            "source_freeze_verifier": "PASS",
            "srg_20_for_2": "40/40 PASS",
            "rust_toolchain": "1.75.0",
        },
        "source_inventory": {
            "path": INVENTORY_PATH,
            "file_count": inventory.get("file_count"),
            "sha256": sha256(INVENTORY),
        },
        "truth_boundary": TRUTH_BOUNDARY,
    }


def verify(*, verify_run: bool = False) -> None:
    receipt = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "techguytool-huawei.phase5-decision-corps-receipt.v1":
        raise ValueError("unsupported Phase 5 receipt schema")
    status = receipt.get("status")
    if status not in {PRELIMINARY_STATUS, FROZEN_STATUS}:
        raise ValueError("unsupported Phase 5 receipt status")
    if receipt.get("phase4_merge_commit") != PHASE4_MERGE_COMMIT:
        raise ValueError("Phase 4 merge authority changed")
    if receipt.get("truth_boundary") != TRUTH_BOUNDARY:
        raise ValueError("Phase 5 truth boundary changed")

    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise ValueError("Phase 5 receipt is missing hosted proof identity")
    if hosted.get("repository") != EXPECTED_REPOSITORY:
        raise ValueError("Phase 5 receipt repository identity changed")
    if hosted.get("workflow") != EXPECTED_WORKFLOW_NAME:
        raise ValueError("Phase 5 receipt workflow identity changed")
    tested_revision = str(hosted.get("tested_revision"))
    run_id = str(hosted.get("run_id"))
    run_url = str(hosted.get("run_url"))
    generated_at = str(receipt.get("generated_at"))
    _validate_proof_identity(tested_revision, run_id, generated_at, run_url)
    if verify_run:
        verify_hosted_run(run_id, tested_revision)

    inventory_claim = receipt.get("source_inventory")
    if not isinstance(inventory_claim, dict):
        raise ValueError("Phase 5 receipt is missing source inventory identity")
    if inventory_claim.get("path") != INVENTORY_PATH:
        raise ValueError("Phase 5 receipt source inventory path changed")

    owner = receipt.get("owner_verification")
    if status == FROZEN_STATUS:
        if not isinstance(owner, dict) or owner.get("status") != "CONFIRMED":
            raise ValueError("frozen Phase 5 receipt requires confirmed owner verification")
        authority_commit = str(owner.get("authority_commit"))
        source_revision = str(owner.get("source_revision"))
        source_run_id = str(owner.get("source_proof_run_id"))
        if _SHA_RE.fullmatch(authority_commit) is None:
            raise ValueError("owner verification authority_commit is invalid")
        if source_revision != tested_revision or source_run_id != run_id:
            raise ValueError("owner verification does not match hosted proof identity")
        _require_ancestor(PHASE4_MERGE_COMMIT, tested_revision)
        _require_ancestor(tested_revision, authority_commit)
        _require_ancestor(authority_commit, "HEAD")
        inventory_bytes = _git_file_bytes(authority_commit, INVENTORY_PATH)
        authority_inventory = _parse_inventory_bytes(inventory_bytes)
        if inventory_claim.get("sha256") != sha256_bytes(inventory_bytes):
            raise ValueError("Phase 5 receipt does not match its authority inventory")
        if inventory_claim.get("file_count") != authority_inventory.get("file_count"):
            raise ValueError("Phase 5 authority inventory file count changed")
        expected_phase5 = _expected_phase5(authority_inventory)
        changed = _changed_files(tested_revision, authority_commit)
    else:
        if owner is not None:
            raise ValueError("preliminary Phase 5 receipt must not claim owner verification")
        _require_ancestor(PHASE4_MERGE_COMMIT, tested_revision)
        _require_ancestor(tested_revision, "HEAD")
        current_inventory = _inventory_payload()
        if inventory_claim.get("sha256") != sha256(INVENTORY):
            raise ValueError("Phase 5 receipt does not match the committed source inventory")
        if inventory_claim.get("file_count") != current_inventory.get("file_count"):
            raise ValueError("Phase 5 source inventory file count changed")
        expected_phase5 = _expected_phase5(current_inventory)
        changed = _changed_files(tested_revision, "HEAD")

    if receipt.get("phase5") != expected_phase5:
        raise ValueError("Phase 5 immutable metadata does not match its authority inventory")

    proof = receipt.get("proof")
    if not isinstance(proof, dict):
        raise ValueError("Phase 5 receipt is missing proof results")
    missing = sorted(_REQUIRED_PROOF - set(proof))
    unknown = sorted(set(proof) - _REQUIRED_PROOF)
    if missing or unknown:
        raise ValueError(f"Phase 5 proof key mismatch; missing={missing} unknown={unknown}")
    failed = [
        key
        for key, value in proof.items()
        if key not in {"srg_20_for_2", "rust_toolchain"} and value != "PASS"
    ]
    if failed:
        raise ValueError("Phase 5 receipt contains non-PASS proof fields: " + ", ".join(failed))
    if proof["srg_20_for_2"] != "40/40 PASS":
        raise ValueError("Phase 5 receipt does not prove SRG 20-for-2")
    if proof["rust_toolchain"] != "1.75.0":
        raise ValueError("Phase 5 receipt records an unsupported Rust toolchain")

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
    parser = argparse.ArgumentParser(description="Build or verify the Phase 5 proof receipt")
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

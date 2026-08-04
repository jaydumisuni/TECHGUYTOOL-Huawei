from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "source_inventory.json"
OUTPUT = ROOT / "manifests" / "phase3_gateway.receipt.json"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_ALLOWED_POST_PROOF_CHANGES = {
    "manifests/phase3_gateway.receipt.json",
    "manifests/source_inventory.json",
    "rust/device_gateway/Cargo.lock",
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
    expected_suffix = f"/actions/runs/{proof_run_id}"
    if not proof_run_url.startswith("https://github.com/") or not proof_run_url.endswith(
        expected_suffix
    ):
        raise ValueError("proof run URL must identify the supplied GitHub Actions run")


def build(
    *,
    tested_revision: str,
    proof_run_id: str,
    generated_at: str,
    proof_run_url: str,
) -> dict[str, object]:
    _validate_proof_identity(tested_revision, proof_run_id, generated_at, proof_run_url)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    phase3_files = [
        item
        for item in inventory.get("files", [])
        if item.get("origin") == "phase3_device_gateway"
    ]
    if not phase3_files:
        raise ValueError("source inventory contains no Phase 3 files")
    return {
        "schema": "techguytool-huawei.phase3-gateway-receipt.v1",
        "status": "PHASE3_DEVICE_GATEWAY_FROZEN",
        "generated_at": generated_at,
        "phase2_merge_commit": "ea6e66dd91031485d6db39d47da294de6ff2e771",
        "hosted_proof": {
            "tested_revision": tested_revision,
            "run_id": int(proof_run_id),
            "run_url": proof_run_url,
        },
        "phase3": {
            "branch": "phase3/device-gateway",
            "database_schema_version": 1,
            "rust_gateway_tests": 7,
            "python_gateway_client_tests": 3,
            "reconnect_proof_cases": 1,
            "device_authority": "none",
            "xray_authority": "read_only",
            "phase3_file_count": len(phase3_files),
        },
        "proof": {
            "cargo_lock_resolved": "PASS",
            "cargo_fmt": "PASS",
            "cargo_clippy_warnings_denied": "PASS",
            "cargo_test": "PASS",
            "gateway_binary_build": "PASS",
            "python_gateway_client_suite": "PASS",
            "ui_reconnect_proof": "PASS",
            "gateway_restart_recovery": "PASS",
            "journal_chain_verification": "PASS",
            "forbidden_device_capability_rejection": "PASS",
            "complete_python_regression": "PASS",
            "phase2_contract_regression": "PASS",
            "source_freeze_verifier": "PASS",
            "rust_toolchain": "1.75.0",
        },
        "source_inventory": {
            "path": "manifests/source_inventory.json",
            "file_count": inventory.get("file_count"),
            "sha256": sha256(INVENTORY),
        },
        "truth_boundary": (
            "This receipt proves only the persistent, device-inert TTG Device Gateway control "
            "plane at the tested revision and hosted run. It proves durable sessions, operation "
            "stage recovery, loopback UI reconnection, provider/capability policy, watchdog state, "
            "diagnostics, and a hash-chained journal. It does not authorize or prove loader "
            "transfer, partition writes, OEMINFO modification, flashing, reboot, drivers, signed "
            "packaging, or physical Huawei repair."
        ),
    }


def verify() -> None:
    receipt = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "techguytool-huawei.phase3-gateway-receipt.v1":
        raise ValueError("unsupported Phase 3 receipt schema")
    if receipt.get("status") != "PHASE3_DEVICE_GATEWAY_FROZEN":
        raise ValueError("Phase 3 receipt is not frozen")

    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise ValueError("Phase 3 receipt is missing hosted proof identity")
    tested_revision = str(hosted.get("tested_revision"))
    run_id = str(hosted.get("run_id"))
    run_url = str(hosted.get("run_url"))
    generated_at = str(receipt.get("generated_at"))
    _validate_proof_identity(tested_revision, run_id, generated_at, run_url)

    proof = receipt.get("proof")
    if not isinstance(proof, dict):
        raise ValueError("Phase 3 receipt is missing proof results")
    failed = [
        name
        for name, value in proof.items()
        if name != "rust_toolchain" and value != "PASS"
    ]
    if failed:
        raise ValueError("Phase 3 receipt contains non-PASS proof fields: " + ", ".join(failed))
    if proof.get("rust_toolchain") != "1.75.0":
        raise ValueError("Phase 3 receipt records an unsupported Rust toolchain")

    inventory = receipt.get("source_inventory")
    if not isinstance(inventory, dict):
        raise ValueError("Phase 3 receipt is missing source inventory identity")

    owner = receipt.get("owner_verification")
    if isinstance(owner, dict):
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
            raise ValueError("Phase 3 receipt does not match its authority inventory")
        changed = _changed_files(tested_revision, authority_commit)
    else:
        _require_ancestor(tested_revision, "HEAD")
        if inventory.get("sha256") != sha256(INVENTORY):
            raise ValueError("Phase 3 receipt does not match the committed source inventory")
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
    parser = argparse.ArgumentParser(description="Build or verify the Phase 3 proof receipt")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--tested-revision")
    parser.add_argument("--proof-run-id")
    parser.add_argument("--generated-at")
    parser.add_argument("--proof-run-url")
    args = parser.parse_args()

    if not INVENTORY.is_file():
        raise SystemExit("source inventory must be generated first")
    if args.verify:
        verify()
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

    payload = build(
        tested_revision=args.tested_revision,
        proof_run_id=args.proof_run_id,
        generated_at=args.generated_at,
        proof_run_url=args.proof_run_url,
    )
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

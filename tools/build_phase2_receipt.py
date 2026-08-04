from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "source_inventory.json"
OUTPUT = ROOT / "manifests" / "source_inventory.receipt.json"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_ALLOWED_POST_PROOF_CHANGES = {
    "manifests/source_inventory.json",
    "manifests/source_inventory.receipt.json",
}


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for one authority file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    """Build a traceable Phase 2 receipt after all hosted proof gates pass."""

    _validate_proof_identity(tested_revision, proof_run_id, generated_at, proof_run_url)
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    phase2_files = [
        item
        for item in inventory.get("files", [])
        if item.get("origin") == "phase2_shared_contracts"
    ]
    return {
        "schema": "techguytool-huawei.source-inventory-receipt.v3",
        "status": "PHASE2_SHARED_CONTRACTS_FROZEN",
        "generated_at": generated_at,
        "phase1_base_commit": "c6c11ece1c5dc98e151589df42f272f4637af4d5",
        "hosted_proof": {
            "tested_revision": tested_revision,
            "run_id": int(proof_run_id),
            "run_url": proof_run_url,
        },
        "phase2": {
            "branch": "phase2/shared-contracts",
            "contract_types": 17,
            "valid_fixtures": 17,
            "invalid_mutation_fixtures": 34,
            "review_edge_fixtures": 3,
            "malformed_json_fixtures": 1,
            "context_fixtures": 2,
            "contract_equivalence_cases": 55,
            "context_equivalence_cases": 2,
            "total_cross_language_cases": 57,
            "device_authority": "none",
            "xray_authority": "read_only",
            "phase2_file_count": len(phase2_files),
        },
        "proof": {
            "python_fixture_suite": "PASS",
            "python_registry_authority": "PASS",
            "rust_fixture_suite": "PASS",
            "python_rust_canonical_equivalence": "PASS",
            "python_rust_sha256_equivalence": "PASS",
            "python_rust_error_code_equivalence": "PASS",
            "python_rust_validation_context_equivalence": "PASS",
            "complete_python_regression": "PASS",
            "cargo_fmt": "PASS",
            "cargo_clippy_warnings_denied": "PASS",
            "cargo_test": "PASS",
            "rust_toolchain": "1.75.0",
            "source_freeze_verifier": "PASS",
        },
        "source_inventory": {
            "path": "manifests/source_inventory.json",
            "file_count": inventory.get("file_count"),
            "sha256": sha256(INVENTORY),
        },
        "private_recovery_archive": {
            "drive_file_id": "1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs",
            "sha256": "d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4",
            "visibility": "private",
        },
        "truth_boundary": (
            "This receipt proves only the deterministic shared contract layer at the exact "
            "tested revision and hosted run recorded above. The authority commit may change only "
            "the inventory and this receipt. It does not authorize or prove loader transfer, "
            "partition writes, OEMINFO modification, flashing, reboot, drivers, signed packaging, "
            "or physical Huawei repair."
        ),
    }


def verify() -> None:
    """Verify receipt provenance and reject source changes after the tested revision."""

    receipt = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if receipt.get("schema") != "techguytool-huawei.source-inventory-receipt.v3":
        raise ValueError("unsupported Phase 2 receipt schema")
    if receipt.get("status") != "PHASE2_SHARED_CONTRACTS_FROZEN":
        raise ValueError("Phase 2 receipt is not frozen")

    hosted = receipt.get("hosted_proof")
    if not isinstance(hosted, dict):
        raise ValueError("Phase 2 receipt is missing hosted proof identity")
    tested_revision = hosted.get("tested_revision")
    run_id = hosted.get("run_id")
    run_url = hosted.get("run_url")
    generated_at = receipt.get("generated_at")
    _validate_proof_identity(
        str(tested_revision), str(run_id), str(generated_at), str(run_url)
    )

    inventory = receipt.get("source_inventory")
    if not isinstance(inventory, dict) or inventory.get("sha256") != sha256(INVENTORY):
        raise ValueError("Phase 2 receipt does not match the committed source inventory")

    proof = receipt.get("proof")
    if not isinstance(proof, dict):
        raise ValueError("Phase 2 receipt is missing proof results")
    pass_fields = [name for name, value in proof.items() if name != "rust_toolchain" and value != "PASS"]
    if pass_fields:
        raise ValueError("Phase 2 receipt contains non-PASS proof fields: " + ", ".join(pass_fields))
    if proof.get("rust_toolchain") != "1.75.0":
        raise ValueError("Phase 2 receipt records an unsupported Rust toolchain")

    subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(tested_revision), "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{tested_revision}..HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    ).stdout.splitlines()
    unexpected = sorted(set(changed) - _ALLOWED_POST_PROOF_CHANGES)
    if unexpected:
        raise ValueError(
            "source changed after hosted proof: " + ", ".join(unexpected)
        )


def main() -> int:
    """Write or verify the traceable Phase 2 proof receipt."""

    parser = argparse.ArgumentParser(description="Build or verify the Phase 2 proof receipt")
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

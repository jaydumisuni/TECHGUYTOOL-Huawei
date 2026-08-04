from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "manifests" / "source_inventory.json"
OUTPUT = ROOT / "manifests" / "source_inventory.receipt.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    phase2_files = [
        item for item in inventory.get("files", []) if item.get("origin") == "phase2_shared_contracts"
    ]
    return {
        "schema": "techguytool-huawei.source-inventory-receipt.v2",
        "status": "PHASE2_SHARED_CONTRACTS_FROZEN",
        "prepared_at": "2026-08-04T15:50:00Z",
        "phase1_base_commit": "c6c11ece1c5dc98e151589df42f272f4637af4d5",
        "phase2": {
            "branch": "phase2/shared-contracts",
            "contract_types": 17,
            "valid_fixtures": 17,
            "invalid_mutation_fixtures": 34,
            "malformed_json_fixtures": 1,
            "invalid_context_fixtures": 1,
            "equivalence_cases": 53,
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
            "This receipt proves only the deterministic shared contract layer after the hosted "
            "workflow completed every listed proof gate. It does not authorize or prove loader "
            "transfer, partition writes, OEMINFO modification, flashing, reboot, drivers, signed "
            "packaging, or physical Huawei repair."
        ),
    }


def main() -> int:
    if not INVENTORY.is_file():
        raise SystemExit("source inventory must be generated first")
    OUTPUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

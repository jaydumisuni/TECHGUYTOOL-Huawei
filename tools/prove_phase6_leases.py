from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASE = ROOT / "rust" / "device_gateway" / "src" / "lease.rs"

REQUIRED_CODES = {
    "MODE_MISMATCH",
    "REBOOT_BLOCKED_BY_ACTIVE_MODE_LEASE",
    "STOCK_FASTBOOT_RESTORE_BLOCKED_BY_ACTIVE_MODE_LEASE",
    "MODE_LEASE_ALREADY_RELEASED",
    "PARTITION_NOT_AUTHORIZED",
    "WRITE_RANGE_EXCEEDS_LEASE",
    "RANGE_MANIFEST_MISMATCH",
    "STAGE_MISMATCH",
    "ADAPTER_ID_MISMATCH",
    "ADAPTER_VERSION_MISMATCH",
    "REBOOT_NOT_AUTHORIZED_BY_EXECUTION_LEASE",
    "EXECUTION_LEASE_ALREADY_CONSUMED",
}

FORBIDDEN_EXECUTION_SURFACES = {
    "std::process::Command",
    "Command::new",
    "serialport::",
    "libusb",
    "rusb::",
    "fastboot.exe",
    "adb.exe",
    "flash_partition",
    "erase_partition",
}


def main() -> int:
    text = LEASE.read_text(encoding="utf-8")
    missing = sorted(code for code in REQUIRED_CODES if code not in text)
    forbidden = sorted(token for token in FORBIDDEN_EXECUTION_SURFACES if token in text)
    checks = {
        "required_policy_codes_present": not missing,
        "no_device_execution_surface": not forbidden,
        "persistent_single_use_ledger": "execution_lease_claims" in text,
        "contract_core_validation": "validate_contract" in text and "load_registry" in text,
        "atomic_claim_transaction": ".transaction()?" in text and "transaction.commit()?" in text,
        "mode_release_conditions_enforced": "is_subset" in text,
        "physical_session_bound": "expected_physical_session_id" in text,
        "artifact_hashes_bound": "expected_artifact_hashes" in text,
        "recipe_hash_bound": "expected_recipe_hash" in text,
        "reboot_permission_bound": "request_reboot" in text,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "schema": "techguytool-huawei.phase6-static-authority-proof.v1",
        "status": status,
        "checks": checks,
        "missing_policy_codes": missing,
        "forbidden_execution_surfaces": forbidden,
        "device_authority": "none",
        "execution_authority": "lease_only",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

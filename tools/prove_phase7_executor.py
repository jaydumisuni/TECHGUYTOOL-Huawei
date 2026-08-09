from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = ROOT / "rust" / "device_gateway" / "src" / "executor.rs"

REQUIRED = {
    "execute_authorized",
    "claim_execution",
    "ADAPTER_NOT_REGISTERED",
    "PAYLOAD_HASH_MISMATCH",
    "PAYLOAD_NOT_AUTHORIZED_ARTIFACT",
    "PAYLOAD_SIZE_MISMATCH",
    "MANDATORY_BACKUP_MISSING",
    "MANDATORY_READBACK_MISSING",
    "READBACK_HASH_MISMATCH",
    "ADAPTER_WRITE_COUNT_MISMATCH",
    "EXECUTION_CANCELLED_BEFORE_CLAIM",
    "EXECUTION_CANCELLED_AFTER_CLAIM",
    "EXECUTION_CANCELLED_DURING_ADAPTER",
}

FORBIDDEN = {
    "std::process::Command",
    "Command::new",
    "shell=true",
    "serialport::",
    "rusb::",
    "libusb",
    "fastboot.exe",
    "adb.exe",
}


def main() -> int:
    text = EXECUTOR.read_text(encoding="utf-8")
    missing = sorted(token for token in REQUIRED if token not in text)
    forbidden = sorted(token for token in FORBIDDEN if token in text)
    checks = {
        "lease_claim_owned_by_executor": "self.lease_guard.claim_execution" in text,
        "no_external_permit_parameter": "permit: &ExecutionPermit" not in text and "permit: ExecutionPermit" not in text,
        "adapter_registry_fail_closed": "ADAPTER_NOT_REGISTERED" in text,
        "payload_hash_verified": "sha256_hex(&request.payload)" in text,
        "artifact_authority_verified": "PAYLOAD_NOT_AUTHORIZED_ARTIFACT" in text,
        "payload_size_verified": "PAYLOAD_SIZE_MISMATCH" in text,
        "backup_required_verified": "MANDATORY_BACKUP_MISSING" in text,
        "readback_required_verified": "MANDATORY_READBACK_MISSING" in text,
        "exact_readback_verified": "READBACK_HASH_MISMATCH" in text,
        "adapter_write_count_verified": "ADAPTER_WRITE_COUNT_MISMATCH" in text,
        "cancellation_before_after_during": all(
            code in text
            for code in (
                "EXECUTION_CANCELLED_BEFORE_CLAIM",
                "EXECUTION_CANCELLED_AFTER_CLAIM",
                "EXECUTION_CANCELLED_DURING_ADAPTER",
            )
        ),
        "no_device_transport_surface": not forbidden,
        "required_policy_surface": not missing,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(
        json.dumps(
            {
                "schema": "techguytool-huawei.phase7-executor-proof.v1",
                "status": status,
                "checks": checks,
                "missing": missing,
                "forbidden": forbidden,
                "device_authority": "none",
                "executor_authority": "bounded-framework-only",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

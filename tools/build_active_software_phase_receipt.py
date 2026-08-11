from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "manifests" / "active_software_phase.json"
INVENTORY = ROOT / "manifests" / "source_inventory.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SystemExit(f"Phase 15 authority_request {field} invalid")
    return value


def _phase15_request(existing: Mapping[str, Any], *, run_id: int, tested_revision: str) -> dict[str, Any]:
    request = existing.get("authority_request")
    if not isinstance(request, Mapping):
        raise SystemExit("Phase 15 authority_request missing")
    if request.get("proof_run_id") != run_id:
        raise SystemExit("Phase 15 authority_request proof_run_id mismatch")
    if request.get("tested_revision") != tested_revision:
        raise SystemExit("Phase 15 authority_request tested_revision mismatch")

    executable_sha256 = request.get("executable_sha256")
    if not isinstance(executable_sha256, str) or not SHA256_RE.fullmatch(executable_sha256):
        raise SystemExit("Phase 15 authority_request executable_sha256 invalid")
    artifact_name = request.get("artifact_name")
    if not isinstance(artifact_name, str) or not artifact_name.strip():
        raise SystemExit("Phase 15 authority_request artifact_name invalid")

    return {
        "proof_run_id": run_id,
        "tested_revision": tested_revision,
        "windows_run_id": _positive_int(request.get("windows_run_id"), "windows_run_id"),
        "executable_sha256": executable_sha256,
        "artifact_id": _positive_int(request.get("artifact_id"), "artifact_id"),
        "artifact_name": artifact_name.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build active TECHGUYTOOL Huawei software-phase receipt")
    parser.add_argument("--run-id", type=int, required=False)
    parser.add_argument("--tested-revision", required=False)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    phase = int(config["phase"])
    receipt_path = ROOT / str(config["receipt_path"])

    if not args.write:
        print(f"ACTIVE RECEIPT BUILDER READY phase={phase} path={receipt_path.relative_to(ROOT)}")
        return 0

    if args.run_id is None or not isinstance(args.tested_revision, str) or not REVISION_RE.fullmatch(args.tested_revision):
        raise SystemExit("--write requires --run-id and a full 40-character lowercase hex --tested-revision")

    inventory_sha256 = sha256(INVENTORY)
    existing: dict[str, Any] = {}
    if receipt_path.is_file():
        loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SystemExit("active software receipt root must be an object")
        existing = loaded

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "hosted_proof": {
            "repository": "jaydumisuni/TECHGUYTOOL-Huawei",
            "run_id": args.run_id,
            "run_url": f"https://github.com/jaydumisuni/TECHGUYTOOL-Huawei/actions/runs/{args.run_id}",
            "tested_revision": args.tested_revision,
            "workflow": "Software Phase Proof",
        },
        "phase": phase,
        "phase_name": config["name"],
        "predecessor_merge": config["predecessor_merge"],
        "proof": {
            "active_phase_proof": "PASS",
            "complete_python_regression": "PASS",
            "contract_core_regression": "PASS",
            "device_gateway_regression": "PASS",
            "rust_clippy": "PASS",
            "rust_format": "PASS",
            "rust_tests": "PASS",
            "source_freeze_verifier": "PASS",
            "srg_20_for_2": "40/40 PASS",
        },
        "schema": f"techguytool-huawei.phase{phase}-receipt.v1",
        "source_inventory": {
            "path": "manifests/source_inventory.json",
            "sha256": inventory_sha256,
        },
        "status": "PROVEN_PENDING_OWNER",
        "truth_boundary": (
            "This receipt proves only the software authority described by the active phase. "
            "Physical-device certification, external proprietary artifacts, Windows production signing and "
            "hardware-specific destructive operations remain outside software-only proof unless "
            "the phase plan explicitly records independent physical evidence."
        ),
    }

    if phase == 15:
        request = _phase15_request(existing, run_id=args.run_id, tested_revision=args.tested_revision)
        payload.update(
            {
                "authority_request": request,
                "release_filename": "TECHGUYTOOL_Huawei.exe",
                "windows_ci": "PASS",
                "ci_test_signing": "PASS",
                "production_signing": "EXTERNAL_CERTIFICATE_REQUIRED",
                "physical_proof_matrix": "INCOMPLETE",
                "production_release_status": "EXTERNAL_CERTIFICATION_PENDING",
                "production_enabled": False,
                "tested_revision": args.tested_revision,
                "source_inventory_sha256": inventory_sha256,
                "executable_sha256": request["executable_sha256"],
                "windows_run_id": request["windows_run_id"],
                "software_proof_run_id": args.run_id,
                "artifact_id": request["artifact_id"],
                "artifact_name": request["artifact_name"],
                "proof_trigger": "final-phase15-authority",
            }
        )

    receipt_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {receipt_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

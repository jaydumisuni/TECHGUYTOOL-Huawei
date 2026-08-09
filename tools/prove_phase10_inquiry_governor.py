from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.inquiry_governor import (  # noqa: E402
    REGISTERED_READ_ONLY_PROBES,
    evaluate_inquiry,
)

SESSION = "11111111-1111-4111-8111-111111111111"
PREDICTION_ID = "22222222-2222-4222-8222-222222222222"
EXECUTOR_ID = "33333333-3333-4333-8333-333333333333"
VERIFICATION_ID = "44444444-4444-4444-8444-444444444444"
LEASE_ID = "55555555-5555-4555-8555-555555555555"
NOW = "2032-01-20T00:30:00Z"


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def executor() -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_type": "executor_result",
        "contract_id": EXECUTOR_ID,
        "producer": "bounded.executor",
        "created_at": NOW,
        "physical_session_id": SESSION,
        "evidence_hashes": [h("executor")],
        "confidence_bps": 10000,
        "expires_at": None,
        "authority": "execution",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "lease_id": LEASE_ID,
            "stage_id": "restore_oeminfo_identity",
            "outcome": "accepted",
            "raw_result_sha256": h("raw"),
            "readback_sha256": h("readback"),
            "bytes_written": 4096,
        },
    }


def verification() -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_type": "verification_result",
        "contract_id": VERIFICATION_ID,
        "producer": "xray.verifier",
        "created_at": NOW,
        "physical_session_id": SESSION,
        "evidence_hashes": [h("verification")],
        "confidence_bps": 10000,
        "expires_at": None,
        "authority": "verification",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "subject_contract_id": EXECUTOR_ID,
            "verdict": "verified",
            "verification_code": "VERIFY_READBACK_301_HASH_MATCH",
            "readback_match": True,
            "observed_at": NOW,
        },
    }


def main() -> int:
    registry = json.loads((ROOT / "manifests" / "inquiry_probe_registry.json").read_text(encoding="utf-8"))
    if registry["probes"] != REGISTERED_READ_ONLY_PROBES:
        raise SystemExit("Inquiry probe registry and implementation differ")
    if any(spec["write_allowed"] is not False for spec in registry["probes"].values()):
        raise SystemExit("Inquiry probe registry expanded write authority")

    prediction = {
        "stage_id": "restore_oeminfo_identity",
        "expected_subjects": {"vog-l29-main-version": "observed"},
        "required_executor_outcome": "accepted",
        "require_readback_match": True,
    }
    gap = evaluate_inquiry(
        physical_session_id=SESSION,
        prediction_contract_id=PREDICTION_ID,
        prediction=prediction,
        executor_result=executor(),
        verification_result=verification(),
        post_evidence={"vog-l29-main-version": "missing"},
        created_at=NOW,
        source_evidence_hashes=[h("p30-replay-evidence")],
    )
    if gap.governor_status != "KNOWLEDGE_GAP":
        raise SystemExit("accepted/readback-matched but unmet P30 prediction did not create a gap")
    if gap.knowledge_gap_contract["payload"]["gap_code"] != "EXPECTED_RESULT_NOT_OBSERVED":
        raise SystemExit("P30-style inquiry gap code mismatch")
    if gap.learning_proposal_contract["payload"]["status"] != "quarantined":
        raise SystemExit("learning candidate bypassed quarantine")
    if gap.learning_proposal_contract["payload"]["auto_promotion_allowed"] is not False:
        raise SystemExit("Inquiry allowed automatic promotion")
    if gap.to_dict()["generic_retry_allowed"] is not False:
        raise SystemExit("Inquiry permitted a generic retry")

    verified = evaluate_inquiry(
        physical_session_id=SESSION,
        prediction_contract_id=PREDICTION_ID,
        prediction=prediction,
        executor_result=executor(),
        verification_result=verification(),
        post_evidence={"vog-l29-main-version": "observed"},
        created_at=NOW,
        source_evidence_hashes=[h("p30-replay-evidence")],
    )
    if verified.governor_status != "VERIFIED" or verified.knowledge_gap_contract is not None:
        raise SystemExit("verified outcome generated a false knowledge gap")

    print(
        json.dumps(
            {
                "schema": "techguytool-huawei.phase10-proof.v1",
                "status": "PASS",
                "p30_unexplained_outcome": "STRUCTURED_GAP",
                "generic_retry": "FORBIDDEN",
                "probe_authority": "REGISTERED_READ_ONLY_ONLY",
                "learning_candidate": "QUARANTINED",
                "auto_promotion": False,
                "execution_authority": "none",
                "device_authority": "none",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

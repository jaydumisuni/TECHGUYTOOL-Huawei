from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.knowledge_workshop import (  # noqa: E402
    DANGEROUS_CHANGE_KINDS,
    READ_ONLY_CHANGE_KINDS,
    admit_learning_proposal,
    promotion_candidate,
    record_canary,
    record_hardware_support,
    record_replay_support,
    specialist_approve,
)

NOW = "2032-01-20T00:30:00Z"


def h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def proposal(kind: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_type": "learning_proposal",
        "contract_id": "33333333-3333-4333-8333-333333333333",
        "producer": "inquiry.governor",
        "created_at": NOW,
        "physical_session_id": None,
        "evidence_hashes": [h("gap")],
        "confidence_bps": None,
        "expires_at": None,
        "authority": "learning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "proposal_id": "22222222-2222-4222-8222-222222222222",
            "gap_id": "11111111-1111-4111-8111-111111111111",
            "change_kind": kind,
            "auto_promotion_allowed": kind == "read_only_parser",
            "replay_fixture_hashes": [h("origin")],
            "status": "quarantined",
        },
    }


def replay(record):
    return record_replay_support(
        record,
        replay_fixture_hashes=[h("origin"), h("challenge-replay")],
        regression_sha256=h("regression"),
        challenge_sha256=h("challenge"),
    )


def main() -> int:
    policy = json.loads((ROOT / "manifests" / "knowledge_workshop_policy.json").read_text(encoding="utf-8"))
    if set(policy["read_only_change_kinds"]) != READ_ONLY_CHANGE_KINDS:
        raise SystemExit("workshop policy read-only change set drift")
    if set(policy["dangerous_change_kinds"]) != DANGEROUS_CHANGE_KINDS:
        raise SystemExit("workshop policy dangerous change set drift")
    if policy["execution_authority"] != "none" or policy["device_authority"] != "none":
        raise SystemExit("workshop policy expanded execution/device authority")

    parser = replay(admit_learning_proposal(proposal("read_only_parser"), now=NOW))
    parser_approved = specialist_approve(parser, approval_sha256=h("parser-approval"))
    candidate = promotion_candidate(parser_approved)
    if candidate["includes_execution"] is not False or candidate["device_authority"] != "none":
        raise SystemExit("read-only parser promotion candidate expanded authority")

    rule = replay(admit_learning_proposal(proposal("diagnostic_rule"), now=NOW))
    rule = record_canary(rule, canary_sha256=h("canary"))
    rule = record_hardware_support(rule, hardware_proof_sha256=h("external-hardware-proof-placeholder-for-validator"))
    rule = specialist_approve(rule, approval_sha256=h("specialist-approval"))
    if rule.status != "specialist_approved":
        raise SystemExit("diagnostic rule lifecycle failed")

    for dangerous in sorted(DANGEROUS_CHANGE_KINDS):
        record = admit_learning_proposal(proposal(dangerous), now=NOW)
        try:
            replay(record)
        except Exception:
            pass
        else:
            raise SystemExit(f"dangerous proposal escaped quarantine: {dangerous}")

    print(
        json.dumps(
            {
                "schema": "techguytool-huawei.phase11-proof.v1",
                "status": "PASS",
                "read_only_learning": "LIFECYCLE_ENFORCED",
                "dangerous_changes": "QUARANTINED",
                "automatic_write_authority": "FORBIDDEN",
                "hardware_proof": "EXTERNAL_EVIDENCE_REQUIRED_FOR_REAL_CERTIFICATION",
                "phase13_promotion": "SEPARATE",
                "execution_authority": "none",
                "device_authority": "none",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

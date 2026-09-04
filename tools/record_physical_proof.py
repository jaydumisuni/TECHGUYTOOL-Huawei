from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.physical_evidence import (  # noqa: E402
    PhysicalEvidenceError,
    build_physical_evidence_packet,
    validate_physical_evidence_packet,
    validate_proof_output_path,
)


def _load_subject(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PhysicalEvidenceError(f"Subject JSON is invalid: {exc}") from exc
    if not isinstance(value, dict) or not value:
        raise PhysicalEvidenceError("Subject JSON must contain a non-empty object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a hashed, reviewable physical-certification evidence packet without "
            "modifying the Phase 15 physical proof matrix."
        )
    )
    parser.add_argument("--entry-id", required=True)
    parser.add_argument("--subject-json", required=True, type=Path)
    parser.add_argument("--evidence-file", action="append", required=True, type=Path)
    parser.add_argument("--evidence-ref", action="append", required=True)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--verified-at", default=None)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        packet = build_physical_evidence_packet(
            entry_id=args.entry_id,
            subject=_load_subject(args.subject_json),
            evidence_files=args.evidence_file,
            evidence_refs=args.evidence_ref,
            verifier=args.verifier,
            verified_at=args.verified_at,
        )
        validate_physical_evidence_packet(packet)
        output = validate_proof_output_path(args.output, ROOT / "proof")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PhysicalEvidenceError) as exc:
        print(f"PHYSICAL_EVIDENCE_ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "status": "EVIDENCE_PACKET_READY",
                "entry_id": packet["entry_id"],
                "evidence_id": packet["evidence"]["evidence_id"],
                "evidence_sha256": packet["evidence"]["evidence_sha256"],
                "subject_identity_hash": packet["evidence"]["subject_identity_hash"],
                "output": str(output),
                "matrix_mutated": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

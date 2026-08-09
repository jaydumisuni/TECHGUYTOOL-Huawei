from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.service_lanes import prove_reference_pairs  # noqa: E402


def main() -> int:
    proof = prove_reference_pairs()
    print(json.dumps(proof, sort_keys=True))
    if proof["status"] != "PASS":
        raise SystemExit("Phase 14 proof failed")
    if proof["proof_level"] != "replay_supported":
        raise SystemExit("Phase 14 proof level drift")
    if proof["hardware_certification"] != "HARDWARE_PENDING":
        raise SystemExit("Phase 14 hardware status overstated")
    if proof["bounded_write_proof"] != "DEFERRED":
        raise SystemExit("Phase 14 bounded-write boundary drift")
    if proof["production_enabled"] is not False:
        raise SystemExit("Phase 14 production authority forbidden")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

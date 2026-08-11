from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.windows_release import validate_windows_release_sources  # noqa: E402


def main() -> int:
    result = validate_windows_release_sources()
    print(json.dumps(result, sort_keys=True))
    if result["status"] not in {"SOURCES_ONLY_PENDING_CI", "CI_PROVEN"}:
        raise SystemExit("Phase 15 software release source proof failed")
    if result["packaging"] != "ONEFILE_READY":
        raise SystemExit("Phase 15 one-file packaging boundary failed")
    if result["physical_matrix"] != "INCOMPLETE":
        raise SystemExit("Phase 15 current physical proof matrix was overstated")
    if result["production_release_status"] != "EXTERNAL_CERTIFICATION_PENDING":
        raise SystemExit("Phase 15 production status was overstated")
    if result["production_enabled"] is not False:
        raise SystemExit("Phase 15 production may not be enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

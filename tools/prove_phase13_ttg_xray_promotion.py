from __future__ import annotations

import json

from techguy_huawei.ttg_xray_promotion import promotion_summary


def main() -> int:
    summary = promotion_summary()
    print(json.dumps(summary, sort_keys=True))
    if summary["status"] != "PASS":
        raise SystemExit("Phase 13 promotion proof failed")
    if summary["independently_explains_frozen_vog_case"] is not True:
        raise SystemExit("Phase 13 exit gate failed")
    if summary["execution_authority"] != "none" or summary["device_authority"] != "none":
        raise SystemExit("Phase 13 authority boundary failed")
    if summary["write_allowed"] is not False:
        raise SystemExit("Phase 13 write boundary failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

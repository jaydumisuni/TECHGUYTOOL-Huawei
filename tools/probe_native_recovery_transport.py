from __future__ import annotations
import json
from techguy_huawei.native_recovery_transport import load_transport_replay

def main()->int:
    replay=load_transport_replay()
    print(json.dumps({
        "transport_id":replay["transport_id"],
        "family":replay["family"],
        "evidence_level":replay["evidence_level"],
        "write_certified":replay["write_certified"],
        "blockers":replay["blockers"],
        "runtime_dependency":replay["research_artifact"]["runtime_dependency"],
    },sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

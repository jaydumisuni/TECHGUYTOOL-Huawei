from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.capability_packs import build_capability_contract, load_kirin_capability_set  # noqa: E402


def main() -> int:
    loaded = load_kirin_capability_set()
    contract = build_capability_contract(loaded, created_at="2032-01-20T00:30:00Z")
    if loaded.manifest["includes_execution"] is not False:
        raise SystemExit("Kirin capability set includes execution")
    if contract["payload"]["includes_execution"] is not False:
        raise SystemExit("Phase 2 capability contract includes execution")
    if loaded.manifest["maturity"] != "replay_supported":
        raise SystemExit("Kirin pack maturity exceeds frozen evidence")
    if set(loaded.provider_ids()) != set(loaded.capability_ids):
        raise SystemExit("provider IDs and advertised capability IDs differ")
    required_rules = {
        "vog.main_version_state.oeminfo",
        "vog.service_mode.preserve_until_verified",
        "vog.stock_fastboot.finalization_only",
        "vog.branding.separate_stage",
        "super.chunking.derive_from_artifact",
    }
    knowledge = {item["id"] for item in loaded.components["kirin-xray-knowledge-pack"]["rules"]}
    if not required_rules.issubset(knowledge):
        raise SystemExit("Kirin knowledge pack lost a frozen VOG/P10 theorem rule")
    replay_ids = {item["scenario_id"] for item in loaded.components["kirin-xray-replay-pack"]["fixtures"]}
    if replay_ids != {"kirin-p10-golden-workflow-v1", "kirin-p30-main-version-mode-hazard-v1"}:
        raise SystemExit("Kirin replay pack drift")
    source = (ROOT / "techguy_huawei" / "capability_packs.py").read_text(encoding="utf-8").lower()
    if "subprocess" in source or "import executor" in source or "from .executor" in source:
        raise SystemExit("Kirin capability consumer gained executor/process authority")
    print(
        json.dumps(
            {
                "schema": "techguytool-huawei.phase12-proof.v1",
                "status": "PASS",
                "pack_version": loaded.manifest["pack_version"],
                "maturity": loaded.manifest["maturity"],
                "component_count": len(loaded.components),
                "capability_count": len(loaded.capability_ids),
                "component_hashes": "VERIFIED",
                "replay_references": "VERIFIED",
                "includes_execution": False,
                "device_authority": "none",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

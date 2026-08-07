from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.decision_corps import evaluate_replay_decision
from techguy_huawei.kirin_xray import load_replay

P10 = ROOT / "replay" / "kirin" / "p10_golden_workflow.json"
P30 = ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json"
RECIPE_HASH = "b" * 64


def prove() -> dict[str, Any]:
    """Derive the Phase 5 exit-gate proof from frozen P10/P30 replay evidence."""

    restore = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="restore_stock_fastboot",
        recipe_hash=RECIPE_HASH,
    )
    by_officer = {decision.officer_id: decision for decision in restore.officer_decisions}
    exit_gate = (
        restore.governor_decision.verdict == "block"
        and restore.governor_decision.veto is True
        and by_officer["safety.challenger"].verdict == "block"
        and by_officer["safety.challenger"].veto is True
        and by_officer["safety.challenger"].reason_code
        == "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED"
    )
    if not exit_gate:
        raise AssertionError("Phase 5 exit gate did not block premature stock-Fastboot restoration")

    reboot = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="reboot",
        recipe_hash=RECIPE_HASH,
    )
    if reboot.governor_decision.verdict != "block":
        raise AssertionError("P30 reboot hazard was not blocked")

    repair = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    if repair.governor_decision.verdict != "allow_stage":
        raise AssertionError("P30 main-version repair stage was not selected")

    p10_final = evaluate_replay_decision(
        P10,
        operation="repair_oeminfo",
        requested_action="finalize",
        recipe_hash=RECIPE_HASH,
    )
    if p10_final.governor_decision.verdict != "block":
        raise AssertionError("P10 service environment finalization was not blocked")

    replay = load_replay(P30)
    unauthorized = copy.deepcopy(replay)
    service = next(
        item for item in unauthorized["endpoints"] if item["transport"] == "huawei_usb_com_1_0"
    )
    service["observed_state"] = "unauthorized"
    unauthorized_report = evaluate_replay_decision(
        unauthorized,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    if unauthorized_report.governor_decision.verdict != "need_technician":
        raise AssertionError("unauthorized service endpoint was promoted into route authority")

    repeated = evaluate_replay_decision(
        P30,
        operation="repair_main_version",
        requested_action="perform_operation",
        recipe_hash=RECIPE_HASH,
    )
    if repair.sha256 != repeated.sha256 or repair.canonical != repeated.canonical:
        raise AssertionError("Decision Corps replay is not deterministic")

    authority = repair.to_dict()
    if authority.get("device_authority") != "none":
        raise AssertionError("Decision Corps expanded device authority")
    if authority.get("execution_authority") != "none":
        raise AssertionError("Decision Corps expanded execution authority")
    if authority.get("decision_authority") != "governance_only":
        raise AssertionError("Decision Corps governance boundary changed")

    return {
        "schema": "techguytool-huawei.phase5-decision-corps-proof.v1",
        "status": "PASS",
        "p30_premature_stock_fastboot_blocked": exit_gate,
        "p30_reboot_blocked": True,
        "p30_repair_stage_selected": True,
        "p10_premature_finalization_blocked": True,
        "unauthorized_service_endpoint_rejected": True,
        "deterministic_replay": True,
        "decision_report_sha256": repair.sha256,
        "veto_officer_count": sum(1 for decision in restore.officer_decisions if decision.veto),
        "decision_authority": "governance_only",
        "execution_authority": "none",
        "device_authority": "none",
    }


def main() -> int:
    """Print the derived Phase 5 proof document."""

    print(json.dumps(prove(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

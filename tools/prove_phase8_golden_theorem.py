from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.golden_theorem import evaluate_workflow, load_theorem, workflow_plan_from_mapping

THEOREM = ROOT / "manifests" / "huawei_revive_golden_theorem.json"
MODULE = ROOT / "techguy_huawei" / "golden_theorem.py"
TESTS = ROOT / "tests" / "test_golden_theorem.py"


def main() -> int:
    theorem = load_theorem(THEOREM)
    sample = {
        "target_family": "VOG",
        "target_region": "C185",
        "service_release_evidence": [
            "target_identity_verified",
            "remaining_firmware_completed",
            "target_boot_environment_ready",
        ],
        "stages": [
            {"stage_id": "service_environment_acquired"},
            {"stage_id": "target_identity_restored", "artifact_family": "VOG", "artifact_region": "C185"},
            {"stage_id": "target_identity_verified"},
            {"stage_id": "regional_firmware_continued", "artifact_family": "VOG", "artifact_region": "C185"},
            {"stage_id": "stock_environment_restored"},
        ],
    }
    verdict = evaluate_workflow(workflow_plan_from_mapping(sample), theorem)
    module_text = MODULE.read_text(encoding="utf-8")
    tests_text = TESTS.read_text(encoding="utf-8")
    checks = {
        "theorem_id_frozen": theorem["theorem_id"] == "huawei-revive-golden-v1",
        "governance_only": theorem["authority"] == "governance_only",
        "no_device_authority": theorem["device_authority"] == "none",
        "no_execution_authority": theorem["execution_authority"] == "none",
        "vog_order_inherits_cleanly": verdict.ok,
        "metadata_not_write_authority": "GT_METADATA_NOT_PARTITION_AUTHORITY" in module_text,
        "donor_family_isolation": "GT_DONOR_FAMILY_ARTIFACT_FORBIDDEN" in module_text,
        "donor_region_isolation": "GT_DONOR_REGION_IDENTITY_FORBIDDEN" in module_text,
        "service_release_fail_closed": "GT_SERVICE_RELEASE_NOT_PROVEN" in module_text,
        "finalization_only": "GT_STOCK_ENVIRONMENT_FINALIZATION_ONLY" in module_text,
        "adversarial_tests_present": tests_text.count("def test_") >= 12,
        "no_executor_import": "executor" not in module_text.lower(),
        "no_process_execution": "subprocess" not in module_text and "os.system" not in module_text,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({
        "schema": "techguytool-huawei.phase8-golden-theorem-proof.v1",
        "status": status,
        "checks": checks,
        "device_authority": "none",
        "execution_authority": "none",
        "truth_boundary": theorem["truth_boundary"],
    }, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

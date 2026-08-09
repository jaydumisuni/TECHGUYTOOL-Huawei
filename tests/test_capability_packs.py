from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from techguy_huawei.capability_packs import (
    CapabilityPackError,
    build_capability_contract,
    load_kirin_capability_set,
    validate_component,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "packs" / "kirin" / "manifest.json"


def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_pack_loads_with_exact_component_hashes():
    loaded = load_kirin_capability_set()
    assert loaded.manifest["includes_execution"] is False
    assert loaded.manifest["maturity"] == "replay_supported"
    assert set(loaded.provider_ids()) == set(loaded.capability_ids)


def test_phase2_capability_contract_is_valid_and_execution_free():
    loaded = load_kirin_capability_set()
    contract = build_capability_contract(loaded, created_at="2032-01-20T00:30:00Z")
    assert contract["payload"]["includes_execution"] is False
    assert contract["payload"]["maturity"] == "replay_supported"
    assert contract["physical_session_id"] is None


def test_component_set_is_exactly_five_sorted_unique():
    value = manifest()
    ids = [item["id"] for item in value["components"]]
    assert len(ids) == 5
    assert ids == sorted(set(ids))


def test_manifest_rejects_execution_authority():
    value = manifest()
    value["includes_execution"] = True
    with pytest.raises(CapabilityPackError, match="EXECUTION_CAPABILITY_FORBIDDEN"):
        validate_manifest(value)


def test_provider_component_rejects_write_allowed():
    loaded = load_kirin_capability_set()
    provider = copy.deepcopy(loaded.components["kirin-xray-provider-pack"])
    provider["providers"][0]["write_allowed"] = True
    with pytest.raises(CapabilityPackError, match="PROVIDER_AUTHORITY_INVALID"):
        validate_component("kirin-xray-provider-pack", provider)


def test_component_rejects_execution_token():
    loaded = load_kirin_capability_set()
    component = copy.deepcopy(loaded.components["kirin-xray-knowledge-pack"])
    component["rules"].append({"id": "bad", "statement": "partition_write", "evidence_level": "replay_supported"})
    with pytest.raises(CapabilityPackError, match="EXECUTION_TOKEN_FORBIDDEN"):
        validate_component("kirin-xray-knowledge-pack", component)


def test_replay_pack_points_only_to_existing_frozen_scenarios():
    loaded = load_kirin_capability_set()
    replay = loaded.components["kirin-xray-replay-pack"]
    paths = {item["path"] for item in replay["fixtures"]}
    assert paths == {
        "replay/kirin/p10_golden_workflow.json",
        "replay/kirin/p30_main_version_mode_hazard.json",
    }


def test_knowledge_pack_preserves_vog_main_version_and_service_hazards():
    loaded = load_kirin_capability_set()
    ids = {rule["id"] for rule in loaded.components["kirin-xray-knowledge-pack"]["rules"]}
    assert "vog.main_version_state.oeminfo" in ids
    assert "vog.service_mode.preserve_until_verified" in ids
    assert "vog.stock_fastboot.finalization_only" in ids


def test_error_pack_contains_diagnosis_and_verification_separately():
    loaded = load_kirin_capability_set()
    errors = loaded.components["kirin-xray-error-pack"]["errors"]
    by_code = {item["code"]: item for item in errors}
    assert by_code["XR-HUA-VERSION-001"]["authority"] == "diagnosis"
    assert by_code["VERIFY-VERSION-302"]["authority"] == "verification"


def test_consumer_module_does_not_import_executor_or_loader_modules():
    source = (ROOT / "techguy_huawei" / "capability_packs.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "from .executor" not in lowered
    assert "import executor" not in lowered
    assert "loader_transfer" in lowered  # only a forbidden-token declaration
    assert "subprocess" not in lowered


def test_manifest_path_escape_fails_closed():
    value = manifest()
    value["components"][0]["path"] = "../executor.py"
    with pytest.raises(CapabilityPackError, match="CAPABILITY_COMPONENT_PATH_INVALID"):
        validate_manifest(value)


def test_pack_is_deterministic():
    first = load_kirin_capability_set()
    second = load_kirin_capability_set()
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.capability_ids == second.capability_ids

from __future__ import annotations

import copy

import pytest

from techguy_huawei.service_lanes import (
    ServiceLaneError,
    evaluate_service_replay,
    load_service_lane_manifest,
    prove_reference_pairs,
    validate_service_lane_manifest,
)


def qcom_replay() -> dict:
    import json
    from pathlib import Path

    return json.loads(
        Path("replay/service/qualcomm_9008_gpt_readonly.json").read_text(encoding="utf-8")
    )


def mtk_replay() -> dict:
    import json
    from pathlib import Path

    return json.loads(
        Path("replay/service/mtk_brom_partition_readonly.json").read_text(encoding="utf-8")
    )


def test_phase14_reference_pairs_pass_at_replay_level_only() -> None:
    proof = prove_reference_pairs()
    assert proof["status"] == "PASS"
    assert proof["proof_level"] == "replay_supported"
    assert proof["hardware_certification"] == "HARDWARE_PENDING"
    assert proof["bounded_write_proof"] == "DEFERRED"
    assert proof["production_enabled"] is False
    assert proof["device_modification"] == "OUT_OF_SCOPE"
    assert len(proof["model_operation_pairs"]) == 2
    for item in proof["model_operation_pairs"]:
        assert item["transport_verified"] is True
        assert item["protocol_verified"] is True
        assert item["artifact_identity_verified"] is True
        assert item["read_only_inventory_verified"] is True
        assert item["write_authority"] == "none"


def test_qcom_requires_exact_9008_transport() -> None:
    replay = qcom_replay()
    replay["transport"]["usb_pid"] = "900E"
    with pytest.raises(ServiceLaneError, match="QCOM_REPLAY_TRANSPORT_MISMATCH"):
        evaluate_service_replay(replay)


def test_qcom_requires_sahara_observation() -> None:
    replay = qcom_replay()
    replay["protocol_observation"]["state"] = "UNKNOWN"
    with pytest.raises(ServiceLaneError, match="QCOM_REPLAY_SAHARA_MISMATCH"):
        evaluate_service_replay(replay)


def test_qcom_rejects_artifact_hash_drift() -> None:
    replay = qcom_replay()
    replay["artifact_identity"]["sha256"] = "0" * 64
    with pytest.raises(ServiceLaneError, match="SERVICE_ARTIFACT_HASH_MISMATCH"):
        evaluate_service_replay(replay)


def test_qcom_rejects_device_use_claim() -> None:
    replay = qcom_replay()
    replay["artifact_identity"]["device_used"] = True
    with pytest.raises(ServiceLaneError, match="SERVICE_ARTIFACT_DEVICE_USE_FORBIDDEN"):
        evaluate_service_replay(replay)


def test_qcom_requires_nonempty_valid_gpt_inventory() -> None:
    replay = qcom_replay()
    replay["gpt_inventory"] = []
    with pytest.raises(ServiceLaneError, match="QCOM_GPT_INVENTORY_INVALID"):
        evaluate_service_replay(replay)


def test_mtk_requires_exact_transport_fixture() -> None:
    replay = mtk_replay()
    replay["transport"]["usb_vid"] = "FFFF"
    with pytest.raises(ServiceLaneError, match="MTK_REPLAY_TRANSPORT_MISMATCH"):
        evaluate_service_replay(replay)


def test_mtk_requires_known_security_state() -> None:
    replay = mtk_replay()
    replay["protocol_observation"]["security_state"] = "UNBOUNDED"
    with pytest.raises(ServiceLaneError, match="MTK_REPLAY_SECURITY_STATE_INVALID"):
        evaluate_service_replay(replay)


def test_mtk_rejects_artifact_hash_drift() -> None:
    replay = mtk_replay()
    replay["artifact_identity"]["sha256"] = "f" * 64
    with pytest.raises(ServiceLaneError, match="SERVICE_ARTIFACT_HASH_MISMATCH"):
        evaluate_service_replay(replay)


def test_mtk_requires_nonempty_valid_partition_inventory() -> None:
    replay = mtk_replay()
    replay["partition_inventory"] = [{"name": "boot_a", "first_lba": 10, "last_lba": 5}]
    with pytest.raises(ServiceLaneError, match="MTK_PARTITION_INVENTORY_INVALID"):
        evaluate_service_replay(replay)


def test_manifest_rejects_production_enablement() -> None:
    manifest = copy.deepcopy(load_service_lane_manifest())
    manifest["production_enabled"] = True
    with pytest.raises(ServiceLaneError, match="SERVICE_LANE_PRODUCTION_FORBIDDEN"):
        validate_service_lane_manifest(manifest)


def test_manifest_rejects_hardware_overclaim() -> None:
    manifest = copy.deepcopy(load_service_lane_manifest())
    manifest["lanes"][0]["hardware_certification"] = "CERTIFIED"
    with pytest.raises(ServiceLaneError, match="SERVICE_LANE_HARDWARE_OVERSTATED"):
        validate_service_lane_manifest(manifest)


def test_manifest_rejects_artifact_device_use_authority() -> None:
    manifest = copy.deepcopy(load_service_lane_manifest())
    manifest["lanes"][1]["artifact_identity"]["device_use_allowed"] = True
    with pytest.raises(ServiceLaneError, match="SERVICE_ARTIFACT_DEVICE_USE_FORBIDDEN"):
        validate_service_lane_manifest(manifest)

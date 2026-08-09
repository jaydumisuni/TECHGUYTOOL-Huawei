from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifests" / "phase14_service_lanes.json"
REPLAY_ROOT = ROOT / "replay" / "service"
MANIFEST_SCHEMA = "techguytool-huawei.phase14-service-lanes.v1"
REPLAY_SCHEMA = "techguytool-huawei.phase14-service-replay.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ServiceLaneError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class ServiceLaneResult:
    profile_id: str
    operation_id: str
    proof_level: str
    hardware_certification: str
    transport_verified: bool
    protocol_verified: bool
    artifact_identity_verified: bool
    read_only_inventory_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "operation_id": self.operation_id,
            "proof_level": self.proof_level,
            "hardware_certification": self.hardware_certification,
            "transport_verified": self.transport_verified,
            "protocol_verified": self.protocol_verified,
            "artifact_identity_verified": self.artifact_identity_verified,
            "read_only_inventory_verified": self.read_only_inventory_verified,
            "production_enabled": False,
            "device_modification": "OUT_OF_SCOPE",
            "write_authority": "none",
        }


def load_service_lane_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    payload = _load_json(path, "SERVICE_LANE_MANIFEST_INVALID")
    validate_service_lane_manifest(payload)
    return payload


def validate_service_lane_manifest(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != MANIFEST_SCHEMA:
        raise ServiceLaneError("SERVICE_LANE_SCHEMA_MISMATCH", repr(payload.get("schema")))
    if payload.get("production_enabled") is not False:
        raise ServiceLaneError("SERVICE_LANE_PRODUCTION_FORBIDDEN", "Phase 14 is not production authority")
    if payload.get("device_modification") != "OUT_OF_SCOPE":
        raise ServiceLaneError("SERVICE_LANE_SCOPE_EXPANDED", "device modification must remain out of scope")

    lanes = payload.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != 2:
        raise ServiceLaneError("SERVICE_LANE_SET_INVALID", "exactly Qualcomm and MediaTek reference lanes required")
    ids: set[str] = set()
    families: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, Mapping):
            raise ServiceLaneError("SERVICE_LANE_INVALID", "lane must be an object")
        profile_id = _required_text(lane, "profile_id", "SERVICE_LANE_PROFILE_INVALID")
        if profile_id in ids:
            raise ServiceLaneError("SERVICE_LANE_PROFILE_DUPLICATE", profile_id)
        ids.add(profile_id)
        family = _required_text(lane, "chipset_family", "SERVICE_LANE_FAMILY_INVALID")
        families.add(family)
        if lane.get("model_scope") != "REFERENCE_FIXTURE_ONLY":
            raise ServiceLaneError("SERVICE_LANE_MODEL_SCOPE_INVALID", profile_id)
        if lane.get("proof_level") != "replay_supported":
            raise ServiceLaneError("SERVICE_LANE_PROOF_OVERSTATED", profile_id)
        if lane.get("hardware_certification") != "HARDWARE_PENDING":
            raise ServiceLaneError("SERVICE_LANE_HARDWARE_OVERSTATED", profile_id)
        limitations = lane.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            raise ServiceLaneError("SERVICE_LANE_LIMITATIONS_MISSING", profile_id)

        artifact = _mapping(lane.get("artifact_identity"), "SERVICE_ARTIFACT_INVALID")
        fixture_hash = str(artifact.get("fixture_sha256", ""))
        if not _SHA256_RE.fullmatch(fixture_hash):
            raise ServiceLaneError("SERVICE_ARTIFACT_HASH_INVALID", profile_id)
        if artifact.get("hash_required") is not True or artifact.get("target_binding_required") is not True:
            raise ServiceLaneError("SERVICE_ARTIFACT_BINDING_WEAK", profile_id)
        if artifact.get("device_use_allowed") is not False:
            raise ServiceLaneError("SERVICE_ARTIFACT_DEVICE_USE_FORBIDDEN", profile_id)

        proof = _mapping(lane.get("read_only_proof"), "SERVICE_READ_ONLY_PROOF_INVALID")
        evidence_hash = str(proof.get("evidence_sha256", ""))
        if not _SHA256_RE.fullmatch(evidence_hash):
            raise ServiceLaneError("SERVICE_EVIDENCE_HASH_INVALID", profile_id)

        if family == "qualcomm":
            _validate_qcom_lane(lane)
        elif family == "mediatek":
            _validate_mtk_lane(lane)
        else:
            raise ServiceLaneError("SERVICE_LANE_FAMILY_UNSUPPORTED", family)

    if families != {"qualcomm", "mediatek"}:
        raise ServiceLaneError("SERVICE_LANE_FAMILY_SET_INVALID", repr(sorted(families)))


def evaluate_service_replay(source: Path | str | Mapping[str, Any]) -> ServiceLaneResult:
    manifest = load_service_lane_manifest()
    replay = _load_replay(source)
    profile_id = _required_text(replay, "profile_id", "SERVICE_REPLAY_PROFILE_INVALID")
    lanes = {str(item["profile_id"]): item for item in manifest["lanes"]}
    lane = lanes.get(profile_id)
    if lane is None:
        raise ServiceLaneError("SERVICE_REPLAY_PROFILE_UNKNOWN", profile_id)

    if replay.get("proof_level") != lane["proof_level"]:
        raise ServiceLaneError("SERVICE_REPLAY_PROOF_MISMATCH", profile_id)
    if replay.get("hardware_certification") != "HARDWARE_PENDING":
        raise ServiceLaneError("SERVICE_REPLAY_HARDWARE_OVERSTATED", profile_id)
    if replay.get("production_enabled") is not False:
        raise ServiceLaneError("SERVICE_REPLAY_PRODUCTION_FORBIDDEN", profile_id)
    if replay.get("device_modification") != "OUT_OF_SCOPE":
        raise ServiceLaneError("SERVICE_REPLAY_SCOPE_EXPANDED", profile_id)

    artifact = _mapping(replay.get("artifact_identity"), "SERVICE_REPLAY_ARTIFACT_INVALID")
    expected_artifact = _mapping(lane.get("artifact_identity"), "SERVICE_ARTIFACT_INVALID")
    if artifact.get("kind") != expected_artifact.get("kind"):
        raise ServiceLaneError("SERVICE_ARTIFACT_KIND_MISMATCH", profile_id)
    if artifact.get("sha256") != expected_artifact.get("fixture_sha256"):
        raise ServiceLaneError("SERVICE_ARTIFACT_HASH_MISMATCH", profile_id)
    if artifact.get("device_used") is not False:
        raise ServiceLaneError("SERVICE_ARTIFACT_DEVICE_USE_FORBIDDEN", profile_id)
    binding = _mapping(artifact.get("target_binding"), "SERVICE_ARTIFACT_TARGET_BINDING_MISSING")
    if binding.get("chipset_family") != lane["chipset_family"]:
        raise ServiceLaneError("SERVICE_ARTIFACT_TARGET_MISMATCH", profile_id)
    if not isinstance(binding.get("storage_type"), str) or not binding.get("storage_type"):
        raise ServiceLaneError("SERVICE_ARTIFACT_STORAGE_BINDING_MISSING", profile_id)

    if replay.get("evidence_sha256") != lane["read_only_proof"]["evidence_sha256"]:
        raise ServiceLaneError("SERVICE_EVIDENCE_HASH_MISMATCH", profile_id)

    if lane["chipset_family"] == "qualcomm":
        transport_ok, protocol_ok, inventory_ok = _evaluate_qcom_replay(lane, replay)
    else:
        transport_ok, protocol_ok, inventory_ok = _evaluate_mtk_replay(lane, replay)

    return ServiceLaneResult(
        profile_id=profile_id,
        operation_id=str(lane["operation_id"]),
        proof_level=str(lane["proof_level"]),
        hardware_certification=str(lane["hardware_certification"]),
        transport_verified=transport_ok,
        protocol_verified=protocol_ok,
        artifact_identity_verified=True,
        read_only_inventory_verified=inventory_ok,
    )


def prove_reference_pairs() -> dict[str, Any]:
    qcom = evaluate_service_replay(REPLAY_ROOT / "qualcomm_9008_gpt_readonly.json")
    mtk = evaluate_service_replay(REPLAY_ROOT / "mtk_brom_partition_readonly.json")
    results = [qcom.to_dict(), mtk.to_dict()]
    if not all(
        item["transport_verified"]
        and item["protocol_verified"]
        and item["artifact_identity_verified"]
        and item["read_only_inventory_verified"]
        for item in results
    ):
        raise ServiceLaneError("SERVICE_REFERENCE_PROOF_INCOMPLETE", repr(results))
    return {
        "schema": "techguytool-huawei.phase14-proof.v1",
        "status": "PASS",
        "model_operation_pairs": results,
        "proof_level": "replay_supported",
        "hardware_certification": "HARDWARE_PENDING",
        "physical_qcom_9008": "HARDWARE_PENDING",
        "physical_mtk_brom_preloader": "HARDWARE_PENDING",
        "bounded_write_proof": "DEFERRED",
        "production_enabled": False,
        "device_modification": "OUT_OF_SCOPE",
    }


def _validate_qcom_lane(lane: Mapping[str, Any]) -> None:
    if lane.get("operation_id") != "read_only_gpt_inventory":
        raise ServiceLaneError("QCOM_OPERATION_INVALID", str(lane.get("operation_id")))
    transport = _mapping(lane.get("transport"), "QCOM_TRANSPORT_INVALID")
    expected = {"kind": "qualcomm_edl", "mode": "edl", "usb_vid": "05C6", "usb_pid": "9008"}
    for key, value in expected.items():
        if transport.get(key) != value:
            raise ServiceLaneError("QCOM_TRANSPORT_INVALID", f"{key}={transport.get(key)!r}")
    protocol = _mapping(lane.get("protocol_observation"), "QCOM_PROTOCOL_INVALID")
    if protocol.get("entry") != "sahara" or protocol.get("required_state") != "HELLO_RESPONSE":
        raise ServiceLaneError("QCOM_SAHARA_POLICY_INVALID", repr(protocol))
    if protocol.get("service_family") != "firehose":
        raise ServiceLaneError("QCOM_SERVICE_FAMILY_INVALID", repr(protocol.get("service_family")))
    proof = _mapping(lane.get("read_only_proof"), "QCOM_READ_ONLY_PROOF_INVALID")
    if proof.get("storage_required") is not True or proof.get("gpt_inventory_required") is not True:
        raise ServiceLaneError("QCOM_READ_ONLY_PROOF_INCOMPLETE", str(lane.get("profile_id")))


def _validate_mtk_lane(lane: Mapping[str, Any]) -> None:
    if lane.get("operation_id") != "read_only_partition_inventory":
        raise ServiceLaneError("MTK_OPERATION_INVALID", str(lane.get("operation_id")))
    transport = _mapping(lane.get("transport"), "MTK_TRANSPORT_INVALID")
    if transport.get("kind") != "mtk_bootrom_preloader" or transport.get("usb_vid") != "0E8D":
        raise ServiceLaneError("MTK_TRANSPORT_INVALID", repr(transport))
    modes = transport.get("accepted_modes")
    if modes != ["bootrom", "preloader"]:
        raise ServiceLaneError("MTK_MODE_SET_INVALID", repr(modes))
    if transport.get("bootrom_pid_fixture") != "0003" or transport.get("preloader_pid") != "2000":
        raise ServiceLaneError("MTK_USB_FIXTURE_INVALID", repr(transport))
    protocol = _mapping(lane.get("protocol_observation"), "MTK_PROTOCOL_INVALID")
    states = protocol.get("allowed_security_states")
    required = {"NONE", "SLA_REQUIRED", "DAA_REQUIRED", "SLA_DAA_REQUIRED", "UNKNOWN"}
    if not isinstance(states, list) or set(states) != required:
        raise ServiceLaneError("MTK_SECURITY_STATE_SET_INVALID", repr(states))
    if protocol.get("security_state_required") is not True or protocol.get("service_family") != "download_agent":
        raise ServiceLaneError("MTK_PROTOCOL_INVALID", repr(protocol))
    proof = _mapping(lane.get("read_only_proof"), "MTK_READ_ONLY_PROOF_INVALID")
    if proof.get("partition_inventory_required") is not True:
        raise ServiceLaneError("MTK_READ_ONLY_PROOF_INCOMPLETE", str(lane.get("profile_id")))


def _evaluate_qcom_replay(lane: Mapping[str, Any], replay: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    transport = _mapping(replay.get("transport"), "QCOM_REPLAY_TRANSPORT_INVALID")
    expected = _mapping(lane.get("transport"), "QCOM_TRANSPORT_INVALID")
    for key in ("kind", "mode", "usb_vid", "usb_pid"):
        if transport.get(key) != expected.get(key):
            raise ServiceLaneError("QCOM_REPLAY_TRANSPORT_MISMATCH", key)
    if transport.get("present") is not True:
        raise ServiceLaneError("QCOM_REPLAY_ENDPOINT_ABSENT", str(lane.get("profile_id")))
    protocol = _mapping(replay.get("protocol_observation"), "QCOM_REPLAY_PROTOCOL_INVALID")
    policy = _mapping(lane.get("protocol_observation"), "QCOM_PROTOCOL_INVALID")
    if protocol.get("entry") != policy.get("entry") or protocol.get("state") != policy.get("required_state"):
        raise ServiceLaneError("QCOM_REPLAY_SAHARA_MISMATCH", repr(protocol))
    if protocol.get("service_family") != policy.get("service_family") or protocol.get("read_only") is not True:
        raise ServiceLaneError("QCOM_REPLAY_PROTOCOL_SCOPE_INVALID", repr(protocol))
    storage = _mapping(replay.get("storage"), "QCOM_REPLAY_STORAGE_MISSING")
    if not storage.get("type") or int(storage.get("logical_block_size", 0)) <= 0 or int(storage.get("capacity_bytes", 0)) <= 0:
        raise ServiceLaneError("QCOM_REPLAY_STORAGE_INVALID", repr(storage))
    inventory = replay.get("gpt_inventory")
    _validate_inventory(inventory, "QCOM_GPT_INVENTORY_INVALID")
    return True, True, True


def _evaluate_mtk_replay(lane: Mapping[str, Any], replay: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    transport = _mapping(replay.get("transport"), "MTK_REPLAY_TRANSPORT_INVALID")
    policy = _mapping(lane.get("transport"), "MTK_TRANSPORT_INVALID")
    mode = str(transport.get("mode", ""))
    if transport.get("kind") != policy.get("kind") or transport.get("usb_vid") != policy.get("usb_vid"):
        raise ServiceLaneError("MTK_REPLAY_TRANSPORT_MISMATCH", repr(transport))
    if mode not in policy.get("accepted_modes", []):
        raise ServiceLaneError("MTK_REPLAY_MODE_INVALID", mode)
    expected_pid = policy["bootrom_pid_fixture"] if mode == "bootrom" else policy["preloader_pid"]
    if transport.get("usb_pid") != expected_pid or transport.get("present") is not True:
        raise ServiceLaneError("MTK_REPLAY_ENDPOINT_INVALID", repr(transport))
    protocol = _mapping(replay.get("protocol_observation"), "MTK_REPLAY_PROTOCOL_INVALID")
    protocol_policy = _mapping(lane.get("protocol_observation"), "MTK_PROTOCOL_INVALID")
    if protocol.get("entry") != protocol_policy.get("entry") or protocol.get("service_family") != protocol_policy.get("service_family"):
        raise ServiceLaneError("MTK_REPLAY_PROTOCOL_MISMATCH", repr(protocol))
    if protocol.get("security_state") not in protocol_policy.get("allowed_security_states", []):
        raise ServiceLaneError("MTK_REPLAY_SECURITY_STATE_INVALID", repr(protocol.get("security_state")))
    if protocol.get("read_only") is not True:
        raise ServiceLaneError("MTK_REPLAY_PROTOCOL_SCOPE_INVALID", repr(protocol))
    storage = _mapping(replay.get("storage"), "MTK_REPLAY_STORAGE_MISSING")
    if not storage.get("type") or int(storage.get("logical_block_size", 0)) <= 0 or int(storage.get("capacity_bytes", 0)) <= 0:
        raise ServiceLaneError("MTK_REPLAY_STORAGE_INVALID", repr(storage))
    inventory = replay.get("partition_inventory")
    _validate_inventory(inventory, "MTK_PARTITION_INVENTORY_INVALID")
    return True, True, True


def _validate_inventory(value: Any, code: str) -> None:
    if not isinstance(value, list) or not value:
        raise ServiceLaneError(code, "non-empty inventory required")
    names: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise ServiceLaneError(code, "inventory item must be an object")
        name = item.get("name")
        first = item.get("first_lba")
        last = item.get("last_lba")
        if not isinstance(name, str) or not name or name in names:
            raise ServiceLaneError(code, f"invalid or duplicate name: {name!r}")
        names.add(name)
        if not isinstance(first, int) or not isinstance(last, int) or first < 0 or last < first:
            raise ServiceLaneError(code, f"invalid LBA range for {name}")


def _load_replay(source: Path | str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(source, Mapping):
        payload = json.loads(json.dumps(dict(source), ensure_ascii=False, allow_nan=False))
    else:
        payload = _load_json(Path(source), "SERVICE_REPLAY_INVALID")
    if payload.get("schema") != REPLAY_SCHEMA:
        raise ServiceLaneError("SERVICE_REPLAY_SCHEMA_MISMATCH", repr(payload.get("schema")))
    return payload


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ServiceLaneError(code, str(exc)) from exc
    if not isinstance(payload, dict):
        raise ServiceLaneError(code, "JSON root must be an object")
    return payload


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ServiceLaneError(code, "object required")
    return value


def _required_text(value: Mapping[str, Any], field: str, code: str) -> str:
    result = value.get(field)
    if not isinstance(result, str) or not result:
        raise ServiceLaneError(code, repr(result))
    return result

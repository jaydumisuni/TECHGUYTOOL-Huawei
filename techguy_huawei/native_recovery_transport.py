from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from .recovery_identity import RecoveryIdentity

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_REPLAY=ROOT/"replay"/"kirin"/"clt_native_recovery_transport.json"
_STATIC_LEVELS=frozenset({"static_interop_research"})
_REQUIRED_BLOCKERS=frozenset({
    "SYSTEM_RECOVERY_COMMAND_FRAMING_UNKNOWN",
    "SYSTEM_RECOVERY_AUTH_FLOW_UNKNOWN",
    "SYSTEM_RECOVERY_TRANSFER_FRAMING_UNKNOWN",
    "SYSTEM_RECOVERY_COMMIT_SEQUENCE_UNKNOWN",
})

class NativeRecoveryTransportError(RuntimeError):
    pass

class TransportStatus(str,Enum):
    UNSUPPORTED="UNSUPPORTED"
    OBSERVED_UNCERTIFIED="OBSERVED_UNCERTIFIED"
    REPLAY_SUPPORTED="REPLAY_SUPPORTED"
    HARDWARE_CERTIFIED="HARDWARE_CERTIFIED"

@dataclass(frozen=True,slots=True)
class TransportCapability:
    transport_id:str
    family:str|None
    status:TransportStatus
    protocol_versions:tuple[str,...]
    package_roles:tuple[str,...]
    evidence_level:str
    write_certified:bool
    blockers:tuple[str,...]


def _validate_replay(replay:Mapping[str,Any])->None:
    required={"schema","transport_id","family","research_artifact","observed_protocol_labels","observed_package_roles","observed_exports","transport_primitives","evidence_level","write_certified","blockers","truth_boundary"}
    if set(replay)!=required:
        raise NativeRecoveryTransportError("REPLAY_SHAPE_INVALID")
    if replay["schema"]!="techguytool-huawei.clt-native-recovery-transport-replay.v1":
        raise NativeRecoveryTransportError("REPLAY_SCHEMA_INVALID")
    if replay["family"]!="CLT" or replay["transport_id"]!="clt-native-system-recovery-v1":
        raise NativeRecoveryTransportError("REPLAY_TARGET_INVALID")
    research=replay["research_artifact"]
    if not isinstance(research,Mapping):
        raise NativeRecoveryTransportError("RESEARCH_ARTIFACT_INVALID")
    if research.get("bundled") is not False or research.get("runtime_dependency") is not False:
        raise NativeRecoveryTransportError("HISUITE_RUNTIME_DEPENDENCY_FORBIDDEN")
    if research.get("sha256")!="7801f3fff3be0b3c63a68f7c577cad3dece98e4854644a1d605679c9b6d7e498":
        raise NativeRecoveryTransportError("RESEARCH_ARTIFACT_HASH_MISMATCH")
    if replay["observed_package_roles"]!=["base","cust","preload"]:
        raise NativeRecoveryTransportError("PACKAGE_ROLE_EVIDENCE_INVALID")
    if replay["evidence_level"] in _STATIC_LEVELS and replay["write_certified"] is not False:
        raise NativeRecoveryTransportError("WRITE_CERTIFICATION_EVIDENCE_INVALID")
    blockers=set(replay["blockers"] if isinstance(replay["blockers"],list) else [])
    if replay["evidence_level"] in _STATIC_LEVELS and not _REQUIRED_BLOCKERS.issubset(blockers):
        raise NativeRecoveryTransportError("STATIC_RESEARCH_BLOCKERS_INCOMPLETE")

def load_transport_replay(source:Mapping[str,Any]|str|Path|None=None)->dict[str,Any]:
    if source is None:
        data=json.loads(DEFAULT_REPLAY.read_text(encoding="utf-8"))
    elif isinstance(source,Mapping):
        data=json.loads(json.dumps(source))
    else:
        data=json.loads(Path(source).read_text(encoding="utf-8"))
    _validate_replay(data)
    return data

def probe_transport_capability(identity:RecoveryIdentity, fastboot_features:Mapping[str,Any], replay:Mapping[str,Any]|None=None)->TransportCapability:
    data=load_transport_replay(replay) if replay is not None else load_transport_replay()
    if identity.family!="CLT":
        return TransportCapability(data["transport_id"],identity.family,TransportStatus.UNSUPPORTED,(),(),data["evidence_level"],False,("CLT_FAMILY_REQUIRED",))
    if fastboot_features.get("normal_fastboot") is not True:
        return TransportCapability(data["transport_id"],identity.family,TransportStatus.UNSUPPORTED,tuple(data["observed_protocol_labels"]),tuple(data["observed_package_roles"]),data["evidence_level"],False,("NORMAL_FASTBOOT_REQUIRED",))
    certified=bool(data["write_certified"])
    status=TransportStatus.HARDWARE_CERTIFIED if certified else TransportStatus.OBSERVED_UNCERTIFIED
    return TransportCapability(data["transport_id"],identity.family,status,tuple(data["observed_protocol_labels"]),tuple(data["observed_package_roles"]),data["evidence_level"],certified,tuple(sorted(data["blockers"])))

def execute_stage(capability:TransportCapability, *, stage_id:str, artifact_hashes:Sequence[str])->dict[str,Any]:
    if not capability.write_certified or capability.status is not TransportStatus.HARDWARE_CERTIFIED:
        raise NativeRecoveryTransportError("TRANSPORT_NOT_CERTIFIED")
    raise NativeRecoveryTransportError("TRANSPORT_EXECUTOR_NOT_IMPLEMENTED")

from __future__ import annotations

import copy

import pytest

from techguy_huawei.native_recovery_transport import (
    NativeRecoveryTransportError,
    TransportStatus,
    execute_stage,
    load_transport_replay,
    probe_transport_capability,
)
from techguy_huawei.recovery_identity import RecoveryIdentity, RecoveryIdentityStatus


def clt_identity():
    return RecoveryIdentity(
        RecoveryIdentityStatus.NEED_IDENTITY_EVIDENCE,
        "CLT",
        "CLT-LGRP2-OVS 9.1.0.325",
        9,
        "6546",
        "LOCKED",
        None,
        None,
        None,
    )


def test_replay_records_clean_room_research_without_runtime_dependency():
    replay=load_transport_replay()
    assert replay["family"]=="CLT"
    assert replay["research_artifact"]["sha256"]=="7801f3fff3be0b3c63a68f7c577cad3dece98e4854644a1d605679c9b6d7e498"
    assert replay["research_artifact"]["bundled"] is False
    assert replay["research_artifact"]["runtime_dependency"] is False
    assert replay["observed_package_roles"]==["base","cust","preload"]
    assert replay["write_certified"] is False


def test_clt_fastboot_is_observed_but_not_write_certified():
    cap=probe_transport_capability(clt_identity(), {"normal_fastboot":True}, load_transport_replay())
    assert cap.status is TransportStatus.OBSERVED_UNCERTIFIED
    assert cap.write_certified is False
    assert cap.transport_id=="clt-native-system-recovery-v1"
    assert "SYSTEM_RECOVERY_COMMAND_FRAMING_UNKNOWN" in cap.blockers


def test_non_clt_identity_is_unsupported():
    ident=RecoveryIdentity(RecoveryIdentityStatus.UNSUPPORTED,"VOG","VOG-LGRP2-OVS 10.0.0.186",10,None,"LOCKED",None,None,None)
    cap=probe_transport_capability(ident,{"normal_fastboot":True},load_transport_replay())
    assert cap.status is TransportStatus.UNSUPPORTED
    assert cap.write_certified is False


def test_execution_is_blocked_while_transport_is_uncertified():
    cap=probe_transport_capability(clt_identity(), {"normal_fastboot":True}, load_transport_replay())
    with pytest.raises(NativeRecoveryTransportError,match="TRANSPORT_NOT_CERTIFIED"):
        execute_stage(cap, stage_id="transfer_recovery_payloads", artifact_hashes=["a"*64])


def test_static_research_cannot_promote_write_certification():
    replay=load_transport_replay()
    mutated=copy.deepcopy(replay)
    mutated["write_certified"]=True
    with pytest.raises(NativeRecoveryTransportError,match="WRITE_CERTIFICATION_EVIDENCE_INVALID"):
        probe_transport_capability(clt_identity(), {"normal_fastboot":True}, mutated)


def test_replay_rejects_hisuite_runtime_or_bundling():
    for field in ("bundled","runtime_dependency"):
        replay=load_transport_replay()
        replay["research_artifact"][field]=True
        with pytest.raises(NativeRecoveryTransportError,match="HISUITE_RUNTIME_DEPENDENCY_FORBIDDEN"):
            probe_transport_capability(clt_identity(), {"normal_fastboot":True}, replay)


def test_fastboot_absence_keeps_transport_unsupported():
    cap=probe_transport_capability(clt_identity(), {"normal_fastboot":False}, load_transport_replay())
    assert cap.status is TransportStatus.UNSUPPORTED
    assert "NORMAL_FASTBOOT_REQUIRED" in cap.blockers

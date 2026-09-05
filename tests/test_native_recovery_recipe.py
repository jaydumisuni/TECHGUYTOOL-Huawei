from __future__ import annotations

import pytest

from techguy_huawei.native_recovery_recipe import (
    NativeRecoveryRecipeError,
    compile_native_recovery_plan,
    load_native_recovery_recipe,
)
from techguy_huawei.recovery_identity import RecoveryIdentity, RecoveryIdentityStatus
from techguy_huawei.recovery_packages import RecoveryPackageArtifact, RecoveryPackageSet


def identity(status=RecoveryIdentityStatus.READY):
    return RecoveryIdentity(status,"CLT","CLT-LGRP2-OVS 9.1.0.325",9,"6546","LOCKED","CLT-L29","C432","C432R1")

def package_set(ready=True):
    arts={}
    for role,sha in (("base","a"*64),("cust","b"*64),("preload","c"*64)):
        arts[role]=RecoveryPackageArtifact(role,f"/{role}.zip",sha,10,role,"CLT",None if role=="base" else "CLT-L29",None if role=="base" else "C432","9.1.0.1")
    return RecoveryPackageSet(ready,None if ready else "ANTI_ROLLBACK_UNRESOLVED","CLT","CLT-L29","C432",arts,"compatible" if ready else "unknown")

def test_recipe_has_required_order_and_no_execution_authority():
    r=load_native_recovery_recipe()
    ids=[s["id"] for s in r["stages"]]
    assert ids==[
        "certify_continuity","verify_fastboot","resolve_identity","bind_packages","verify_package_set",
        "acquire_recovery_lease","prepare_transport","transfer_recovery_payloads","verify_transfer",
        "enter_update_stage","verify_resulting_identity","close_recovery_plan"
    ]
    assert r["authority"]=="planning_only"
    assert r["production_enabled"] is False

def test_plan_blocks_when_identity_not_exact():
    plan=compile_native_recovery_plan(identity(RecoveryIdentityStatus.NEED_IDENTITY_EVIDENCE),package_set(),"session-1",{"certified":True,"id":"clt"})
    assert plan["state"]=="blocked"
    assert "IDENTITY_NOT_READY" in plan["blockers"]

def test_plan_blocks_when_transport_not_certified():
    plan=compile_native_recovery_plan(identity(),package_set(),"session-1",{"certified":False,"id":"clt"})
    assert plan["state"]=="blocked"
    assert "TRANSPORT_NOT_CERTIFIED" in plan["blockers"]

def test_plan_ready_only_when_all_authorities_ready():
    plan=compile_native_recovery_plan(identity(),package_set(),"session-1",{"certified":True,"id":"clt-native-v1"})
    assert plan["state"]=="ready"
    assert plan["target_profile_id"]=="CLT-L29.C432"
    assert plan["artifact_hashes"]==["a"*64,"b"*64,"c"*64]
    assert plan["production_enabled"] is False

def test_recipe_rejects_reordered_stages():
    r=load_native_recovery_recipe(); r["stages"][0],r["stages"][1]=r["stages"][1],r["stages"][0]
    with pytest.raises(NativeRecoveryRecipeError,match="STAGE_ORDER_INVALID"):
        compile_native_recovery_plan(identity(),package_set(),"session-1",{"certified":True,"id":"clt"},recipe=r)

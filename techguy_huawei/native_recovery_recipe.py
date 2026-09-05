from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .recovery_identity import RecoveryIdentity, RecoveryIdentityStatus
from .recovery_packages import RecoveryPackageSet

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RECIPE=ROOT/"recipes"/"clt_native_system_recovery_v1.json"
STAGE_ORDER=("certify_continuity","verify_fastboot","resolve_identity","bind_packages","verify_package_set","acquire_recovery_lease","prepare_transport","transfer_recovery_payloads","verify_transfer","enter_update_stage","verify_resulting_identity","close_recovery_plan")

class NativeRecoveryRecipeError(ValueError):
    pass

def _canonical(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)

def load_native_recovery_recipe(source:Mapping[str,Any]|str|Path|None=None)->dict[str,Any]:
    if source is None: data=json.loads(DEFAULT_RECIPE.read_text(encoding="utf-8"))
    elif isinstance(source,Mapping): data=deepcopy(dict(source))
    else: data=json.loads(Path(source).read_text(encoding="utf-8"))
    validate_native_recovery_recipe(data)
    return data

def validate_native_recovery_recipe(recipe:Mapping[str,Any])->None:
    required={"schema","recipe_id","recipe_version","authority","execution_authority","production_enabled","family","required_mode","required_package_roles","stages","truth_boundary"}
    if set(recipe)!=required: raise NativeRecoveryRecipeError("RECIPE_SHAPE_INVALID")
    if recipe["schema"]!="techguytool-huawei.native-system-recovery.clt.v1": raise NativeRecoveryRecipeError("RECIPE_SCHEMA_INVALID")
    if recipe["authority"]!="planning_only" or recipe["execution_authority"]!="lease_required" or recipe["production_enabled"] is not False: raise NativeRecoveryRecipeError("RECIPE_AUTHORITY_EXPANDED")
    if recipe["family"]!="CLT" or recipe["required_mode"]!="normal_fastboot": raise NativeRecoveryRecipeError("RECIPE_TARGET_INVALID")
    if recipe["required_package_roles"]!=["base","cust","preload"]: raise NativeRecoveryRecipeError("PACKAGE_ROLE_SET_INVALID")
    ids=[s.get("id") for s in recipe["stages"]]
    if tuple(ids)!=STAGE_ORDER: raise NativeRecoveryRecipeError("STAGE_ORDER_INVALID")

def recipe_hash(recipe:Mapping[str,Any])->str:
    validate_native_recovery_recipe(recipe)
    return hashlib.sha256(_canonical(recipe).encode()).hexdigest()

def compile_native_recovery_plan(identity:RecoveryIdentity, package_set:RecoveryPackageSet, physical_session_id:str, transport_capability:Mapping[str,Any], *, recipe:Mapping[str,Any]|None=None)->dict[str,Any]:
    r=load_native_recovery_recipe(recipe) if recipe is not None else load_native_recovery_recipe()
    blockers=[]
    if identity.status is not RecoveryIdentityStatus.READY: blockers.append("IDENTITY_NOT_READY")
    if not package_set.ready: blockers.append(package_set.blocker or "PACKAGE_SET_NOT_READY")
    if not physical_session_id: blockers.append("PHYSICAL_SESSION_REQUIRED")
    if transport_capability.get("certified") is not True: blockers.append("TRANSPORT_NOT_CERTIFIED")
    if identity.lock_state!="LOCKED": blockers.append("LOCK_STATE_UNEXPECTED")
    target=f"{identity.model}.{identity.region}" if identity.model and identity.region else "CLT.UNKNOWN"
    hashes=sorted(a.sha256 for a in package_set.artifacts.values()) if package_set.artifacts else []
    return {
        "schema":"techguytool-huawei.compiled-native-recovery-plan.v1",
        "recipe_id":r["recipe_id"],
        "recipe_hash":recipe_hash(r),
        "physical_session_id":physical_session_id,
        "target_profile_id":target,
        "transport_id":transport_capability.get("id"),
        "artifact_hashes":hashes,
        "state":"blocked" if blockers else "ready",
        "blockers":blockers,
        "stages":[dict(s) for s in r["stages"]],
        "production_enabled":False,
        "device_authority":"none",
    }

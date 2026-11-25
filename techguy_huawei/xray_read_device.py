"""Read-only integration of the canonical TTG Device X-Ray deep scan.

The shared scanner owns evidence collection. Huawei projects selected, bound
observations into its technician report; never promote a scan to write authority.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import os
import subprocess
import sys
import uuid

from .device_engine import DeviceSnapshot, EngineResult
from .action_health import ActionState
from .platform_tools import resolve_tool


def bundled_source(project:Path)->Path:
    from hashlib import sha256
    root=project/"runtime"/"xray"
    manifest=json.loads((root/"source-manifest.json").read_text(encoding="utf8"))
    if manifest.get("commit")!="47df719f60d85e06ccecd867fdd4d65b26864378":
        raise RuntimeError("Unexpected bundled X-Ray source version")
    for rel,expected in manifest["files"].items():
        path=root/rel
        if not path.is_file() or path.is_symlink() or root.resolve() not in path.resolve().parents or sha256(path.read_bytes()).hexdigest()!=expected:
            raise RuntimeError("Bundled X-Ray integrity check failed: "+rel)
    return root/"src"


def _runtime(project:Path)->tuple[list[str],dict]:
    env=os.environ.copy()
    bundled_source(project)
    if getattr(sys,"frozen",False):
        return [str(Path(sys.argv[0]).resolve()),"--xray-worker"],env
    interpreter=Path(sys.executable)
    if interpreter.name.lower()=="pythonw.exe":
        interpreter=interpreter.with_name("python.exe")
    return [str(interpreter),str(project/"main.py"),"--xray-worker"],env


def scan(project:Path,root:Path)->dict:
    cmd,env=_runtime(project)
    for tool in ("adb","fastboot"):
        resolved=resolve_tool(project,tool)
        if resolved:env["TTG_XRAY_"+tool.upper()]=resolved
    job=root.resolve()/("read-device-"+uuid.uuid4().hex)
    job.mkdir(parents=True,exist_ok=False)
    p=subprocess.run([*cmd,str(job)],cwd=project,env=env,shell=False,
                      capture_output=True,text=True,encoding="utf-8",errors="replace",
                      timeout=600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if p.returncode not in (0,2):
        raise RuntimeError("X-Ray scanner failed; full diagnostic log saved")
    summary=json.loads((job/"scanner-summary.json").read_text(encoding="utf8"))
    bundle=Path(summary["output"]).resolve()
    if job not in bundle.parents or not bundle.is_dir():
        raise RuntimeError("X-Ray returned an invalid evidence path")
    candidates=json.loads((bundle/"device_candidates.json").read_text(encoding="utf8"))
    return {"summary":summary,"candidates":candidates,"bundle":str(bundle)}


def _known(value):
    return isinstance(value,str) and bool(value.strip()) and value.strip().casefold() not in {
        "unknown","unavailable","none","n/a","not reported","null"
    }


def project_scan(snapshot:DeviceSnapshot,base:EngineResult,report:dict)->tuple[DeviceSnapshot,EngineResult]:
    data=report["candidates"]
    rows=data.get("candidates",[])
    selected=data.get("selected_candidate_id")
    # A selected candidate alone is not evidence of physical binding if
    # several devices are attached. Require the existing exact serial or a
    # unique Huawei/Honor protocol identity.
    if snapshot.serial:
        matches=[c for c in rows if c.get("identity",{}).get("serial")==snapshot.serial]
    else:
        matches=[c for c in rows if c.get("candidate_id")==selected and
            any(str(c.get("identity",{}).get(k,"")).strip().casefold() in {"huawei","honor"} for k in ("brand","manufacturer"))]
        if len(rows)!=1:matches=[]
    if len(matches)!=1:
        payload=dict(base.payload or {})
        payload["xray"]={"status":"UNBOUND","bundle":report["bundle"],"candidate_count":len(rows)}
        return snapshot,EngineResult(base.ok,base.message,base.health_state,payload)
    c=matches[0];identity=c.get("identity",{});storage=c.get("storage",{})
    brands={str(identity.get(k,"")).strip().casefold() for k in ("brand","manufacturer") if _known(identity.get(k))}
    if brands and not brands.intersection({"huawei","honor"}):
        raise RuntimeError("X-Ray identity conflicts with Huawei/Honor")
    # Never silently overwrite an already resolved conflicting model.
    model=identity.get("internal_model") or identity.get("marketing_model")
    if snapshot.serial and _known(model) and snapshot.model not in {"Huawei Android Device","NO DEVICE CONNECTED"} and "-" in snapshot.model and snapshot.model.casefold()!=model.casefold():
        raise RuntimeError("X-Ray model conflicts with the live Huawei probe")
    snapshot.connected=True
    mapping={"product_name":"marketing_model","model":"internal_model","platform":"chipset",
             "serial":"serial","build_number":"build","security_patch":"security_patch","board_id":"board"}
    for attr,key in mapping.items():
        value=identity.get(key)
        if _known(value):setattr(snapshot,attr,value)
    if not snapshot.session_id:
        snapshot.session_id=str(uuid.uuid4())
    mode=identity.get("active_mode")
    if _known(mode) and (not snapshot.interface or snapshot.interface in {"Huawei USB","?"}):snapshot.interface=mode
    locked=identity.get("bootloader_locked")
    if isinstance(locked,bool):
        snapshot.bootloader_state="locked" if locked else "unlocked"
        snapshot.security="Bootloader "+snapshot.bootloader_state
    observations=c.get("observations",[])
    details={}
    for key,label in (("imei","IMEI"),("firmware_version","Firmware version"),
                      ("bootloader","Bootloader version"),("kernel","Kernel")):
        if _known(identity.get(key)):details[label]=identity[key]
    for o in observations:
        if not o.get("connected"):continue
        ids=o.get("identifiers",{})
        caps=o.get("capabilities",{})
        if _known(ids.get("android")):snapshot.android_version=ids["android"]
        if _known(ids.get("vendorcountry")):snapshot.vendor_country=ids["vendorcountry"]
        for key,label in (("imei","IMEI"),("imei2","IMEI 2"),("meid","MEID")):
            if _known(ids.get(key)):details.setdefault(label,ids[key])

        for key,label in (("device","Device codename"),("baseband","Baseband"),
                          ("kernel","Kernel"),("fingerprint","Build fingerprint"),
                          ("variant","Variant"),("anti","Anti-rollback"),
                          ("battery-voltage","Battery voltage"),("secure","Secure boot")):
            if _known(ids.get(key)):details.setdefault(label,ids[key])
    for key,label in (("baseband","Baseband"),("storage_model","Storage model"),
                      ("verified_boot_state","Verified boot"),("slot_suffix","Active slot")):
        if _known(identity.get(key)):details.setdefault(label,identity[key])
    capacity=storage.get("capacity_bytes") or identity.get("storage_capacity_bytes")
    if isinstance(capacity,int) and capacity>0:details["Internal storage"]=f"{capacity/10**9:.2f} GB ({capacity/2**30:.2f} GiB)"
    if _known(storage.get("storage_type")):details["Storage type"]=storage["storage_type"]
    count=storage.get("partition_count")
    if isinstance(count,int) and count>0:details["Observed partitions"]=str(count)
    deep=report["summary"].get("deep_diagnostics") or {}
    diagnostics=deep.get("candidates",{}).get(c["candidate_id"],{})
    for name,status in diagnostics.get("causes",{}).items():
        if status in {"SUSPECTED","POSSIBLE_BUILD_CONFLICT"}:
            details[name.replace("_"," ").capitalize()]=status.replace("_"," ").lower()
    health=diagnostics.get("health_descriptors",[])
    if health:
        known=[h.get("status") for h in health if h.get("status") in {"WARNING","URGENT","REPORTED"}]
        if known:details["Storage health"]="Urgent" if "URGENT" in known else "Warning" if "WARNING" in known else "Descriptors reported"
    payload=dict(base.payload or {})
    payload.update(asdict(snapshot))
    payload["xray"]={"status":"BOUND","bundle":report["bundle"],"candidate_id":c["candidate_id"],
                     "verdict":c.get("certification",{}).get("verdict"),"details":details,
                     "identity":identity,"storage":storage,
                     "partitions":[{"transport":o.get("transport"),**part} for o in observations if o.get("connected") for part in o.get("partitions",[])],
                     "diagnostics":diagnostics,"certification":c.get("certification",{}),
                     "firmware":c.get("firmware",{}),"profile_match":c.get("profile_match",{}),
                     "challenges":c.get("challenges",[]),
                     "write_allowed":False}
    return snapshot,EngineResult(True,f"Connected: {snapshot.model} via {snapshot.interface}.",ActionState.READY,payload)


def enrich(engine,base:EngineResult,root:Path,progress):
    progress("X-Ray: deep device identity, firmware and storage scan...")
    try:
        report=scan(engine.app_root,root)
        snapshot,result=project_scan(engine.snapshot,base,report)
        engine.snapshot=snapshot
        return result
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        payload=dict(base.payload or {})
        payload["xray"]={"status":"UNAVAILABLE","reason":str(exc),"write_allowed":False}
        return EngineResult(base.ok,base.message,base.health_state,payload)

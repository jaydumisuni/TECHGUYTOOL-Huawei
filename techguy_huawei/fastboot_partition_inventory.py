"""Read-only Huawei Fastboot partition inventory (donor ptable contract)."""
import re
from dataclasses import replace
from subprocess import SubprocessError

def parse_table(code, output):
    if code or len(output)>1024*1024 or "FAILED" in output.upper():
        return []
    names=[]
    for line in output.splitlines():
        m=re.fullmatch(r"\s*\(bootloader\)\s*:\s*([A-Za-z][A-Za-z0-9_]{0,63})\s*",line)
        if m:
            name=m.group(1).lower()
            if name not in names:names.append(name)
            if len(names)>512:return []
    return [{"name":name,"transport":"fastboot","source":"huawei_ptable","read_only":True} for name in names]

def enrich_inventory(engine,result,serial,progress):
    # Observe names only, never transfer partition contents, or open service mode.
    snapshot=engine.snapshot
    if not result.ok or not serial or snapshot.serial!=serial or snapshot.interface!="Fastboot":
        return result
    binary=engine._tool("fastboot")
    if not binary:return result
    progress("Reading Huawei Fastboot partition inventory...")
    try:
        proc,_=engine._run("read_device",[binary,"-s",serial,"getvar","ptable"])
        rows=parse_table(proc.returncode,(proc.stdout or "")+"\n"+(proc.stderr or ""))
    except (OSError,SubprocessError):
        return result
    if not rows:return result
    payload=dict(result.payload or {})
    xray=payload.get("xray",{})
    observed=xray.get("partitions",[]) if xray.get("status")=="BOUND" else []
    names={str(row.get("name","")).lower() for row in observed if isinstance(row,dict)}
    payload["partition_inventory"]=[*observed,*(row for row in rows if row["name"] not in names)]
    return replace(result,payload=payload)

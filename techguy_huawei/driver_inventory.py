"""Local Windows driver inventory for the existing driver dialog.

Scan only: no driver replacement, removal, or elevated operation is inferred
from USB enumeration. Report the actual PnP state and missing package custody.
"""
import json,os,shutil,subprocess
from .device_engine import EngineResult
from .action_health import ActionState

SCRIPT=r"""
$items = @(Get-PnpDevice -PresentOnly -ErrorAction Stop | Where-Object {
    $_.InstanceId -match '^USB\\VID_(12D1|05C6)' -or
    $_.FriendlyName -match 'Huawei|Honor|QDLoader|Android.*(ADB|Bootloader)|Fastboot'
} | ForEach-Object {
    [ordered]@{name=[string]$_.FriendlyName;class=[string]$_.Class;status=[string]$_.Status;problem=[string]$_.Problem}
})
ConvertTo-Json -InputObject $items -Compress
"""
def scan(runner=subprocess.run):
    powershell=shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:return EngineResult(False,"Windows PnP inventory unavailable.",ActionState.MISSING_DEPENDENCY)
    try:
        proc=runner([powershell,"-NoProfile","-NonInteractive","-Command",SCRIPT],shell=False,
                    capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if proc.returncode:raise ValueError((proc.stderr or "PnP query failed").strip())
        rows=json.loads(proc.stdout.lstrip("\ufeff"))
        if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):raise ValueError("Invalid driver inventory")
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return EngineResult(False,"Driver scan failed: "+str(exc),ActionState.FAILED)
    return EngineResult(True,"Driver scan complete: "+str(len(rows))+" relevant present interfaces. No driver changes performed; installation requires a matching signed driver package.",ActionState.READY,{"interfaces":rows,"scan_only":True})

def repair(runner=subprocess.run):
    """Ask Windows to rediscover hardware using its existing driver store."""
    before=scan(runner)
    if not before.ok:return before
    if not any(str(row.get("status","")).upper()!="OK" or str(row.get("problem","")) not in {"","CM_PROB_NONE","0"} for row in before.payload["interfaces"]):
        return EngineResult(True,"No present driver fault detected.",ActionState.READY,{**before.payload,"repair_attempted":False})
    exe=shutil.which("pnputil.exe")
    if not exe:
        return EngineResult(False,"Windows PnP repair utility unavailable.",ActionState.MISSING_DEPENDENCY,before.payload)
    try:
        proc=runner([exe,"/scan-devices"],shell=False,capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    except (OSError,subprocess.SubprocessError) as exc:
        return EngineResult(False,"Driver rediscovery failed: "+str(exc),ActionState.FAILED,before.payload)
    after=scan(runner)
    rows=(after.payload or {}).get("interfaces",[])
    clear=bool(rows) and after.ok and all(str(row.get("status","")).upper()=="OK" and str(row.get("problem","")) in {"","CM_PROB_NONE","0"} for row in rows)
    ok=proc.returncode==0 and clear
    message="Windows driver rediscovery completed; present interfaces report healthy." if ok else "Driver fault not resolved by Windows rediscovery. A matching signed driver package or administrator authorization may be required."
    return EngineResult(ok,message,ActionState.READY if ok else ActionState.FAILED,{"interfaces":rows,"before":before.payload["interfaces"],"scan_only":False,"repair_attempted":True,"rediscovery_exit":proc.returncode})

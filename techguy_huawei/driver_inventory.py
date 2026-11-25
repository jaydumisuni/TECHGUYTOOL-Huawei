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

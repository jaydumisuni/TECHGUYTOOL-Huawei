"""Official device-facing owner assistance; no lock removal or credential access."""
from .action_health import ActionState
from .device_engine import EngineResult

def run(engine, action, expected_serial=""):
    if action not in {"pair","huawei_id","bootloader","frp_repair"}:
        raise ValueError("Unknown owner service")
    result=engine.probe()
    snapshot=engine.snapshot
    if not result.ok or not snapshot.connected or not snapshot.serial:
        return EngineResult(False,"Connect one identified Huawei/Honor device first.",ActionState.GUARDED)
    if expected_serial and snapshot.serial!=expected_serial:
        return EngineResult(False,"Connected device changed; read the intended device again.",ActionState.GUARDED)
    payload={"model":snapshot.model,"interface":snapshot.interface,"serial_bound":True}
    if action=="bootloader":
        state=snapshot.bootloader_state or "not reported"
        return EngineResult(state in {"locked","unlocked"},"Bootloader state: "+state+". Use the manufacturer's authorized unlock/relock procedure where available.",ActionState.READY if state in {"locked","unlocked"} else ActionState.GUARDED,{**payload,"bootloader_state":state,"lock_changed":False})
    if action=="frp_repair":
        return EngineResult(False,"Use the previously synced Google account or official account recovery. No factory-reset protection state was changed.",ActionState.GUARDED,{**payload,"frp_state":snapshot.frp_state or "not reported","lock_changed":False})
    if snapshot.interface!="ADB":
        return EngineResult(False,"Start Android and authorize USB debugging to open device settings.",ActionState.GUARDED,payload)
    adb=engine._tool("adb")
    if not adb:return EngineResult(False,"Local ADB unavailable.",ActionState.MISSING_DEPENDENCY,payload)
    # Bind the selected authorized transport again immediately before the UI action.
    proc,_=engine._run("owner_service_inventory",[adb,"devices","-l"])
    rows=engine._adb_rows(proc.stdout)
    if proc.returncode or len(rows)!=1 or rows[0].split()[:2]!=[snapshot.serial,"device"]:
        return EngineResult(False,"Authorized Android connection changed.",ActionState.GUARDED,payload)
    intent="android.settings.BLUETOOTH_SETTINGS" if action=="pair" else "android.settings.SYNC_SETTINGS"
    proc,_=engine._run("owner_service_settings",[adb,"-s",snapshot.serial,"shell","am","start","-a",intent])
    text=(proc.stdout or "")+" "+(proc.stderr or "")
    ok=proc.returncode==0 and "Starting:" in text and not any(x in text.lower() for x in ("error:","exception","unable to resolve","permission denial"))
    return EngineResult(ok,("Bluetooth pairing settings opened on the device." if action=="pair" else "Account settings opened on the device.") if ok else "Android did not confirm opening the requested settings.",ActionState.READY if ok else ActionState.FAILED,{**payload,"settings_opened":ok,"user_action_required":True,"repair_completed":False})

from types import SimpleNamespace
from techguy_huawei.owner_services import run
from techguy_huawei.device_engine import DeviceSnapshot,EngineResult,DeviceEngine
from techguy_huawei.action_health import ActionState
from techguy_huawei.detected_target import observed_target

class Engine:
    def __init__(self):
        self.snapshot=DeviceSnapshot(connected=True,interface="ADB",model="ANE-LX1",serial="TEST1",bootloader_state="locked")
        self.calls=[]
    def probe(self):return EngineResult(True,"Detected",ActionState.READY)
    def _tool(self,name):return "adb"
    _adb_rows=staticmethod(DeviceEngine._adb_rows)
    def _run(self,action,argv):
        self.calls.append(argv)
        return SimpleNamespace(returncode=0,stdout="TEST1 device" if action=="owner_service_inventory" else "Starting: Intent",stderr=""),[]

def test_pair_and_account_open_settings_only():
    e=Engine()
    assert run(e,"pair","TEST1").payload["settings_opened"]
    assert e.calls[-1][-1]=="android.settings.BLUETOOTH_SETTINGS"
    assert run(e,"huawei_id","TEST1").payload["repair_completed"] is False
    assert e.calls[-1][-1]=="android.settings.SYNC_SETTINGS"
    before=len(e.calls)
    assert not run(e,"pair","OTHER").ok
    assert len(e.calls)==before
    assert run(e,"bootloader","TEST1").payload["lock_changed"] is False
    assert not run(e,"frp_repair","TEST1").ok
    assert len(e.calls)==before

def test_exact_silicon_suffix_refinement():
    for generic,exact in [("kirin620","hisi620c"),("kirin710","hisi710a")]:
        d=DeviceSnapshot(connected=True,interface="Fastboot",model="ABC-LX1",serial="TEST1",platform=exact)
        target=observed_target(d,{},lambda m:generic)
        assert (target.chipset,target.loader_variant,target.conflict)==(generic,exact,False)

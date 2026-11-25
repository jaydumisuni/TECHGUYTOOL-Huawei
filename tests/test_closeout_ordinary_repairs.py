from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from techguy_huawei import driver_inventory,partition_service as p,firmware_flash as f
from test_partition_service import Transport

def test_driver_rediscovery_checks_post_state(monkeypatch):
    monkeypatch.setattr(driver_inventory.shutil,"which",lambda name:name)
    scans=iter([[{"name":"Huawei USB","status":"Error","problem":"CM_PROB_FAILED_START"}],[{"name":"Huawei USB","status":"OK","problem":"CM_PROB_NONE"}]])
    commands=[]
    def runner(argv,**kwargs):
        commands.append(argv)
        assert not kwargs["shell"]
        return SimpleNamespace(returncode=0,stdout=json.dumps(next(scans)) if argv[0].startswith("powershell") else "",stderr="")
    result=driver_inventory.repair(runner)
    assert result.ok and result.payload["repair_attempted"]
    assert commands[1]==["pnputil.exe","/scan-devices"]

def test_erase_requires_confirmation_backup_and_readback(tmp_path,monkeypatch):
    class EraseTransport(Transport):
        def __call__(self,exe,args,timeout=12):
            if args[2:]==["erase","system"]:
                self.calls.append(args)
                self.writes+=1
                self.data=b"\0"*4096
                return 0,"Erasing 'system' OKAY"
            return super().__call__(exe,args,timeout)
    tr=EraseTransport();monkeypatch.setattr(f,"_exec",tr)
    args=("fake","SIM01","ANE-LX1","kirin659","system")
    plan=p.prepare_erase(*args)
    assert not tr.writes
    with pytest.raises(f.FlashError,match="plan changed"):
        p.apply_erase(*args,"wrong",tmp_path,lambda _:None)
    assert not tr.writes
    receipt=p.apply_erase(*args,plan["fingerprint"],tmp_path,lambda _:None)
    assert receipt["erase_acknowledged"] and receipt["readback_verified"]
    assert Path(receipt["backup_path"]).with_name("partition.img").read_bytes()==b"A"*4096
    assert tr.writes==1
    assert not any("reboot" in args for args in tr.calls)

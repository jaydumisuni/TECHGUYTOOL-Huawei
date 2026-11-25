from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from techguy_huawei.operation_history import records,read_log,export
from techguy_huawei.operation_log import ActionLog
from techguy_huawei.action_health import ActionState
from techguy_huawei.device_engine import EngineResult
from techguy_huawei import driver_inventory

def test_existing_reports_and_export(tmp_path):
    root=tmp_path/"logs"
    r=ActionLog(root,"read_device")
    r.add("Model: ANE-LX1")
    r.complete(EngineResult(True,"Read complete",ActionState.READY))
    rows=records(root)
    assert len(rows)==1 and rows[0]["model"]=="ANE-LX1" and rows[0]["result"]=="OK"
    assert "Read complete" in read_log(root,r.log_path)
    dest=tmp_path/"history.json"
    export(root,dest,rows)
    assert json.loads(dest.read_text())==rows
    with pytest.raises(ValueError):export(root,dest,rows)
    with pytest.raises(ValueError):read_log(root,dest)
    assert r.log_path.exists()

def test_driver_inventory_uses_read_only_query(monkeypatch):
    monkeypatch.setattr(driver_inventory.shutil,"which",lambda _: "powershell.exe")
    def fake(argv,**kwargs):
        assert not kwargs["shell"] and "Get-PnpDevice" in argv[-1]
        return SimpleNamespace(returncode=0,stdout=json.dumps([{"name":"Huawei USB","status":"OK"}]),stderr="")
    r=driver_inventory.scan(fake)
    assert r.ok and r.payload["scan_only"] and r.payload["interfaces"][0]["status"]=="OK"

from pathlib import Path
from types import SimpleNamespace
import json
import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication,QEventLoop,QTimer
from techguy_huawei import backend as backend_module
from techguy_huawei import desktop_worker as worker_module
from techguy_huawei.backend import Backend
from techguy_huawei.action_health import ActionState
from techguy_huawei.device_engine import EngineResult
from techguy_huawei.service_dispatch import ServiceResponse


def test_gui_preflight_then_distinct_confirm_worker_without_device_writes(tmp_path,monkeypatch):
    evidence=tmp_path/"evidence"
    evidence.mkdir()
    monkeypatch.setattr(backend_module.AppPaths,"resolve",
        lambda:SimpleNamespace(root=tmp_path,evidence=evidence,logs=evidence,registration=evidence/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    actions=[]
    def service(request,progress=None,cancel=None):
        actions.append(request)
        if request.firmware_apply:
            assert request.firmware_plan_hash=="frozen-package-plan"
            assert request.firmware_model=="ELE-L29"
            assert request.firmware_chipset=="kirin980"
            return ServiceResponse(request.action_id,EngineResult(
                True,"Simulated writes accepted",ActionState.READY,
                {"preflight_only":False,"write_authorized":True,"no_reboot":True}))
        return ServiceResponse(request.action_id,EngineResult(
            True,"Package inspected",ActionState.READY,
            {"fingerprint":"frozen-package-plan","preflight_only":True,
             "write_authorized":False,"model":"ELE-L29","chipset":"kirin980",
             "mode":"Repair","partitions":[{"partition":"kernel"}]}))
    monkeypatch.setattr(worker_module,"execute",service)
    app=QCoreApplication.instance() or QCoreApplication([])
    ui=Backend(Path(__file__).resolve().parents[1])
    ui.health_timer.stop()
    events=[]
    ui.firmwarePlanChanged.connect(lambda:events.append((ui.operationBusy,ui.firmwarePlanReady)))
    def complete():
        loop=QEventLoop()
        deadline=QTimer();deadline.setSingleShot(True);deadline.timeout.connect(loop.quit);deadline.start(4500)
        ui.operationBusyChanged.connect(lambda:loop.quit() if not ui.operationBusy else None)
        while ui.operationBusy and deadline.isActive():loop.exec()
        deadline.stop()
        assert not ui.operationBusy
    ui.setFirmwarePath(str(tmp_path/"package.json"))
    ui.setFirmwareModel("ELE-L29")
    ui.setFirmwareChipset("kirin980")
    ui.setFirmwareMode("Repair")
    assert ui.firmwarePlanReady is False
    ui.runAction("flash_firmware")
    complete()
    assert len(actions)==1 and actions[0].firmware_apply is False
    assert ui.firmwarePlanReady and (False,True) in events
    assert ui.confirmFirmwareFlash()
    complete()
    assert len(actions)==2 and actions[1].firmware_apply is True
    assert ui.firmwarePlanReady is False
    assert ui.confirmFirmwareFlash() is False

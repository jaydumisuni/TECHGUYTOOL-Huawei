from pathlib import Path
from types import SimpleNamespace
import pytest
from techguy_huawei.device_engine import DeviceSnapshot
from techguy_huawei.detected_target import observed_target, ObservedTarget

ROOT=Path(__file__).resolve().parents[1]
def snap(model,chip,serial="S1",interface="Fastboot"):
    return DeviceSnapshot(connected=True,interface=interface,model=model,platform=chip,serial=serial)

def test_projection():
    lookup=lambda m: {"VTR-L29":"kirin960","ANE-LX1":"kirin659"}.get(m,"")
    assert observed_target(snap("VTR-L29","hisi960"),{},lookup)==ObservedTarget("VTR-L29","kirin960")
    assert observed_target(snap("ANE-LX1","Android / ADB",interface="ADB"),{},lookup)==ObservedTarget("ANE-LX1","kirin659")
    assert observed_target(snap("VTR-L29","kirin980"),{},lookup).conflict
    assert observed_target(snap("Huawei device (identity pending)","Huawei USB","","HUAWEI USB COM 1.0"),{},lookup)==ObservedTarget()
    assert observed_target(snap("Huawei kirin980 (model unresolved)","kirin980"),{},lookup)==ObservedTarget("","kirin980")

def test_shared_auto_target_changes_and_disconnect(tmp_path,monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    from techguy_huawei import backend as module
    from techguy_huawei.backend import Backend
    from techguy_huawei.action_health import ActionState
    from techguy_huawei.device_engine import EngineResult
    from techguy_huawei.service_dispatch import ServiceResponse
    app=QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(module.AppPaths,"resolve",lambda:SimpleNamespace(root=tmp_path,evidence=tmp_path,logs=tmp_path,registration=tmp_path/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    ui=Backend(ROOT);ui.health_timer.stop()
    def result(device,ok=True):
        ui.registry.begin_async("read_device")
        ui._on_service_finished(ServiceResponse("read_device",EngineResult(ok,"Simulated detection",ActionState.READY,{}),device))
    result(snap("VTR-L29","kirin960"))
    assert (ui.firmwareModel,ui.firmwareChipset)==("VTR-L29","kirin960")
    result(snap("ANE-LX1","kirin659","S2"))
    assert (ui.firmwareModel,ui.firmwareChipset)==("ANE-LX1","kirin659")
    assert ui.loaderVariantOptions==["hisi65x_a","hisi65x_b"]
    assert ui.setLoaderVariant("hisi65x_a")
    result(snap("ANE-LX1","kirin659","S3"))
    assert ui.loaderVariant==""
    result(DeviceSnapshot(),False)
    assert (ui.firmwareModel,ui.firmwareChipset)==("","")
    ui.setFirmwareModel("ELE-L29")
    result(snap("ANE-LX1","kirin659"))
    assert ui.firmwareModel=="ELE-L29"

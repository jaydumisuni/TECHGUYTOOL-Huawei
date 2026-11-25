from pathlib import Path
from types import SimpleNamespace
import pytest
from techguy_huawei.usb_presence import Presence,PresenceTracker
from techguy_huawei.detected_target import observed_target,ObservedTarget
from techguy_huawei.device_engine import DeviceSnapshot

ROOT=Path(__file__).resolve().parents[1]

def test_presence_transitions():
    t=PresenceTracker()
    empty=Presence("no_huawei")
    adb=Presence("adb","device-a","107e")
    fastboot=Presence("normal_fastboot","device-a","3609")
    assert t.update(empty)=="unchanged"
    assert t.update(adb)=="scan"
    assert t.update(adb)=="unchanged"
    assert t.update(None)=="unchanged"
    assert t.update(fastboot)=="scan"
    assert t.update(Presence("normal_fastboot","device-b","3609"))=="scan"
    assert t.update(Presence("multiple_huawei_devices"))=="clear"
    assert t.update(empty)=="clear"
    assert t.update(empty)=="unchanged"

def test_reported_variant_only():
    lookup=lambda m:"kirin659"
    d=DeviceSnapshot(connected=True,interface="Fastboot",model="ANE-LX1",serial="S1",platform="hisi65x_a")
    assert observed_target(d,{},lookup)==ObservedTarget("ANE-LX1","kirin659",False,"hisi65x_a")
    d.platform="kirin659";d.board_id="unknown"
    assert observed_target(d,{},lookup).loader_variant==""
    d.platform="hisi710a"
    assert observed_target(d,{},lookup).conflict

def test_backend_hotplug_automatically_dispatches_reads_and_clears(tmp_path,monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication,QEventLoop,QTimer
    from techguy_huawei import backend as module,usb_presence
    from techguy_huawei.backend import Backend
    app=QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(module.AppPaths,"resolve",lambda:SimpleNamespace(root=tmp_path,evidence=tmp_path,logs=tmp_path,registration=tmp_path/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    ui=Backend(ROOT);ui.health_timer.stop()
    calls=[]
    monkeypatch.setattr(ui,"runAction",lambda a:calls.append(a))
    monkeypatch.setattr(module.sys,"platform","win32")
    current=Presence("adb","A","107e")
    monkeypatch.setattr(usb_presence,"observe",lambda:current)
    ui._heartbeat()
    loop=QEventLoop();timer=QTimer()
    timer.timeout.connect(lambda:loop.quit() if ui._usb_presence_worker is None else None)
    timer.start(10);QTimer.singleShot(2000,loop.quit);loop.exec();timer.stop()
    assert calls==["read_device"] and ui._usb_presence_worker is None
    ui._on_usb_presence(current)
    assert calls==["read_device"]
    ui._device_snapshot=DeviceSnapshot(connected=True,interface="Fastboot",model="ANE-LX1",serial="S1",platform="hisi65x_a")
    ui._apply_detected_target({})
    assert ui.firmwareModel=="ANE-LX1" and ui.firmwareChipset=="kirin659" and ui.loaderVariant=="hisi65x_a"
    ui._on_usb_presence(None)
    assert ui.connected
    ui._busy=True
    ui._on_usb_presence(Presence("no_huawei"))
    assert ui.connected
    ui._busy=False
    ui._on_usb_presence(Presence("no_huawei"))
    assert not ui.connected and not ui.firmwareModel and not ui.loaderVariant
    ui._on_usb_presence(Presence("normal_fastboot","B","3609"))
    assert calls==["read_device","read_device"]

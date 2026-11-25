from pathlib import Path
import json
from types import SimpleNamespace
import pytest
from techguy_huawei.service_loader_registry import resolve_loader, resolve_variant

ROOT=Path(__file__).resolve().parents[1]

def test_each_ambiguous_model_resolves_variants_without_changing_chipset(tmp_path,monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication
    from techguy_huawei import backend as module
    from techguy_huawei.backend import Backend
    app=QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(module.AppPaths,"resolve",lambda:SimpleNamespace(
        root=tmp_path,evidence=tmp_path,logs=tmp_path,registration=tmp_path/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    ui=Backend(ROOT);ui.health_timer.stop()
    rows=json.loads(ui.deviceProfilesJson)["models"]
    checked=0; choices=0
    for row in rows:
        ui.selectDeviceProfile(row["model"])
        chip=ui.firmwareChipset
        base=resolve_loader(ROOT,chip)
        if base.status!="loader_variant_required":continue
        assert ui.loaderVariant==""
        for candidate in base.candidate_families:
            assert ui.setLoaderVariant(candidate)
            assert ui.firmwareModel==row["model"] and ui.firmwareChipset==chip
            selected=json.loads(ui.selectedServiceLoaderJson)
            assert selected["status"]=="verified_container_available"
            assert selected["cpu"]==candidate
            assert selected["chipset"]==base.chipset
            assert selected["transport_proven"] is False
            choices+=1
        assert not ui.setLoaderVariant("hisi990")
        assert ui.setLoaderVariant("")
        assert json.loads(ui.selectedServiceLoaderJson)["status"]=="loader_variant_required"
        checked+=1
    assert checked==27 and choices==54
    ui.selectDeviceProfile("ANE-LX1")
    ui.setFirmwareChipset("hisi65x_a")
    assert ui.firmwareChipset=="kirin659" and ui.loaderVariant=="hisi65x_a"
    ui.selectDeviceProfile("VTR-L29")
    assert ui.firmwareChipset=="kirin960" and ui.loaderVariant==""
    ui.selectDeviceProfile("UNKNOWN-X99")
    assert ui.firmwareChipset=="" and ui.loaderVariant==""
    print("MODEL_VARIANT_CHOICES_PASS",checked,choices)

def test_invalid_variant_does_not_resolve():
    assert resolve_variant(ROOT,"kirin659","hisi990").status=="invalid_loader_variant"
    assert resolve_variant(ROOT,"kirin980","hisi970").status=="invalid_loader_variant"

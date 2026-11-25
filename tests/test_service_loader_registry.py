from __future__ import annotations
import json,shutil
from pathlib import Path

from techguy_huawei.service_loader_registry import resolve_loader


def test_kirin980_loader_resolves_exact_verified_stage():
    root=Path(__file__).resolve().parents[1]
    result=resolve_loader(root,"kirin980")
    assert result.status=="verified_images_unstaged",result
    assert result.cpu=="hisi980" and result.stage=="service-fastboot"
    assert result.image_names==("xloader.img","uce.img","fastboot.img")
    assert not result.transport_proven
    assert Path(result.loader_root).is_dir()


def test_unknown_and_unqualified_chipsets_do_not_get_fallback_loader():
    root=Path(__file__).resolve().parents[1]
    for chip in ("mt6785","qualcomm",""):
        result=resolve_loader(root,chip)
        assert result.status in ("no_qualified_loader","awaiting_chipset")
        assert not result.image_names


def test_hash_mismatch_is_not_accepted(tmp_path):
    (tmp_path/"data").mkdir()
    (tmp_path/"runtime"/"service-loaders"/"hisi980").mkdir(parents=True)
    source=Path(__file__).resolve().parents[1]
    shutil.copyfile(source/"data"/"service_loader_profiles.json",tmp_path/"data"/"service_loader_profiles.json")
    for name in ("xloader.img","uce.img","fastboot.img"):
        shutil.copyfile(source/"runtime"/"service-loaders"/"hisi980"/name,
                        tmp_path/"runtime"/"service-loaders"/"hisi980"/name)
    image=tmp_path/"runtime"/"service-loaders"/"hisi980"/"xloader.img"
    with image.open("r+b") as f:
        byte=f.read(1);f.seek(0);f.write(bytes([byte[0]^1]))
    resolved=resolve_loader(tmp_path,"kirin980")
    assert resolved.status=="loader_hash_mismatch"


def test_selected_model_autofills_correct_loader_without_touching_phone(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from PySide6.QtCore import QCoreApplication
    from techguy_huawei import backend as module
    from techguy_huawei.backend import Backend
    from techguy_huawei.testpoint_catalog import load_device_profiles
    root=Path(__file__).resolve().parents[1]
    app=QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(module.AppPaths,"resolve",lambda:SimpleNamespace(
        root=tmp_path,evidence=tmp_path,logs=tmp_path,registration=tmp_path/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    ui=Backend(root)
    ui.health_timer.stop()
    ui.selectDeviceProfile("ELE-L29")
    assert ui.firmwareChipset=="kirin980"
    desc=json.loads(ui.selectedServiceLoaderJson)
    assert desc["cpu"]=="hisi980" and desc["status"]=="verified_images_unstaged"
    assert "not sent" in ui.selectedServiceLoaderLabel.lower()
    ui.setFirmwareChipset("kirin970")
    assert ui.firmwareModel==""
    assert json.loads(ui.selectedServiceLoaderJson)["status"] in {"verified_container_available","loader_files_missing","no_qualified_loader"}

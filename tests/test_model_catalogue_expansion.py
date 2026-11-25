from pathlib import Path
from collections import Counter
import json
import re
import pytest
from techguy_huawei.fastboot_identity import canonical_chipset
from techguy_huawei.service_loader_registry import resolve_loader

ROOT=Path(__file__).resolve().parents[1]

def test_catalogue_has_unique_sourced_model_mappings():
    rows=json.loads((ROOT/"data/device_profiles.json").read_text(encoding="utf8"))["models"]
    ids=[r["model"] for r in rows]
    assert len(ids)==len(set(ids))
    assert len(rows)>=96
    for r in rows:
        assert r["name"] and r["platform"]
        if r.get("provenance")=="published_hardware_specification":
            assert r["source"].startswith("https://")
            assert r["chipset"]
    assert next(r for r in rows if r["model"]=="VTR-L29")["chipset"]=="kirin960"

def test_loader_variant_aliases_remain_distinct():
    assert canonical_chipset("hisi710a")=="kirin710a"
    assert canonical_chipset("hisi620c")=="kirin620c"
    assert canonical_chipset("hisi710")!="kirin710a"
    assert canonical_chipset("hisi620")!="kirin620c"

def test_all_catalogue_rows_use_shared_backend_selection(tmp_path,monkeypatch):
    pytest.importorskip("PySide6")
    from types import SimpleNamespace
    from PySide6.QtCore import QCoreApplication
    from techguy_huawei import backend as module
    from techguy_huawei.backend import Backend
    app=QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(module.AppPaths,"resolve",lambda:SimpleNamespace(
        root=tmp_path,evidence=tmp_path,logs=tmp_path,registration=tmp_path/"registration.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self:None)
    ui=Backend(ROOT);ui.health_timer.stop()
    rows=json.loads(ui.deviceProfilesJson)["models"]
    counts=Counter()
    for r in rows:
        ui.selectDeviceProfile(r["model"])
        expected=r.get("chipset",r["platform"].lower().replace(" ",""))
        assert ui.firmwareModel==r["model"]
        assert canonical_chipset(ui.firmwareChipset)==canonical_chipset(expected),r
        resolved=json.loads(ui.selectedServiceLoaderJson)
        assert resolved==json.loads(json.dumps(resolve_loader(ROOT,expected).to_dict()))
        counts[resolved["status"]]+=1
        if expected.startswith(("kirin","hisi")):
            assert resolved["status"] in {"verified_container_available","verified_images_unstaged","loader_variant_required"},(r,resolved)
            assert "HUAWEI USB COM 1.0"==ui.expectedServiceInterface(r["model"])
    print("MODEL_CATALOGUE_RESOLUTION",dict(counts))

from pathlib import Path
import json
from techguy_huawei.service_loader_registry import resolve_loader
from techguy_huawei.fastboot_identity import canonical_chipset
from techguy_huawei.qualcomm_layout import scalar,compare,preview
from techguy_huawei.firmware_flash import FlashError
import pytest

ROOT=Path(__file__).resolve().parents[1]

def test_all_reference_family_resolution():
    rows=json.loads((ROOT/"data/kirin_loader_inventory.json").read_text())["families"]
    assert len(rows)==18 and sum(len(x["files"]) for x in rows)==56
    for row in rows:
        cpu=row["cpu"]
        selection=resolve_loader(ROOT,cpu)
        assert selection.status in {"verified_container_available","verified_images_unstaged","loader_variant_required","loader_files_missing"},(cpu,selection)
        if selection.status=="loader_variant_required":
            assert cpu in selection.candidate_families
        else:
            assert selection.cpu==cpu
    assert canonical_chipset("k3v2")=="hisik3v2"

def test_gpt_preview_scalar_and_delta():
    assert scalar("NUM_DISK_SECTORS-33.",1000)==967
    with pytest.raises(FlashError):scalar("NUM_DISK_SECTORS*9",1000)
    d=compare({"rows":{"system":(34,99),"old":(100,101)}},{"rows":{"system":(34,120),"new":(121,122)}})
    assert d["added"]==["new"] and d["removed"]==["old"] and not d["same_layout"]
    assert d["changed"][0]["name"]=="system"
    assert preview({"all_operations":[]},{})=={}

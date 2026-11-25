from pathlib import Path
import pytest
from techguy_huawei import firmware_flash as f
from techguy_huawei.kirin_board_package import inspect
from techguy_huawei.qualcomm_board import xml_root
from test_firmware_flash_generic import Fastboot

def vendor(root,model="ANE-LX1",chip="kirin659"):
    root.mkdir(exist_ok=True)
    (root/"system.img").write_bytes(b"system"*100)
    (root/"loader.img").write_bytes(b"loader")
    (root/"oem.img").write_bytes(b"oem")
    text=f'''<?xml version="1.0" encoding="gb2312"?>
<configurations><configuration ap_platform="{chip}" product_id="{model.split('-')[0]}" version="{model}-BD 1.0">
<bootloaderimage_ddr><image identifier="xloader" name="DDR">absent.img</image></bootloaderimage_ddr>
<bootloaderimage><image identifier="xloader" name="LOADER">loader.img</image></bootloaderimage>
<eraseimage><image identifier="userdata" name="USERDATA"></image></eraseimage>
<fastbootimage><image identifier="system" name="SYSTEM">system.img</image>
<image identifier="oeminfo" name="OEMINFO">oem.img</image></fastbootimage>
</configuration></configurations>'''
    p=root/"Download.xml";p.write_bytes(text.encode("gb2312"));return p

@pytest.mark.parametrize("model,chip",[("ANE-LX1","kirin659"),("CLT-L29","kirin970"),("ELE-L29","kirin980"),("ABC-LX1","kirin990")])
def test_vendor_repair(tmp_path,monkeypatch,model,chip):
    p=vendor(tmp_path,model,chip)
    plan=inspect(p)
    assert plan["model"]==model
    assert [o.partition for o in plan["operations"]]==["system"]
    assert len(plan["stages"])==3
    assert any("optional DDR" in x["reason"] for x in plan["excluded"])
    fb=Fastboot(chip=chip,model=model)
    def run(exe,args,timeout=12):
        if args[-2:]==["getvar","partition-size:system"]:return 0,"partition-size:system: 0x1000"
        return fb(exe,args,timeout)
    monkeypatch.setattr(f,"_exec",run)
    selected=f.plan(str(p),model,chip,"Repair","fake")
    assert not any("flash" in a for a in fb.calls)
    assert selected.operations[0].partition=="system"
    r=f.apply(str(p),model,chip,"Repair","fake",selected.fingerprint,tmp_path/"evidence",lambda _:None)
    assert r["completed"]==1 and r["no_reboot"]
    assert [a[5] for a in fb.calls if a[2:5]==["-S","256M","flash"]]==["system"]

def test_vendor_repair_rejects_missing_selected_image(tmp_path):
    p=vendor(tmp_path);(tmp_path/"system.img").unlink()
    with pytest.raises(f.FlashError,match="Missing firmware image"):inspect(p)

def test_vendor_rejects_model_mismatch(tmp_path):
    p=vendor(tmp_path)
    with pytest.raises(f.FlashError,match="model differs"):inspect(p,"ANE-LX2")

def test_vendor_rejects_entity_declaration(tmp_path):
    p=tmp_path/"Download.xml";p.write_text('<!DOCTYPE configurations [<!ENTITY x "bad">]><configurations/>')
    with pytest.raises(ValueError):xml_root(p)

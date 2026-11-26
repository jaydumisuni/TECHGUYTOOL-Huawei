from pathlib import Path
import hashlib
import json
import struct
import pytest
from techguy_huawei import firmware_flash as f

def raw_app(root,part="KERNEL"):
    root.mkdir(parents=True,exist_ok=True)
    file=root/"UPDATE.APP"
    data=b"tested payload" * 50
    header=bytearray(98)
    header[:4]=f.MAGIC
    struct.pack_into("<I",header,4,98)
    struct.pack_into("<I",header,24,len(data))
    header[60:60+len(part)] = part.encode("ascii")
    file.write_bytes(bytes(92)+header+data)
    return file

def fake(monkeypatch,*,chip="kirin980",model="",fastboot_serial="SERVICE01"):
    calls=[]
    def exec_cmd(binary,argv,timeout=12):
        calls.append(list(argv))
        if argv==["devices"]:return 0,fastboot_serial+"\tfastboot\n"
        if argv[-2:]==["getvar","product"]:return 0,"product: "+chip
        if argv[-2:]==["oem","get-bootinfo"]:return 0,"(bootloader)  unlocked\nOKAY"
        if argv[-2:]==["oem","get-build-number"]:
            return (0,f"(bootloader): {model} 10.0.0.1") if model else (1,"FAILED")
        raise AssertionError(argv)
    monkeypatch.setattr(f,"_exec",exec_cmd)
    return calls

def test_raw_auto_detect_model_chipset(tmp_path,monkeypatch):
    calls=fake(monkeypatch,model="ELE-L29")
    plan=f.plan(str(raw_app(tmp_path/"ELE-L29D-Firmware")),"","","Repair","fake")
    assert plan.model=="ELE-L29" and plan.chipset=="kirin980"
    assert [x.partition for x in plan.operations]==["kernel"]
    assert not any("flash" in a for a in calls)

def test_raw_manual_model_detect_chipset_when_model_hidden(tmp_path,monkeypatch):
    calls=fake(monkeypatch)
    plan=f.plan(str(raw_app(tmp_path/"VOGUE-L29D-Firmware")),"VOG-L29","","Repair","fake")
    assert plan.model=="VOG-L29" and plan.chipset=="kirin980"
    assert plan.device_reported_model==""
    assert not any("flash" in a for a in calls)

def test_raw_chipset_selection_requires_model_when_unreadable(tmp_path,monkeypatch):
    calls=fake(monkeypatch)
    with pytest.raises(f.FlashError,match="Model detection unavailable"):
        f.plan(str(raw_app(tmp_path/"Unknown")),"","kirin980","Repair","fake")
    assert not any("flash" in a for a in calls)

def test_downgrade_guard_requires_antirollback_proof(tmp_path,monkeypatch):
    calls=fake(monkeypatch)
    app=raw_app(tmp_path/"ELE-L29")
    with pytest.raises(f.FlashError,match="anti-rollback"):
        f.plan(str(app),"ELE-L29","kirin980","Downgrade","fake")
    assert not calls

@pytest.mark.parametrize("partition",["oeminfo_a","userdata_b","modemnvm_factory_a","fastboot_b","xloader_a","ptable"])
def test_protected_partition_variants_remain_blocked(partition):
    assert f._protected_partition(partition)

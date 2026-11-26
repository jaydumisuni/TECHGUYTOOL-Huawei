from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
import pytest
from techguy_huawei import firmware_flash as f

class Fastboot:
    def __init__(self,chip="kirin980",multiple=False,model="",fail=False):
        self.chip,self.multiple,self.model,self.fail=chip,multiple,model,fail
        self.calls=[]
    def __call__(self,exe,args,timeout=12):
        self.calls.append(args)
        if args==["devices"]:
            return 0,"TEST01\tfastboot\n"+("TEST02\tfastboot\n" if self.multiple else "")
        if args[-2:]==["oem","get-bootinfo"]:return 0,"(bootloader)  unlocked\nOKAY"
        if args[-2:]==["getvar","product"]:return 0,"product: "+self.chip
        if args[-2:]==["oem","get-build-number"]:
            return (0,"(bootloader): "+self.model+" 10.0.0.1") if self.model else (1,"FAILED")
        if args[2:5]==["-S","256M","flash"]:
            partition=args[5]
            return (1,"FAILED") if self.fail else (0,f"Sending '{partition}' OKAY\nWriting '{partition}' OKAY")
        raise AssertionError(args)

def manifest(root,model,chip,partition="kernel"):
    dest=root/model;dest.mkdir()
    image=dest/"firmware.img";image.write_bytes(b"firmware"*1000)
    m=dest/"package.json";m.write_text(json.dumps({"schema":f.SCHEMA,"model":model,
        "chipset":chip,"operations":[{"partition":partition,"file":image.name,
        "size":image.stat().st_size,"sha256":hashlib.sha256(image.read_bytes()).hexdigest()}]}))
    return m

@pytest.mark.parametrize("model,chip",[("VOG-L29","kirin980"),("ELE-L29","kirin980"),("ANE-LX1","kirin659")])
def test_manifest_generic_models(tmp_path,monkeypatch,model,chip):
    fb=Fastboot(chip);monkeypatch.setattr(f,"_exec",fb)
    p=f.plan(str(manifest(tmp_path,model,chip)),model,"","Repair","fake")
    assert p.model==model and p.chipset==chip and len(p.operations)==1
    assert not any("flash" in x for x in fb.calls)

def test_manual_update_app_parsing_and_protection(tmp_path,monkeypatch):
    fb=Fastboot();monkeypatch.setattr(f,"_exec",fb)
    raw=bytearray(92)
    for name in ("KERNEL","OEMINFO","VBMETA"):
        data=name.encode()*8;head=bytearray(98);head[:4]=f.MAGIC
        struct.pack_into("<I",head,4,98);struct.pack_into("<I",head,24,len(data))
        head[60:60+len(name)]=name.encode();raw.extend(head);raw.extend(data)
    app=tmp_path/"UPDATE.APP";app.write_bytes(raw)
    p=f.plan(str(app),"ELE-L29","kirin980","Repair","fake")
    assert [x.partition for x in p.operations]==["kernel","vbmeta"]
    assert "OEMINFO" in p.excluded

def test_mismatch_blocks_write(tmp_path,monkeypatch):
    fb=Fastboot("kirin970");monkeypatch.setattr(f,"_exec",fb)
    with pytest.raises(f.FlashError,match="chipset"):
        f.plan(str(manifest(tmp_path,"ELE-L29","kirin980")),"ELE-L29","","Repair","fake")
    assert not any("flash" in x for x in fb.calls)

def test_model_family_guard(tmp_path,monkeypatch):
    fb=Fastboot(model="CLT-L29");monkeypatch.setattr(f,"_exec",fb)
    with pytest.raises(f.FlashError,match="model family"):
        f.plan(str(manifest(tmp_path,"ELE-L29","kirin980")),"ELE-L29","","Repair","fake")

def test_no_protected_partition(tmp_path,monkeypatch):
    fb=Fastboot();monkeypatch.setattr(f,"_exec",fb)
    with pytest.raises(f.FlashError,match="Protected"):
        f.plan(str(manifest(tmp_path,"VOG-L29","kirin980","oeminfo")),"VOG-L29","","Repair","fake")
    assert not fb.calls

def test_preflight_confirm_and_no_reboot(tmp_path,monkeypatch):
    fb=Fastboot();monkeypatch.setattr(f,"_exec",fb)
    source=manifest(tmp_path,"VOG-L29","kirin980")
    p=f.plan(str(source),"VOG-L29","","Repair","fake")
    with pytest.raises(f.FlashError,match="plan changed"):
        f.apply(str(source),"VOG-L29","","Repair","fake","old",tmp_path/"ev",lambda _:None)
    assert not any("flash" in x for x in fb.calls)
    output=f.apply(str(source),"VOG-L29","","Repair","fake",p.fingerprint,tmp_path/"ev",lambda _:None)
    assert output["completed"]==1 and output["no_reboot"]
    assert any("flash" in x for x in fb.calls)
    assert not any("reboot" in x or "erase" in x or "unlock" in x for x in fb.calls)

def test_failed_write_stops(tmp_path,monkeypatch):
    fb=Fastboot(fail=True);monkeypatch.setattr(f,"_exec",fb)
    src=manifest(tmp_path,"VOG-L29","kirin980")
    p=f.plan(str(src),"VOG-L29","","Repair","fake")
    with pytest.raises(f.FlashError,match="did not acknowledge"):
        f.apply(str(src),"VOG-L29","","Repair","fake",p.fingerprint,tmp_path/"ev",lambda _:None)

def test_multi_device_rejected(tmp_path,monkeypatch):
    fb=Fastboot(multiple=True);monkeypatch.setattr(f,"_exec",fb)
    with pytest.raises(f.FlashError,match="Exactly one"):
        f.plan(str(manifest(tmp_path,"VOG-L29","kirin980")),"VOG-L29","","Repair","fake")

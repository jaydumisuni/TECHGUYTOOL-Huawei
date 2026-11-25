import hashlib,json,struct
import pytest
from techguy_huawei import firmware_flash as f
from test_firmware_flash_generic import Fastboot

def test_manifest_multipart_hash_and_execution(tmp_path,monkeypatch):
    raw=bytearray(92)
    parts=[b"A"*128,b"B"*256]
    for data in parts:
        head=bytearray(98);head[:4]=f.MAGIC
        struct.pack_into("<I",head,4,98);struct.pack_into("<I",head,24,len(data))
        head[60:65]=b"SUPER";raw.extend(head);raw.extend(data)
    app=tmp_path/"UPDATE.APP";app.write_bytes(raw)
    manifest=tmp_path/"package.json"
    operation={"partition":"super","file":app.name,"name":"SUPER","indices":[1,2],"size":384,"sha256":hashlib.sha256(b"".join(parts)).hexdigest()}
    payload={"schema":f.SCHEMA,"model":"ELE-L29","chipset":"kirin980","operations":[operation]}
    manifest.write_text(json.dumps(payload))
    fb=Fastboot(model="ELE-L29")
    def run(exe,args,timeout=12):
        if "flash" in args:
            from pathlib import Path
            assert Path(args[-1]).read_bytes()==b"".join(parts)
        return fb(exe,args,timeout)
    monkeypatch.setattr(f,"_exec",run)
    plan=f.plan(str(manifest),"ELE-L29","kirin980","Repair","fake")
    assert plan.operations[0].segments and len(plan.operations)==1
    assert f.apply(str(manifest),"ELE-L29","kirin980","Repair","fake",plan.fingerprint,tmp_path/"ev",lambda _:None)["completed"]==1
    assert not list((tmp_path/"ev").glob(".staging-*"))
    operation["indices"]=[2,1]
    manifest.write_text(json.dumps(payload))
    with pytest.raises(f.FlashError,match="merged SHA256 mismatch"):
        f.plan(str(manifest),"ELE-L29","kirin980","Repair","fake")

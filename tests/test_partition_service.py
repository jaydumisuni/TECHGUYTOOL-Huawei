from pathlib import Path
import pytest
from techguy_huawei import partition_service as p,firmware_flash as f

class Transport:
    def __init__(self):
        self.serial="SIM01";self.data=b"A"*4096;self.writes=0;self.calls=[]
    def __call__(self,exe,args,timeout=12):
        self.calls.append(args)
        if args==["devices"]:return 0,self.serial+"\tfastboot"
        if args[-2:]==["oem","get-bootinfo"]:return 0,"(bootloader) unlocked"
        if args[-2:]==["getvar","product"]:return 0,"product: kirin659"
        if args[-2:]==["oem","get-build-number"]:return 0,"(bootloader) ANE-LX1 9.1.0.1"
        if args[-2:]==["getvar","partition-size:system"]:return 0,"partition-size:system: 0x1000"
        if args[2]=="fetch":
            Path(args[-1]).write_bytes(self.data);return 0,"OKAY"
        if args[2:5]==["-S","256M","flash"]:
            self.writes+=1
            raw=Path(args[-1]).read_bytes();self.data=raw.ljust(4096,b"\0")
            return 0,"Sending 'system' OKAY\nWriting 'system' OKAY"
        raise AssertionError(args)

def test_backup_write_restore(tmp_path,monkeypatch):
    tr=Transport();monkeypatch.setattr(f,"_exec",tr)
    args=("fake","SIM01","ANE-LX1","kirin659","system")
    receipt=p.backup(*args,tmp_path,lambda _:None)
    assert tr.writes==0
    image=tmp_path/"replacement.img";image.write_bytes(b"B"*4096)
    plan=p.prepare(*args,image)
    assert tr.writes==0
    with pytest.raises(f.FlashError,match="plan changed"):
        p.apply(*args,image,False,"wrong",tmp_path,lambda _:None)
    assert tr.writes==0
    result=p.apply(*args,image,False,plan["fingerprint"],tmp_path,lambda _:None)
    assert result["readback_verified"] and tr.data==b"B"*4096
    plan=p.prepare(*args,receipt["backup_path"],True)
    assert p.apply(*args,receipt["backup_path"],True,plan["fingerprint"],tmp_path,lambda _:None)["readback_verified"]
    assert tr.data==b"A"*4096 and tr.writes==2
    assert not any("erase" in a or "reboot" in a for a in tr.calls)

def test_wrong_device_and_corrupt_backup(tmp_path,monkeypatch):
    tr=Transport();monkeypatch.setattr(f,"_exec",tr)
    args=("fake","SIM01","ANE-LX1","kirin659","system")
    receipt=p.backup(*args,tmp_path,lambda _:None)
    tr.serial="SIM02"
    with pytest.raises(f.FlashError,match="identity changed"):
        p.prepare(*args,receipt["backup_path"],True)
    tr.serial="SIM01"
    Path(receipt["backup_path"]).with_name("partition.img").write_bytes(b"X"*4096)
    with pytest.raises(f.FlashError,match="integrity mismatch"):
        p.prepare(*args,receipt["backup_path"],True)
    assert tr.writes==0

from pathlib import Path
import hashlib
import struct
import zlib
import xml.etree.ElementTree as ET
from unittest.mock import patch
import pytest
from techguy_huawei import qualcomm_package as q
from techguy_huawei.fastboot_identity import model_from_build, lock_state, canonical_chipset, acknowledged
from techguy_huawei.firmware_flash import FlashError

def fixture(root,storage="emmc",sector=512):
    root.mkdir(parents=True,exist_ok=True)
    (root/("prog_"+storage+"_firehose.elf")).write_bytes(b"\x7fELF"+b"\0"*100)
    (root/"boot.img").write_bytes(b"A"*sector)
    (root/"userdata.img").write_bytes(b"B"*sector)
    data=ET.Element("data")
    for label,start in (("boot",40),("userdata",100)):
        ET.SubElement(data,"program",label=label,filename=label+".img",SECTOR_SIZE_IN_BYTES=str(sector),num_partition_sectors="2",physical_partition_number="0",start_sector=str(start),file_sector_offset="0",sparse="false")
    raw=root/"rawprogram0.xml";ET.ElementTree(data).write(raw)
    ET.ElementTree(ET.Element("patches")).write(root/"patch0.xml")
    return raw

def gpt(sector,backup=False):
    count=128;size=128;disk=1000;array_sectors=(count*size)//sector
    a=bytearray(count*size)
    for i,(name,start,end) in enumerate((("boot",40,41),("userdata",100,101))):
        off=i*size;a[off:off+16]=b"X"*16
        struct.pack_into("<QQ",a,off+32,start,end)
        b=name.encode("utf-16-le");a[off+56:off+56+len(b)]=b
    h=bytearray(sector);h[:8]=b"EFI PART"
    struct.pack_into("<II",h,8,0x10000,92)
    struct.pack_into("<QQQQ",h,24,disk-1 if backup else 1,1 if backup else disk-1,34,disk-array_sectors-2)
    struct.pack_into("<QIII",h,72,disk-array_sectors-1 if backup else 2,count,size,zlib.crc32(a))
    struct.pack_into("<I",h,16,zlib.crc32(h[:92]))
    return bytes(a)+bytes(h) if backup else (bytes(sector)+bytes(h)+bytes(a)).ljust(34*sector,b"\0")

@pytest.mark.parametrize("storage,sector",[("emmc",512),("ufs",4096)])
def test_discovery_and_live_geometry(tmp_path,storage,sector):
    raw=fixture(tmp_path,storage,sector);p=q.discover(raw)
    assert p["storage"]==storage and len(p["operations"])==1
    assert p["excluded"]==["userdata"]
    layout=q._gpt(gpt(sector),sector,0,1);n=layout["array_sectors"]+1
    assert q._gpt(gpt(sector,True),sector,1000-n,n-1)==layout
    q._geometry(p,{0:layout})
    p["operations"][0]["start_sector"]=100
    with pytest.raises(FlashError,match="fit live"):q._geometry(p,{0:layout})

def test_discovery_without_patch(tmp_path):
    raw=fixture(tmp_path);(tmp_path/"patch0.xml").unlink()
    assert q.discover(raw)["patch"]==""

def test_ambiguous_programmer(tmp_path):
    raw=fixture(tmp_path);(tmp_path/"prog_ufs_firehose.elf").write_bytes(b"\x7fELF")
    with pytest.raises(FlashError,match="one intended"):q.discover(raw)

def test_legacy_identity():
    assert model_from_build("(bootloader) CAZ-AL10C00B387")=="CAZ-AL10"
    assert model_from_build("(bootloader) ANE-LX1 9.1.0.123")=="ANE-LX1"
    assert lock_state("(bootloader) Lock state is unlock")=="unlocked"
    assert lock_state("(bootloader) Lock state is locked")=="locked"
    assert lock_state("(bootloader) locked\n(bootloader) unlocked")=="unverified"
    assert canonical_chipset("hisi970")=="kirin970"
    assert acknowledged("system",0,"Sending sparse 'system' 1/1 (10 KB) OKAY\nWriting 'system' OKAY")

def test_package_driven_programming_mock_transport(tmp_path):
    raw=fixture(tmp_path/"package")
    evidence=tmp_path/"evidence"; target=b"A"*512+b"\0"*512
    flashed=False
    calls=[]
    def run(qdl,argv,cwd,timeout=120):
        nonlocal flashed
        calls.append(argv)
        if "--dry-run" in argv:
            return 0,'flashed "boot" successfully\nflashed 1 partition'
        if "read" in argv:
            i=argv.index("read");addr=argv[i+1];dest=Path(argv[i+2])
            if addr=="0/0+34":dest.write_bytes(gpt(512))
            elif addr=="0/967+33":dest.write_bytes(gpt(512,True))
            elif addr=="0/40+2":dest.write_bytes(target if flashed else b"Z"*1024)
            else:raise AssertionError(addr)
            return 0,'TargetName="8953"'
        if Path(argv[-1]).suffix==".xml":
            flashed=True
            return 0,'flashed "boot" successfully\nflashed 1 partition'
        raise AssertionError(argv)
    with patch.object(q,"resolve_qdl",return_value=Path("qdl")),patch.object(q,"_device",return_value="SAMPLE"),patch.object(q,"_run",side_effect=run):
        p=q.plan(tmp_path,raw,"ABC-LX1","msm8953",evidence)
        assert p["fingerprint"] and not flashed
        with pytest.raises(FlashError,match="changed"):q.apply(tmp_path,raw,"ABC-LX1","msm8953","wrong",evidence,lambda _:None)
        assert not flashed
        r=q.apply(tmp_path,raw,"ABC-LX1","msm8953",p["fingerprint"],evidence,lambda _:None)
        assert r["completed"]==1 and r["readback_verified"] and not r["boot_verified"]
        assert flashed
        assert not any("reset" in a for a in calls)

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

from hashlib import sha256
from unittest.mock import patch
import struct,zlib
import xml.etree.ElementTree as ET
from test_qualcomm_package import fixture,gpt
from techguy_huawei import qualcomm_package as q
from techguy_huawei import qualcomm_reconstruction as reconstruction

def change_boot(raw,backup=False):
    b=bytearray(raw)
    h_off=len(b)-512 if backup else 512
    a_off=0 if backup else 1024
    struct.pack_into("<QQ",b,a_off+32,50,51)
    struct.pack_into("<I",b,h_off+88,zlib.crc32(b[a_off:a_off+128*128]))
    struct.pack_into("<I",b,h_off+16,0)
    struct.pack_into("<I",b,h_off+16,zlib.crc32(b[h_off:h_off+92]))
    return bytes(b)

def test_reconstruction_full_mock_worker(tmp_path):
    raw=fixture(tmp_path/"package"); folder=raw.parent
    oldp=gpt(512);oldb=gpt(512,True)
    newp=change_boot(oldp);newb=change_boot(oldb,True)
    (folder/"gpt_main0.bin").write_bytes(newp)
    (folder/"gpt_backup0.bin").write_bytes(newb)
    tree=ET.parse(raw);root=tree.getroot()
    root[0].set("start_sector","50")
    for label,name,count,start in (("PrimaryGPT","gpt_main0.bin","34","0"),("BackupGPT","gpt_backup0.bin","33","NUM_DISK_SECTORS-33.")):
        ET.SubElement(root,"program",label=label,filename=name,
            SECTOR_SIZE_IN_BYTES="512",num_partition_sectors=count,physical_partition_number="0",
            start_sector=start,file_sector_offset="0",sparse="false")
    tree.write(raw)
    log='flashed "boot" successfully\nflashed "PrimaryGPT" successfully\nflashed "BackupGPT" successfully\nflashed 3 partitions'
    flashed=False
    def run(qdl,argv,cwd,timeout=120):
        nonlocal flashed
        if "--dry-run" in argv:return 0,log
        if "read" in argv:
            i=argv.index("read");addr=argv[i+1];dest=Path(argv[i+2])
            if addr=="0/0+34":data=newp if flashed else oldp
            elif addr=="0/966+34":data=bytes(512)+(newb if flashed else oldb)
            elif addr=="0/967+33":data=newb if flashed else oldb
            elif addr=="0/50+2":data=(b"A"*512+bytes(512)) if flashed else b"Z"*1024
            else:raise AssertionError(addr)
            dest.write_bytes(data);return 0,'TargetName="8953"'
        if Path(argv[-1]).suffix==".xml":
            flashed=True;return 0,log
        raise AssertionError(argv)
    evidence=tmp_path/"evidence"
    with patch.object(q,"resolve_qdl",return_value=Path("qdl")),patch.object(q,"_device",return_value="SAMPLE"),patch.object(q,"_run",side_effect=run):
        p=q.plan(tmp_path,raw,"ABC-LX1","msm8953",evidence)
        assert p["vendor_reconstruction"] and p["fingerprint"] and not flashed
        assert not p["layout_delta"]["0"]["primary"]["same_layout"]
        assert p["layout_delta"]["0"]["primary"]["changed"][0]["name"]=="boot"
        with pytest.raises(FlashError,match="changed"):q.apply(tmp_path,raw,"ABC-LX1","msm8953","wrong",evidence,lambda _:None)
        assert not flashed
        r=q.apply(tmp_path,raw,"ABC-LX1","msm8953",p["fingerprint"],evidence,lambda _:None)
        assert r["completed"]==3 and r["gpt_verified"] and not r["boot_verified"]
        receipt=json.loads(Path(r["evidence_path"]).read_text())
        assert len(receipt["backup"])==3 and receipt["readback"][0]["label"]=="boot"
        assert flashed

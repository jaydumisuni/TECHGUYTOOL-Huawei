from pathlib import Path
import json
from unittest.mock import patch
import xml.etree.ElementTree as ET
from techguy_huawei.action_health import ActionState
from techguy_huawei.device_engine import DeviceSnapshot,EngineResult
from techguy_huawei.xray_read_device import project_scan
from techguy_huawei.operation_log import device_read_lines,full_device_report
from test_qualcomm_package import fixture
from techguy_huawei import qualcomm_package as q

def candidate():
    return {"candidate_id":"abc","identity":{"brand":"Huawei","internal_model":"ANE-LX1",
        "chipset":"kirin659","serial":"TEST123","build":"ANE-LX1 9.1.0.1","active_mode":"adb",
        "bootloader_locked":False,"imei":"TEST_IMEI"},"storage":{"capacity_bytes":64000000000,
        "storage_type":"emmc","partition_count":1},"observations":[{"connected":True,
        "transport":"adb","identifiers":{"android":"9"},"partitions":[{"name":"system","size_bytes":1000}]}],
        "certification":{"verdict":"INVESTIGATE"}}

def test_deep_report_binding():
    c=candidate()
    s=DeviceSnapshot(connected=True,serial="TEST123",model="ANE-LX1",interface="ADB")
    base=EngineResult(True,"Connected",ActionState.READY,{})
    report={"candidates":{"selected_candidate_id":"abc","candidates":[c]},"bundle":"fixture",
        "summary":{"deep_diagnostics":{"candidates":{"abc":{"causes":{"storage_failure":"SUSPECTED"}}}}}}
    s,r=project_scan(s,base,report)
    assert s.android_version=="9" and s.platform=="kirin659"
    assert r.payload["xray"]["write_allowed"] is False
    lines="\n".join(device_read_lines(s,r))
    assert "64.00 GB" in lines and "Storage failure: suspected" in lines
    assert "Unavailable (not reported" not in lines and "TEST_IMEI" not in lines
    full=full_device_report(s,r)
    assert "PARTITION INVENTORY" in full and "system" in full and "TEST_IMEI" in full
    s.serial="DIFFERENT"
    _,r=project_scan(s,base,report)
    assert r.payload["xray"]["status"]=="UNBOUND"

def test_multigroup_not_alternative(tmp_path):
    raw=fixture(tmp_path)
    root=ET.Element("data")
    ET.SubElement(root,"program",label="vendor",filename="vendor.img",
        SECTOR_SIZE_IN_BYTES="512",num_partition_sectors="2",physical_partition_number="1",
        start_sector="40",file_sector_offset="0",sparse="false")
    (tmp_path/"vendor.img").write_bytes(b"V"*512)
    ET.ElementTree(root).write(tmp_path/"rawprogram1.xml")
    ET.ElementTree(ET.Element("patches")).write(tmp_path/"patch1.xml")
    ET.ElementTree(root).write(tmp_path/"rawprogram0_unsparse.xml")
    p=q.discover(raw)
    assert p["programs"]==["rawprogram0.xml","rawprogram1.xml"]
    assert p["patches"]==["patch0.xml","patch1.xml"]
    assert [x["label"] for x in p["operations"]]==["boot","vendor"]
    out=tmp_path/"combined.xml";q.filtered(p,out)
    assert len(ET.parse(out).getroot())==2

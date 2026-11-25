from types import SimpleNamespace
from techguy_huawei.fastboot_partition_inventory import parse_table,enrich_inventory
from techguy_huawei.device_engine import EngineResult,DeviceSnapshot
from techguy_huawei.action_health import ActionState
from techguy_huawei.operation_log import full_device_report

def test_donor_partition_table_parsing():
    text="(bootloader) : boot\n(bootloader) : SYSTEM\n(bootloader) : boot\n(bootloader) : invalid/name\nOKAY"
    assert [x["name"] for x in parse_table(0,text)]==["boot","system"]
    assert parse_table(1,text)==[]
    assert parse_table(0,text+"\nFAILED")==[]
    assert parse_table(0,"(bootloader) product: kirin980")==[]

def test_read_only_inventory_merge_and_identity():
    calls=[]
    snapshot=DeviceSnapshot(connected=True,interface="Fastboot",serial="S1")
    def run(action,argv):
        calls.append(argv)
        return SimpleNamespace(returncode=0,stdout="(bootloader) : boot",stderr="(bootloader) : system"),[]
    engine=SimpleNamespace(snapshot=snapshot,_tool=lambda name:"fastboot",_run=run)
    base=EngineResult(True,"Detected",ActionState.READY,{"xray":{"status":"BOUND","partitions":[{"name":"boot","size_bytes":512}]}})
    result=enrich_inventory(engine,base,"S1",lambda message:None)
    assert calls==[["fastboot","-s","S1","getvar","ptable"]]
    assert result.payload["partition_inventory"][0]["size_bytes"]==512
    assert result.payload["partition_inventory"][1]["name"]=="system"
    assert enrich_inventory(engine,base,"S2",lambda message:None) is base
    assert len(calls)==1
    fallback=enrich_inventory(engine,EngineResult(True,"Detected",ActionState.READY,{"xray":{"status":"UNAVAILABLE"}}),"S1",lambda message:None)
    assert "PARTITION INVENTORY" in full_device_report(snapshot,fallback)
    assert len(fallback.payload["partition_inventory"])==2

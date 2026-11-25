"""Offline vendor GPT layout preview.

Replays bounded vendor GPT patch data in memory, without a device connection.
Only GPT regions participate; other patch targets are reported separately.
"""
from __future__ import annotations
import re
import struct
import zlib
from pathlib import Path

from .firmware_flash import FlashError
from .qualcomm_package import _gpt

def scalar(value,capacity):
    if type(value) is int:return value
    raw=str(value).strip()
    if re.fullmatch(r"\d+\.?",raw):return int(raw.rstrip("."))
    m=re.fullmatch(r"NUM_DISK_SECTORS-(\d+)\.?",raw)
    if m:return capacity-int(m.group(1))
    raise FlashError("Unsupported GPT expression")

def gpt_label(label):
    return label.casefold() in {"primarygpt","backupgpt","gpt_main","gpt_backup"}

def templates(package):
    rows={}
    for op in package["all_operations"]:
        if not op["filename"] or not gpt_label(op["label"]):continue
        lun=op["physical_partition_number"]
        role="primary" if op["label"].casefold() in {"primarygpt","gpt_main"} else "backup"
        pair=rows.setdefault(lun,{})
        if role in pair:raise FlashError("Duplicate GPT image for LUN "+str(lun))
        if op["sparse"]!="false" or op["file_sector_offset"]!=0:
            raise FlashError("Unsupported GPT image encoding")
        path=Path(package["folder"])/op["filename"]
        if path.stat().st_size!=op["sector_size"]*op["sectors"] or path.stat().st_size>1024*1024:
            raise FlashError("Unsupported GPT image size")
        pair[role]=op
    if any(set(pair)!={"primary","backup"} for pair in rows.values()):
        raise FlashError("Both vendor GPT copies are required for layout preview")
    return rows

def preview(package,capacities):
    result={}
    for lun,pair in templates(package).items():
        if lun not in capacities:raise FlashError("Disk capacity not observed for LUN "+str(lun))
        capacity=capacities[lun]
        primary,backup=pair["primary"],pair["backup"]
        sector=primary["sector_size"]
        if backup["sector_size"]!=sector:raise FlashError("Conflicting GPT sector sizes")
        regions=[]
        for role,op in pair.items():
            start=scalar(op["start_sector"],capacity)
            data=bytearray((Path(package["folder"])/op["filename"]).read_bytes())
            end=start+len(data)//sector
            if start<0 or end>capacity:raise FlashError("GPT template outside disk")
            if role=="primary" and start!=0:raise FlashError("Primary GPT does not start at LBA zero")
            if role=="backup" and end!=capacity:raise FlashError("Backup GPT does not end at disk boundary")
            regions.append((role,start,end,data))
        def locate(lba,offset,size):
            if not 0<=offset<sector or size<0:raise FlashError("Invalid GPT patch address")
            for role,start,end,data in regions:
                at=(lba-start)*sector+offset
                if start<=lba<end and 0<=at<=len(data) and at+size<=len(data):
                    return data,at
            raise FlashError("Patch outside supplied GPT regions")
        for manifest in package["manifests"]:
            for patch in manifest["patches"]:
                if patch["physical_partition_number"]!=lun or patch["target"]!="DISK":continue
                # Only actual disk GPT patches are replayed. The corresponding
                # file patches describe the same vendor update, not a second write.
                start=scalar(patch["start_sector"],capacity)
                size=patch["size_in_bytes"]
                if size not in {1,2,4,8}:raise FlashError("Unsupported GPT patch width")
                dest,at=locate(start,patch["byte_offset"],size)
                value=patch["value"]
                m=re.fullmatch(r"CRC32\(([^,]+),\s*(\d+)\)",value,re.I)
                if m:
                    count=int(m.group(2))
                    buf,off=locate(scalar(m.group(1),capacity),0,count)
                    val=zlib.crc32(buf[off:off+count])
                else:val=scalar(value,capacity)
                if not 0<=val<1<<(8*size):raise FlashError("GPT patch value exceeds field")
                dest[at:at+size]=val.to_bytes(size,"little")
        layouts={}
        for role,start,end,data in regions:
            header=1 if role=="primary" else len(data)//sector-1
            layouts[role]=_gpt(bytes(data),sector,start,header)
            if layouts[role]["disk_sectors"]!=capacity:raise FlashError("Patched GPT capacity mismatch")
        if layouts["primary"]!=layouts["backup"]:raise FlashError("Patched vendor GPT copies disagree")
        result[lun]={"layout":layouts["primary"],"sector_size":sector,
                     "regions":{role:{"start":start,"end":end,"bytes":len(data)} for role,start,end,data in regions}}
    return result

def compare(current,target):
    before=current["rows"];after=target["rows"]
    return {"added":sorted(set(after)-set(before)),"removed":sorted(set(before)-set(after)),
            "changed":[{"name":name,"before":before[name],"after":after[name]}
                       for name in sorted(set(before)&set(after)) if before[name]!=after[name]],
            "same_layout":before==after}

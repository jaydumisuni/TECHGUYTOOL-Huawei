"""Native QDL v2.9.1 staged CAZ-AL10 recovery.

The package/geometry profile is the physically observed 64 GB B387->B077
route. New Windows transport uses the upstream QUD backend and skip-reset.
Physical validation on Windows is still outstanding; no live I/O in tests.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json
import os
import re
import shutil
import struct
import subprocess
import uuid
import zlib
import xml.etree.ElementTree as ET

from .firmware_flash import FlashError, _digest
from .qualcomm_board import xml_root
from .qdl_runtime import QDL_FILES, resolve_qdl, _run, _device as qdl_device
from .caz_al10_recovery import board_preview, BOARD_EXCLUDED, matches_target, RECIPE

SECTORS=122142720
BEFORE_LAYOUT="add8600f1c621cfa9c84769cb339c6f88d58b8cc08fa8aa60f757c280a0526bc"
AFTER_LAYOUT="d0c544b24c2cd8617348d24895fa844d001eac2f8339ae1d04ddfa3b95c365bd"
BACKUP_NAMES=("sbl1","rpm","tz","devcfg","aboot","cmnlib","cmnlib64","keymaster",
 "sbl1bak","rpmbak","tzbak","devcfgbak","abootbak","cmnlibbak","cmnlib64bak",
 "keymasterbak","oeminfo","fsg","modemst1","modemst2","fsc","ssd","sec","nff",
 "misc","boot","recovery","erecovery","devinfo","persist","keystore","config",
 "syscfg","mcfg","lksecapp","lksecappbak","rrecord","patch","bootfail_info","version")
LOADER="prog_emmc_firehose.mbn"
PATCH="patch0.xml"


def _device(qdl:Path,folder:Path)->str:
    return qdl_device(qdl,folder,runner=_run)

def _layout(raw:bytes,base:int,header_index:int)->dict[str,list[int]]:
    if len(raw)%512 or header_index<0 or (header_index+1)*512>len(raw):
        raise FlashError("Invalid GPT read size.")
    h=raw[header_index*512:(header_index+1)*512]
    if h[:8]!=b"EFI PART":
        raise FlashError("GPT signature absent.")
    length,crc=struct.unpack_from("<II",h,12)
    if not 92<=length<=512:
        raise FlashError("Invalid GPT header length.")
    z=bytearray(h[:length]); z[16:20]=b"\0"*4
    if zlib.crc32(z)!=crc:
        raise FlashError("GPT header CRC mismatch.")
    this,alternate,first,last=struct.unpack_from("<QQQQ",h,24)
    if this!=base+header_index or {this,alternate}!={1,SECTORS-1} or not 34<=first<=last<=SECTORS-34:
        raise FlashError("GPT capacity or usable geometry differs from the demonstrated 64 GB target.")
    lba,count,size,entries_crc=struct.unpack_from("<QIII",h,72)
    offset=(lba-base)*512
    if not 1<=count<=128 or size!=128 or offset<0 or offset+count*size>len(raw):
        raise FlashError("GPT entries exceed the captured range.")
    a=raw[offset:offset+count*size]
    if zlib.crc32(a)!=entries_crc:
        raise FlashError("GPT entry CRC mismatch.")
    rows={}
    for i in range(count):
        x=a[i*size:(i+1)*size]
        if not any(x[:16]):continue
        start,end=struct.unpack_from("<QQ",x,32)
        name=x[56:128].decode("utf-16le").rstrip("\0")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",name) or name in rows or not first<=start<=end<=last:
            raise FlashError("Invalid GPT partition geometry.")
        rows[name]=[start,end]
    ordered=sorted(rows.values())
    if any(a[1]>=b[0] for a,b in zip(ordered,ordered[1:])):
        raise FlashError("Overlapping GPT partitions.")
    return rows


def _layout_digest(rows):
    return sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _filtered(source:Path,dest:Path):
    root=xml_root(source)
    for node in list(root):
        if not node.get("filename") or node.get("label","").casefold() in BOARD_EXCLUDED:
            root.remove(node)
    if len(root)!=150:
        raise FlashError("Unexpected filtered factory write count.")
    ET.ElementTree(root).write(dest,encoding="utf-8",xml_declaration=True)
    return [node.get("label") for node in root]


def _acks(output:str,expected:list[str]):
    rows=re.findall(r'flashed "([^"]+)" successfully',output)
    return rows==expected and bool(re.search(r"\b13 patches applied\b",output)) and bool(re.search(r"\bflashed 150 partitions\b",output)) and bool(re.search(r"\bpartition 0 is now bootable\b",output))


def _args(folder,serial):
    return ["--color=never","--backend=qud","--serial="+serial,"--storage=emmc","--skip-reset","--include="+str(folder),str(folder/LOADER)]


def board_plan(project:Path,rawprogram:Path,model:str,chipset:str,evidence:Path)->dict:
    if not matches_target(model,chipset):
        raise FlashError("Select CAZ-AL10 / MSM8953.")
    rawprogram=rawprogram.resolve()
    result=board_preview(rawprogram)
    qdl=resolve_qdl(project)
    from .edl_reconnect import ensure
    serial=ensure(lambda:_device(qdl,rawprogram.parent),stage="board preflight")
    evidence.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(evidence).free<1024**3:
        raise FlashError("At least 1 GiB free is required for board backup and readback.")
    # QDL v2.9.1 no-device dry-run, exact filtered plan and vendor patches.
    job=evidence/("board-plan-"+uuid.uuid4().hex)
    job.mkdir()
    filtered=job/"rawprogram.xml"
    expected=_filtered(rawprogram,filtered)
    code,log=_run(qdl,["--color=never","--dry-run","--storage=emmc",
        "--include="+str(rawprogram.parent),str(rawprogram.parent/LOADER),
        str(filtered),str(rawprogram.parent/PATCH)],rawprogram.parent,180)
    (job/"dry-run.log").write_text(log,encoding="utf8")
    if code or not _acks(log,expected):
        raise FlashError("QDL factory plan dry-run did not reproduce all 150 operations and 13 patches.")
    result.update({"qdl_available":True,"qdl_sha256":QDL_FILES["qdl.exe"],
        "source_path":str(rawprogram),"serial_hash":sha256(serial.encode()).hexdigest(),
        "userdata_replaced":True,"board_recovery":True,
        "qualification":"NATIVE_WINDOWS_ADAPTER_SOFTWARE_READY_PHYSICAL_PENDING",
        "no_reboot":False,"dry_run":"PASS"})
    result["fingerprint"]=sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


def board_apply(project:Path,rawprogram:Path,model:str,chipset:str,fingerprint:str,
                evidence:Path,progress)->dict:
    rawprogram=rawprogram.resolve()
    current=board_plan(project,rawprogram,model,chipset,evidence)
    if not fingerprint or current["fingerprint"]!=fingerprint:
        raise FlashError("Board plan or target changed; verify again.")
    folder=rawprogram.parent
    qdl=resolve_qdl(project)
    from .edl_reconnect import ensure, run_stage
    serial=ensure(lambda:_device(qdl,folder),expected_hash=current["serial_hash"],stage="board recovery")
    if sha256(serial.encode()).hexdigest()!=current["serial_hash"]:
        raise FlashError("EDL serial changed.")
    job=evidence/("board-run-"+uuid.uuid4().hex)
    job.mkdir()
    backup=job/"backup"; backup.mkdir()
    after=job/"readback"; after.mkdir()
    report={"recipe":RECIPE,"fingerprint":fingerprint,"status":"RUNNING",
        "backup":{},"readback":{},"program_acknowledged":False,"boot_verified":False}
    def save():
        p=job/"receipt.tmp"; p.write_text(json.dumps(report,indent=2),encoding="utf8");p.replace(job/"receipt.json")
    def run(name,args,timeout=180,debug=False):
        code,out=run_stage(lambda:_device(qdl,folder),serial,name,args,
            lambda:_run(qdl,(["--debug"] if debug else [])+_args(folder,serial)+args,folder,timeout),
            lambda attempt,log:(job/(name+("" if attempt==1 else "-retry-"+str(attempt))+".log")).write_text(log,encoding="utf8"))
        if code or re.search(r"(?m)^ERR:",out):
            raise FlashError("QDL stopped at "+name+"; evidence retained.")
        return out
    def read_args(root,ranges):
        args=[]
        for name,(start,end) in ranges.items():
            args += ["read",f"0/{start}+{end-start+1}",str(root/(name+".bin"))]
        return args
    def validate_files(root,ranges):
        hashes={}
        for name,(start,end) in ranges.items():
            p=root/(name+".bin")
            if not p.is_file() or p.stat().st_size!=(end-start+1)*512:
                raise FlashError("Incomplete physical read: "+name)
            hashes[name]=_digest(p)
        return hashes
    save()
    try:
        progress("Reading live eMMC GPT and chipset evidence")
        primary={"gpt-primary":[0,33]}
        out=run("gpt-before",read_args(backup,primary),debug=True)
        # XML Firehose target is an independently observed fact, not model
        # identity; operator selects exact model and GPT profile is checked.
        if not re.search(r'TargetName\s*=\s*["\x27]?(?:MSM)?8953\b',out,re.I):
            raise FlashError("Firehose did not report the observed MSM8953 target.")
        rows=_layout((backup/"gpt-primary.bin").read_bytes(),0,1)
        if _layout_digest(rows)!=BEFORE_LAYOUT:
            raise FlashError("Current GPT is outside the physically proven B387 64 GB recovery profile.")
        ranges={name:rows[name] for name in BACKUP_NAMES}
        ranges["gpt-backup"]=[SECTORS-33,SECTORS-1]
        if shutil.disk_usage(job).free<sum((b-a+1)*512 for a,b in ranges.values())+400*1024**2:
            raise FlashError("Insufficient backup/readback capacity.")
        progress("Backing up 41 device regions")
        run("backup",read_args(backup,ranges),timeout=600)
        report["backup"]=validate_files(backup,{**primary,**ranges})
        backup_rows=_layout((backup/"gpt-backup.bin").read_bytes(),SECTORS-33,32)
        # The recovered handset really had B387 primary (61 entries) and
        # B077/B175 backup (54 entries), both CRC-valid. This precise mixed
        # geometry is a qualified input observation, not arbitrary corruption.
        backup_layout=_layout_digest(backup_rows)
        if backup_layout not in {BEFORE_LAYOUT,AFTER_LAYOUT}:
            raise FlashError("Backup GPT is outside both known layouts.")
        report["pre_gpt"]={"primary_layout":_layout_digest(rows),
                           "backup_layout":backup_layout,
                           "copies_agree":rows==backup_rows}
        save()
        filtered=job/"rawprogram-preserve.xml"
        expected=_filtered(rawprogram,filtered)
        # Same device, complete hashes, no reuse of a historical handset backup.
        if validate_files(backup,{**primary,**ranges})!=report["backup"]:
            raise FlashError("Backup content changed.")
        progress("Programming factory firmware and GPT")
        out=run("program",[str(filtered),str(folder/PATCH)],timeout=7200)
        if not _acks(out,expected):
            raise FlashError("Not all 150 writes and 13 patches were acknowledged.")
        report["program_acknowledged"]=True;save()
        progress("Reading back GPT and boot/recovery before reset")
        after_ranges={**primary,"gpt-backup":[SECTORS-33,SECTORS-1],
                      **{name:rows[name] for name in ("boot","recovery",*sorted(BOARD_EXCLUDED))}}
        run("readback",read_args(after,after_ranges),timeout=600)
        report["readback"]=validate_files(after,after_ranges)
        newrows=_layout((after/"gpt-primary.bin").read_bytes(),0,1)
        if _layout_digest(newrows)!=AFTER_LAYOUT or _layout((after/"gpt-backup.bin").read_bytes(),SECTORS-33,32)!=newrows:
            raise FlashError("Restored GPT does not match B077 geometry.")
        for name in ("boot","recovery"):
            img=folder/(name+".img")
            if _digest(after/(name+".bin"),size=img.stat().st_size)!=_digest(img):
                raise FlashError("Board image readback mismatch: "+name)
        if any(report["readback"][name]!=report["backup"][name] for name in BOARD_EXCLUDED):
            raise FlashError("Excluded device-unique region changed before reset.")
        report["status"]="BOARD_READBACK_VERIFIED";save()
        progress("Returning board to normal boot")
        run("reset",["reset"],timeout=60)
        report["status"]="BOARD_RESET_ACKNOWLEDGED";report["reset_acknowledged"]=True;save()
    except Exception as exc:
        report["error"]=str(exc);report["status"]="STOPPED_ON_ERROR";save();raise
    return {"status":report["status"],"evidence_path":str(job/"receipt.json"),
            "completed":150,"backup_regions":len(report["backup"]),
            "readback_verified":True,"boot_verified":False,"no_reboot":False,
            "next_stage":"Confirm board Android boot, then enter Fastboot and select Repair with B175 UPDATE.APP."}

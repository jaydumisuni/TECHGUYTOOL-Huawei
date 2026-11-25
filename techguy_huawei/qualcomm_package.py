"""Package-driven Qualcomm recovery planning and same-layout programming.

The vendor package supplies the programmer, storage family, XML and images.
No model allowlist or fixed partition count. Existing-layout repair preserves
GPT, device-unique and user-data partitions. Repartitioning remains a separate
recipe because matching image names alone cannot prove new geometry safe.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import struct
import uuid
import zlib
import xml.etree.ElementTree as ET

from .firmware_flash import FlashError, _digest, _model, _chipset
from .qualcomm_board import build_plan, xml_root, BoardPlanError, UNIQUE_DATA, safe_member
from .qdl_runtime import resolve_qdl, _run, _device

SCHEMA="techguy.huawei.qualcomm-package.v2"
PROTECTED=set(UNIQUE_DATA)|{"userdata","cache","metadata","nvme","modem_secure","nvm","nvram","nvdata","factory","protect1","protect2","carrier","devcfg_sec","misc","gpt","primarygpt","backupgpt","partition","partitiontable","ptable","xbl_config_sec"}

def _protected(label):
    name=re.sub(r"_(?:a|b)$","",label.casefold())
    return name in PROTECTED or name.startswith(("gpt","modemst","modemnvm","oeminfo","persist","frp","secure_storage","secdata","nvram","nvdata"))

def _hash_obj(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def discover(rawprogram:Path):
    rawprogram=rawprogram.resolve()
    folder=rawprogram.parent
    if not rawprogram.is_file() or rawprogram.suffix.casefold()!=".xml":
        raise FlashError("Select a vendor rawprogram XML.")
    try:
        if xml_root(rawprogram).tag!="data":
            raise FlashError("Not a Qualcomm rawprogram manifest.")
        loaders=sorted(p for p in folder.iterdir() if p.is_file() and not p.is_symlink()
                      and re.search(r"firehose",p.name,re.I)
                      and not re.search(r"crc|digest|sig(?:nature)?",p.stem,re.I)
                      and p.suffix.lower() in {".mbn",".elf",".bin"})
        # Prefer no candidate by filename similarity alone. Explicit selection
        # uses the operator's package directory containing its intended loader.
        if len(loaders)!=1:
            raise FlashError("Expected one intended Firehose programmer in this package; found: "+", ".join(x.name for x in loaders))
        loader=loaders[0]
        stores=[x for x in ("emmc","ufs") if x in loader.stem.lower()]
        if len(stores)!=1:
            raise FlashError("Programmer does not declare eMMC or UFS in its filename; select a storage-specific package.")
        storage=stores[0]
        # Collect numbered groups from the selected naming family. Plain and
        # unsparse variants are alternative package sets, not additive groups.
        m=re.fullmatch(r"rawprogram(\d+)(_unsparse)?\.xml",rawprogram.name,re.I)
        if m:
            suffix=m.group(2) or ""
            pattern=re.compile(r"rawprogram(\d+)"+re.escape(suffix)+r"\.xml",re.I)
            found=[(int(match.group(1)),p) for p in folder.iterdir()
                   if p.is_file() and (match:=pattern.fullmatch(p.name))]
            groups=sorted(found,key=lambda pair:pair[0])
            if len({i for i,_ in groups})!=len(groups):
                raise FlashError("Duplicate numbered rawprogram group.")
        else:
            groups=[(None,rawprogram)]
        manifests=[]
        for index,group in groups:
            patch=folder/("patch"+str(index if index is not None else 0)+".xml")
            if not patch.is_file():
                choices=sorted(folder.glob("patch*.xml"))
                if index is None and len(choices)==1:patch=choices[0]
                elif index is None and len(choices)>1:raise FlashError("Matching patch XML is ambiguous.")
                else:patch=None
            manifests.append(build_plan(folder,group.name,patch.name if patch else "",loader.name))
        all_operations=[op for manifest in manifests for op in manifest["operations"]]
        selected=[op for op in all_operations if op["filename"] and not _protected(op["label"])]
        if not selected:raise FlashError("No non-protected firmware image operations.")
        # Keep the historical single-manifest API for the reference package;
        # combined operations/patches are the authoritative multi-group set.
        return {"schema":SCHEMA,"folder":str(folder),"program":rawprogram.name,
                "programs":[x["program"] for x in manifests],
                "patch":manifests[0]["patch"],"patches":[x["patch"] for x in manifests if x["patch"]],
                "programmer":loader.name,"storage":storage,
                "manifest":manifests[0],"manifests":manifests,
                "all_operations":all_operations,"operations":selected,
                "excluded":sorted({op["label"] for op in all_operations if not op["filename"] or _protected(op["label"])}),
                "scope":"existing_layout_repair_no_gpt_patches"}
    except (BoardPlanError,OSError) as exc:
        raise FlashError(str(exc)) from exc

def filtered(package:dict,path:Path):
    root=ET.Element("data")
    for name in package["programs"]:
        source=xml_root(Path(package["folder"])/name)
        for node in source:
            if node.get("filename") and not _protected(node.get("label","")):
                root.append(node)
    if len(root)!=len(package["operations"]):raise FlashError("Filtered package count changed.")
    ET.ElementTree(root).write(path,encoding="utf-8",xml_declaration=True)


def _acks(output,operations):
    expected=[op["label"] for op in operations]
    found=re.findall(r'flashed "([^"]+)" successfully',output)
    return found==expected and bool(re.search(r"\bflashed "+str(len(expected))+r" partitions?\b",output))

def _gpt(raw:bytes,sector:int,base:int,header:int):
    """Read and check GPT with no fixed capacity or model-specific geometry."""
    if sector not in (512,4096) or len(raw)%sector or (header+1)*sector>len(raw):
        raise FlashError("Invalid GPT capture geometry.")
    h=raw[header*sector:(header+1)*sector]
    if h[:8]!=b"EFI PART":raise FlashError("GPT signature missing.")
    length,crc=struct.unpack_from("<II",h,12)
    if not 92<=length<=sector:raise FlashError("GPT header size invalid.")
    hh=bytearray(h[:length]);hh[16:20]=b"\0"*4
    if zlib.crc32(hh)!=crc:raise FlashError("GPT header CRC mismatch.")
    current,alternate,first,last=struct.unpack_from("<QQQQ",h,24)
    disk=max(current,alternate)+1
    if current!=base+header or min(current,alternate)!=1 or not 2<=first<=last<disk-1:
        raise FlashError("GPT capacity/usable range invalid.")
    lba,n,size,crc=struct.unpack_from("<QIII",h,72)
    offset=(lba-base)*sector
    if not 1<=n<=1024 or size<128 or size>1024 or size%8 or offset<0 or offset+n*size>len(raw):
        raise FlashError("GPT entries outside bounded capture.")
    entries=raw[offset:offset+n*size]
    if zlib.crc32(entries)!=crc:raise FlashError("GPT array CRC mismatch.")
    rows={}
    for i in range(n):
        item=entries[i*size:(i+1)*size]
        if not any(item[:16]):continue
        name=item[56:128].decode("utf-16le").rstrip("\0").casefold()
        start,end=struct.unpack_from("<QQ",item,32)
        if not re.fullmatch(r"[a-z0-9_.-]+",name) or name in rows or not first<=start<=end<=last:
            raise FlashError("Invalid GPT partition entry.")
        rows[name]=(start,end)
    intervals=sorted(rows.values())
    if any(a[1]>=b[0] for a,b in zip(intervals,intervals[1:])):
        raise FlashError("Overlapping live GPT partitions.")
    return {"disk_sectors":disk,"rows":rows,"array_sectors":(n*size+sector-1)//sector}

def _geometry(package,layouts):
    occupied={}
    for op in package["operations"]:
        lun=op["physical_partition_number"];label=op["label"].casefold()
        start=op["start_sector"];count=op["sectors"]
        if type(start)!=int or count<=0:raise FlashError("Unknown live sector expression for "+label)
        layout=layouts[lun];span=layout["rows"].get(label)
        end=start+count-1
        if not span or not span[0]<=start<=end<=span[1]:
            raise FlashError("Package range does not fit live partition "+label+"; repartitioning requires a matching recovery recipe.")
        intervals=occupied.setdefault(lun,[])
        if any(a<=end and start<=b for a,b in intervals):
            raise FlashError("Overlapping package writes in LUN "+str(lun))
        intervals.append((start,end))

def plan(project:Path,rawprogram:Path,model:str,chipset:str,evidence:Path):
    target=_model(model)
    chip=_chipset(chipset)
    package=discover(rawprogram)
    result={"schema":SCHEMA,"recipe":"qualcomm.package.same-layout",
        "model":target,"chipset":chip,"mode":"Board Firmware",
        "source_path":str(rawprogram.resolve()),"package":package,
        "partitions":[{"partition":op["label"],**op} for op in package["operations"]],
        "excluded":package["excluded"],"preflight_only":True,"write_authorized":False,
        "board_recovery":True,"same_layout":True,"userdata_replaced":False,"no_reboot":True,
        "gpt_patches_deferred":True}
    try:qdl=resolve_qdl(project)
    except FlashError as exc:
        result["device_status"]=str(exc);return result
    folder=Path(package["folder"])
    evidence.mkdir(parents=True,exist_ok=True)
    job=evidence/("qualcomm-plan-"+uuid.uuid4().hex);job.mkdir()
    xml=job/"program.xml";filtered(package,xml)
    code,log=_run(qdl,["--color=never","--dry-run","--storage="+package["storage"],
        "--include="+str(folder),str(folder/package["programmer"]),str(xml)],folder,180)
    (job/"dry-run.log").write_text(log,encoding="utf8")
    if code or not _acks(log,package["operations"]):
        raise FlashError("QDL package dry-run did not acknowledge all selected images.")
    result["dry_run"]="PASS"
    try:serial=_device(qdl,folder)
    except FlashError as exc:
        result["device_status"]=str(exc);return result
    result["serial_hash"]=sha256(serial.encode()).hexdigest()
    result["fingerprint"]=_hash_obj(result)
    return result

def _chip_matches(output,chip):
    # Exact reported Firehose TargetName with only canonical Qualcomm prefix
    # normalization. Unknown/alias silicon is not inferred from USB VID/PID.
    values=re.findall(r'TargetName\s*=\s*["\x27]?([A-Za-z0-9_]+)',output,re.I)
    def norm(x):return re.sub(r"^(?:msm|sdm|sm|apq|qcm|qcs)","",x.casefold())
    return bool(values) and any(norm(v)==norm(chip) for v in values)

def _check_image(op,package,readback:Path):
    """Compare raw image contents or sparse RAW/FILL chunks, streaming only."""
    image=Path(package["folder"])/op["filename"]
    sector=op["sector_size"];offset=op["file_sector_offset"]*sector
    with image.open("rb") as src,readback.open("rb") as actual:
        src.seek(offset)
        def compare(size,pattern=None):
            while size:
                n=min(size,1024*1024)
                wanted=src.read(n) if pattern is None else (pattern*((n+3)//4))[:n]
                if len(wanted)!=n or actual.read(n)!=wanted:
                    raise FlashError("Readback mismatch: "+op["label"])
                size-=n
        if op["sparse"]!="true":
            compare(image.stat().st_size-offset);return
        if offset:raise FlashError("Sparse input with nonzero file offset is not qualified.")
        header=src.read(28)
        if len(header)!=28:raise FlashError("Sparse header truncated.")
        magic,major,minor,fh,ch,bs,blocks,chunks,checksum=struct.unpack("<IHHHHIIII",header)
        if magic!=0xed26ff3a or major!=1 or fh<28 or ch<12 or bs<4 or bs%4 or bs*blocks>op["sectors"]*sector or chunks>1000000:
            raise FlashError("Sparse geometry invalid.")
        src.seek(fh);done=0
        for _ in range(chunks):
            chunk=src.read(ch)
            if len(chunk)!=ch:raise FlashError("Sparse chunk truncated.")
            kind,_,count,total=struct.unpack("<HHII",chunk[:12]);length=count*bs
            if kind==0xcac1 and total==ch+length:compare(length);done+=count
            elif kind==0xcac2 and total==ch+4:
                pattern=src.read(4)
                if len(pattern)!=4:raise FlashError("Sparse fill missing.")
                compare(length,pattern);done+=count
            elif kind==0xcac3 and total==ch:actual.seek(length,1);done+=count
            elif kind==0xcac4 and count==0 and total==ch+4:
                if len(src.read(4))!=4:raise FlashError("Sparse CRC missing.")
            else:raise FlashError("Unsupported sparse chunk.")
            if done>blocks:raise FlashError("Sparse expanded size overflow.")
        if done!=blocks or src.tell()!=image.stat().st_size:raise FlashError("Sparse file length mismatch.")

def apply(project:Path,rawprogram:Path,model:str,chipset:str,fingerprint:str,evidence:Path,progress):
    current=plan(project,rawprogram,model,chipset,evidence)
    if not fingerprint or current.get("fingerprint")!=fingerprint:raise FlashError("Board package or device changed; verify again.")
    package=current["package"];folder=Path(package["folder"]);qdl=resolve_qdl(project)
    serial=_device(qdl,folder)
    if sha256(serial.encode()).hexdigest()!=current["serial_hash"]:raise FlashError("EDL target changed.")
    job=evidence/("qualcomm-run-"+uuid.uuid4().hex);job.mkdir()
    report={"schema":SCHEMA,"fingerprint":fingerprint,"status":"RUNNING",
            "backup":[],"readback":[],"completed":0,"boot_verified":False,"no_reboot":True}
    def save():
        tmp=job/"receipt.tmp";tmp.write_text(json.dumps(report,indent=2),encoding="utf8");tmp.replace(job/"receipt.json")
    def run(name,args,timeout=600,debug=False):
        if _device(qdl,folder)!=serial:raise FlashError("EDL target detached or changed.")
        argv=(["--debug"] if debug else [])+["--color=never","--backend=qud","--serial="+serial,
            "--storage="+package["storage"],"--skip-reset","--include="+str(folder),str(folder/package["programmer"]),*args]
        code,log=_run(qdl,argv,folder,timeout)
        (job/(name+".log")).write_text(log,encoding="utf8")
        if code:raise FlashError("QDL stopped at "+name)
        return log
    def read(name,lun,start,count,sector,dest,debug=False):
        log=run(name,["read",f"{lun}/{start}+{count}",str(dest)],7200,debug)
        if not dest.is_file() or dest.stat().st_size!=count*sector:raise FlashError("Physical read length mismatch: "+name)
        return log
    save()
    try:
        layouts={}
        sectors={}
        for op in package["operations"]:
            lun=op["physical_partition_number"];sector=op["sector_size"]
            if lun in sectors and sectors[lun]!=sector:raise FlashError("Mixed sector sizes in one LUN.")
            sectors[lun]=sector
        for lun,sector in sectors.items():
            # 34 sectors cover ordinary GPT and are bounded; unusual larger
            # tables are rejected, not guessed.
            primary=job/f"gpt-{lun}-primary.bin"
            log=read(f"gpt-{lun}-primary",lun,0,34,sector,primary,True)
            if not _chip_matches(log,current["chipset"]):raise FlashError("Live Firehose TargetName does not match selected chipset.")
            layout=_gpt(primary.read_bytes(),sector,0,1)
            n=layout["array_sectors"]+1
            backup=job/f"gpt-{lun}-backup.bin"
            start=layout["disk_sectors"]-n
            read(f"gpt-{lun}-backup",lun,start,n,sector,backup)
            if _gpt(backup.read_bytes(),sector,start,n-1)!=layout:raise FlashError("Primary and backup GPT disagree; use an explicit repartitioning recovery recipe.")
            layouts[lun]=layout
        _geometry(package,layouts)
        # A firmware package can contain a target GPT with a different layout.
        # We do not ignore such a mismatch. Compare supplied primary GPT when
        # its actual file format contains a complete standard GPT.
        for op in package["all_operations"]:
            if not op["filename"] or op["label"].casefold() not in {"primarygpt","gpt_main","gpt"}:continue
            lun=op["physical_partition_number"];sector=op["sector_size"]
            if lun not in layouts:continue
            f=Path(package["folder"])/op["filename"]
            if f.stat().st_size>1024*1024:raise FlashError("Unrecognized package GPT image size.")
            target=_gpt(f.read_bytes(),sector,0,1)
            if target["rows"]!=layouts[lun]["rows"]:raise FlashError("Package requests a different GPT layout; use explicit repartitioning recipe.")
        ops=package["operations"]
        total=sum(op["sectors"]*op["sector_size"] for op in ops)
        peak=max(op["sectors"]*op["sector_size"] for op in ops)
        if shutil.disk_usage(job).free<total+peak+64*1024**2:
            raise FlashError("Actual repair backup/readback needs additional destination storage; firmware itself is not copied.")
        progress("Backing up selected live write ranges")
        for i,op in enumerate(ops):
            dest=job/f"backup-{i:05d}.bin"
            read(f"backup-{i:05d}",op["physical_partition_number"],op["start_sector"],op["sectors"],op["sector_size"],dest)
            report["backup"].append({"label":op["label"],"file":dest.name,"sha256":_digest(dest),"bytes":dest.stat().st_size})
            save()
        # Rehash backup and package immediately before the write.
        if any(_digest(job/x["file"])!=x["sha256"] for x in report["backup"]):raise FlashError("Backup changed.")
        if discover(rawprogram)!=package:raise FlashError("Package changed during backup.")
        xml=job/"program.xml";filtered(package,xml)
        progress("Programming package-selected firmware")
        log=run("program",[str(xml)],7200)
        if not _acks(log,ops):raise FlashError("Incomplete QDL programming acknowledgments.")
        report["completed"]=len(ops);save()
        for i,op in enumerate(ops):
            dest=job/f"readback-{i:05d}.bin"
            read(f"readback-{i:05d}",op["physical_partition_number"],op["start_sector"],op["sectors"],op["sector_size"],dest)
            _check_image(op,package,dest)
            report["readback"].append({"label":op["label"],"sha256":_digest(dest),"verified":True})
            save();dest.unlink()
        report["status"]="WRITES_READBACK_VERIFIED_NO_RESET"
    except Exception as exc:
        report["status"]="STOPPED_ON_ERROR";report["error"]=str(exc);save();raise
    save()
    return {"status":report["status"],"completed":report["completed"],
            "readback_verified":True,"boot_verified":False,"no_reboot":True,
            "evidence_path":str(job/"receipt.json")}

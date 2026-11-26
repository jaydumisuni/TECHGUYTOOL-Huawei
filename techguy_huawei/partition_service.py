"""Local authorized Fastboot partition backup and repair.
No model allowlist; the live partition geometry and device identity bind each job.
"""
from pathlib import Path
import hashlib,json,re,shutil,uuid,struct
from datetime import datetime,timezone
from . import firmware_flash as f

SCHEMA="techguy.huawei.partition-backup.v1"
def _hash(value):return hashlib.sha256(value.encode()).hexdigest()
def _partition(name):
    if not f.PARTITION_NAME.fullmatch(name):raise f.FlashError("Invalid partition name")
    if not re.fullmatch(r"(?:cache|boot|recovery|recovery_ramdisk|erecovery_ramdisk|ramdisk|kernel|system|vendor|product|cust|odm|super|dtbo|vbmeta|vendor_boot|init_boot)(?:_[ab])?",name):
        raise f.FlashError("Use the applicable dedicated service function for this partition")
    return name
def _target(binary,serial,model,chip,part):
    if not serial or not model or not chip:raise f.FlashError("Read the connected device first")
    actual,product,reported=f._device(binary,chip,model)
    if actual!=serial or reported!=model.upper():raise f.FlashError("Device identity changed or not fully reported")
    code,out=f._exec(binary,["-s",serial,"getvar","partition-size:"+part])
    m=re.search(r"partition-size:"+re.escape(part)+r"\s*:\s*(0x[0-9a-f]+|[0-9]+)",out,re.I)
    if code or not m or "FAILED" in out.upper():raise f.FlashError("Live partition size unavailable")
    size=int(m.group(1),0)
    if not 0<size<=f.MAX_PAYLOAD:raise f.FlashError("Invalid partition size")
    return size
def _save(path,data):
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(data,indent=2),encoding="utf8");tmp.replace(path)
def backup(binary,serial,model,chip,part,dest,progress):
    part=_partition(part);size=_target(binary,serial,model,chip,part)
    root=Path(dest).resolve()
    if not root.is_dir():raise f.FlashError("Select an existing backup directory")
    if shutil.disk_usage(root).free<size+1024**2:raise f.FlashError("Insufficient backup storage")
    job=root/("partition-"+part+"-"+uuid.uuid4().hex);job.mkdir()
    img=job/"partition.img";partial=job/"partition.partial"
    progress("Reading "+part+" from the connected device")
    code,out=f._exec(binary,["-s",serial,"fetch",part,str(partial)],timeout=7200)
    if code or "FAILED" in out.upper() or not partial.is_file() or partial.stat().st_size!=size:raise f.FlashError("Partition fetch incomplete or unsupported in current mode; partial retained")
    if f._unique_device(binary)!=serial:raise f.FlashError("Device changed during backup")
    sha=f._digest(partial);partial.replace(img)
    receipt={"schema":SCHEMA,"model":model.upper(),"chipset":chip,"serial_sha256":_hash(serial),
        "partition":part,"size":size,"sha256":sha,"file":img.name,
        "created":datetime.now(timezone.utc).isoformat()}
    path=job/"backup.json";_save(path,receipt)
    return {"backup_path":str(path),"partition":part,"size":size,"sha256":sha}
def _backup_source(manifest,serial,model,chip,part,size):
    p=Path(manifest).resolve()
    if p.stat().st_size>65536:raise f.FlashError("Invalid backup receipt")
    d=json.loads(p.read_text(encoding="utf8"))
    if (d.get("schema")!=SCHEMA or d.get("serial_sha256")!=_hash(serial) or
        d.get("model")!=model.upper() or f.canonical_chipset(d.get("chipset",""))!=f.canonical_chipset(chip) or
        d.get("partition")!=part or d.get("size")!=size or d.get("file")!="partition.img"):
        raise f.FlashError("Backup does not match connected device and partition")
    image=p.parent/"partition.img"
    if image.is_symlink() or not image.is_file() or image.stat().st_size!=size or f._digest(image)!=d.get("sha256"):
        raise f.FlashError("Backup integrity mismatch")
    return image
def prepare(binary,serial,model,chip,part,source,restore=False):
    part=_partition(part);size=_target(binary,serial,model,chip,part)
    path=Path(source).resolve()
    image=_backup_source(path,serial,model,chip,part,size) if restore else path
    if not image.is_file() or image.is_symlink() or not 0<image.stat().st_size<=size:raise f.FlashError("Image does not fit live partition")
    # Raw complete partition images can be verified byte for byte. Firmware
    # sparse images remain in the existing package-driven firmware worker.
    with image.open("rb") as fh:
        if fh.read(4)==b"\x3a\xff\x26\xed":raise f.FlashError("Use Firmware Flash for sparse firmware images")
    plan={"model":model.upper(),"chipset":chip,"serial_sha256":_hash(serial),"partition":part,
        "source":str(path),"image":str(image),"size":size,"image_size":image.stat().st_size,
        "sha256":f._digest(image),"restore":restore}
    plan["fingerprint"]=_hash(json.dumps(plan,sort_keys=True))
    return plan
def apply(binary,serial,model,chip,part,source,restore,fingerprint,evidence,progress):
    p=prepare(binary,serial,model,chip,part,source,restore)
    if not fingerprint or p["fingerprint"]!=fingerprint:raise f.FlashError("Partition plan changed; confirm again")
    root=Path(evidence);root.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(root).free<2*p["size"]+1024**2:raise f.FlashError("Insufficient backup/readback storage")
    before=backup(binary,serial,model,chip,part,root,progress)
    if prepare(binary,serial,model,chip,part,source,restore)!=p:raise f.FlashError("Device or image changed after backup")
    job=Path(before["backup_path"]).parent;receipt=job/"write-receipt.json"
    result={"status":"RUNNING","plan":p,"backup":before,"no_reboot":True};_save(receipt,result)
    try:
        progress("Writing "+part)
        code,out=f._exec(binary,["-s",serial,"-S","256M","flash",part,p["image"]],timeout=7200)
        if not f.acknowledged(part,code,out):raise f.FlashError("Write was not acknowledged")
        progress("Verifying "+part+" readback")
        if _target(binary,serial,model,chip,part)!=p["size"]:raise f.FlashError("Partition geometry changed")
        dest=job/"readback.partial"
        code,out=f._exec(binary,["-s",serial,"fetch",part,str(dest)],timeout=7200)
        if code or "FAILED" in out.upper() or not dest.is_file() or dest.stat().st_size!=p["size"] or f._digest(dest,size=p["image_size"])!=p["sha256"]:
            raise f.FlashError("Partition readback verification failed")
        if f._unique_device(binary)!=serial:raise f.FlashError("Device changed during readback")
        result.update(status="READBACK_VERIFIED",readback_verified=True);_save(receipt,result);dest.unlink()
    except Exception as exc:
        result.update(status="STOPPED_ON_ERROR",error=str(exc));_save(receipt,result);raise
    return {"partition":part,"backup_path":before["backup_path"],"evidence_path":str(receipt),"readback_verified":True,"no_reboot":True}

def prepare_erase(binary,serial,model,chip,part):
    part=_partition(part)
    size=_target(binary,serial,model,chip,part)
    plan={"operation":"erase","model":model.upper(),"chipset":chip,"serial_sha256":_hash(serial),
          "partition":part,"size":size,"no_reboot":True}
    plan["fingerprint"]=_hash(json.dumps(plan,sort_keys=True))
    return plan

def apply_erase(binary,serial,model,chip,part,fingerprint,evidence,progress):
    plan=prepare_erase(binary,serial,model,chip,part)
    if not fingerprint or plan["fingerprint"]!=fingerprint:
        raise f.FlashError("Erase plan changed; confirm again")
    root=Path(evidence);root.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(root).free<2*plan["size"]+1024**2:
        raise f.FlashError("Insufficient backup/readback storage")
    before=backup(binary,serial,model,chip,part,root,progress)
    if prepare_erase(binary,serial,model,chip,part)!=plan:
        raise f.FlashError("Device or geometry changed after backup")
    job=Path(before["backup_path"]).parent;receipt=job/"erase-receipt.json"
    result={"status":"RUNNING","plan":plan,"backup":before,"no_reboot":True}
    _save(receipt,result)
    try:
        progress("Erasing selected ordinary repair partition "+part)
        code,out=f._exec(binary,["-s",serial,"erase",part],timeout=7200)
        if code or "FAILED" in out.upper() or not re.search(r"Erasing\s+'"+re.escape(part)+r"'\s+OKAY",out,re.I):
            raise f.FlashError("Erase was not acknowledged")
        result["erase_acknowledged"]=True
        _save(receipt,result)
        if _target(binary,serial,model,chip,part)!=plan["size"]:
            raise f.FlashError("Partition geometry changed")
        dest=job/"erase-readback.partial"
        code,out=f._exec(binary,["-s",serial,"fetch",part,str(dest)],timeout=7200)
        if code or "FAILED" in out.upper() or not dest.is_file() or dest.stat().st_size!=plan["size"]:
            raise f.FlashError("Erase acknowledged but readback unavailable")
        if f._unique_device(binary)!=serial:raise f.FlashError("Device changed during readback")
        fill=None;uniform=True
        with dest.open("rb") as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b""):
                if fill is None:fill=chunk[0]
                if fill not in (0,255) or chunk!=bytes([fill])*len(chunk):
                    uniform=False;break
        result.update(status="READBACK_VERIFIED" if uniform else "ERASE_ACK_READBACK_INCONCLUSIVE",
                      readback_verified=uniform,readback_sha256=f._digest(dest))
        _save(receipt,result)
        if uniform:dest.unlink()
    except Exception as exc:
        result.update(status="STOPPED_ON_ERROR",error=str(exc));_save(receipt,result);raise
    return {"partition":part,"backup_path":before["backup_path"],"evidence_path":str(receipt),
            "erase_acknowledged":True,"readback_verified":uniform,"no_reboot":True}

"""Vendor package reconstruction helpers for the existing QDL worker.

No device model whitelist: actual target geometry comes from supplied GPT
templates and bounded patch expressions. The caller owns confirmation,
transport and evidence. This module is also usable entirely offline.
"""
from __future__ import annotations
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from .firmware_flash import FlashError
from .qualcomm_board import xml_root
from .qualcomm_layout import templates,preview,compare,scalar,gpt_label

def operations(package):
    from .qualcomm_package import _protected
    return [op for op in package["all_operations"] if op["filename"] and
            (gpt_label(op["label"]) or not _protected(op["label"]))]

def program_xml(package,destination):
    from .qualcomm_package import _protected
    root=ET.Element("data")
    for name in package["programs"]:
        for node in xml_root(Path(package["folder"])/name):
            if node.get("filename") and (gpt_label(node.get("label","")) or not _protected(node.get("label",""))):
                root.append(node)
    ET.ElementTree(root).write(destination,encoding="utf-8",xml_declaration=True)

def patch_xml(package,destination):
    pairs=templates(package)
    root=ET.Element("patches")
    count=0
    for name in package["patches"]:
        for node in xml_root(Path(package["folder"])/name):
            if node.get("filename")!="DISK":continue
            if int(node.get("physical_partition_number","-1")) not in pairs:
                raise FlashError("Disk patch has no paired vendor GPT templates")
            root.append(node);count+=1
    ET.ElementTree(root).write(destination,encoding="utf-8",xml_declaration=True)
    return count

def validate(package,primary,secondary):
    """Both observed GPTs may disagree, but all protected regions must survive."""
    from .qualcomm_package import _protected,_geometry
    pairs=templates(package)
    if not pairs:raise FlashError("No vendor GPT reconstruction templates")
    if set(primary)!=set(secondary):raise FlashError("Incomplete live GPT inventory")
    targets=preview(package,{lun:row["disk_sectors"] for lun,row in primary.items()})
    target_layouts=dict(primary)
    for lun,target in targets.items():
        target_layouts[lun]=target["layout"]
    # Non-GPT LUNs must retain their current consistent layout.
    for lun,layout in primary.items():
        other=secondary[lun]
        if layout["disk_sectors"]!=other["disk_sectors"]:
            raise FlashError("Live GPT copies disagree on capacity")
        if lun not in targets and layout!=other:
            raise FlashError("Inconsistent GPT on a LUN without reconstruction templates")
        new=target_layouts[lun]["rows"]
        for old in (layout["rows"],other["rows"]):
            for label,span in old.items():
                # Data volumes are excluded from writing, but a factory layout
                # may change their geometry. The UI warns of loss of access.
                base=re.sub(r"_(?:a|b)$","",label)
                if _protected(label) and base not in {"userdata","cache","metadata","misc"}:
                    if new.get(label)!=span:
                        raise FlashError("Vendor layout would move or remove a protected region: "+label)
    _geometry(package,target_layouts)
    ops=operations(package)
    ranges=[]
    for op in ops:
        lun=op["physical_partition_number"]
        layout=target_layouts.get(lun)
        if layout is None:raise FlashError("No observed storage LUN for "+op["label"])
        start=scalar(op["start_sector"],layout["disk_sectors"]);end=start+op["sectors"]-1
        if start<0 or end>=layout["disk_sectors"]:raise FlashError("Program range outside disk")
        if gpt_label(op["label"]):
            if lun not in targets:raise FlashError("GPT image has no validated target")
        else:
            # Existing and target protected ranges may not be overwritten
            # by an apparently unrelated image name.
            for source in (primary[lun],secondary[lun],layout):
                for label,(a,b) in source["rows"].items():
                    base=re.sub(r"_(?:a|b)$","",label)
                    if _protected(label) and base not in {"userdata","cache","metadata","misc"} and a<=end and start<=b:
                        raise FlashError("Firmware range overlaps protected region: "+label)
        for other_lun,a,b in ranges:
            if other_lun==lun and a<=end and start<=b:raise FlashError("Overlapping reconstruction program ranges")
        ranges.append((lun,start,end))
    return {"targets":targets,"layouts":target_layouts,"ranges":ranges,
            "delta":{str(lun):{"primary":compare(primary[lun],target["layout"]),
                               "backup":compare(secondary[lun],target["layout"])}
                     for lun,target in targets.items()}}

def execute(project,rawprogram,current,evidence,progress):
    """Execute an explicitly confirmed reconstruction plan through QDL."""
    from hashlib import sha256
    import json,shutil,uuid
    from . import qualcomm_package as q
    from .firmware_flash import _digest
    package=current["package"]
    folder=Path(package["folder"])
    qdl=q.resolve_qdl(project)
    serial=q._device(qdl,folder)
    if sha256(serial.encode()).hexdigest()!=current["serial_hash"]:
        raise FlashError("EDL target changed")
    job=evidence/("reconstruction-"+uuid.uuid4().hex);job.mkdir()
    report={"status":"RUNNING","fingerprint":current["fingerprint"],"backup":[],
            "readback":[],"completed":0,"boot_verified":False,"no_reboot":True}
    def save():
        tmp=job/"receipt.tmp";tmp.write_text(json.dumps(report,indent=2),encoding="utf8");tmp.replace(job/"receipt.json")
    def run(name,args,timeout=7200):
        if q._device(qdl,folder)!=serial:raise FlashError("EDL target detached or changed")
        argv=["--color=never","--backend=qud","--serial="+serial,
            "--storage="+package["storage"],"--skip-reset","--include="+str(folder),
            str(folder/package["programmer"]),*args]
        code,log=q._run(qdl,argv,folder,timeout)
        (job/(name+".log")).write_text(log,encoding="utf8")
        if code or re.search(r"(?m)^ERR:",log):raise FlashError("QDL stopped at "+name)
        return log
    def read(name,op,start,count,dest):
        run(name,["read",f"{op['physical_partition_number']}/{start}+{count}",str(dest)])
        if not dest.is_file() or dest.stat().st_size!=count*op["sector_size"]:
            raise FlashError("Incomplete physical read: "+name)
    save()
    try:
        progress("Rechecking confirmed live and vendor GPT layouts")
        primary,secondary,hashes=q._live_layouts(package,qdl,serial,job,current["chipset"])
        if hashes!=current["pre_gpt_hashes"]:raise FlashError("Live GPT changed after confirmation")
        check=validate(package,primary,secondary)
        if check["delta"]!=current["layout_delta"]:raise FlashError("Layout preview changed after confirmation")
        report["layout_delta"]=check["delta"];save()
        ops=operations(package);ranges=check["ranges"]
        total=sum(op["sectors"]*op["sector_size"] for op in ops)
        peak=max(op["sectors"]*op["sector_size"] for op in ops)
        if shutil.disk_usage(job).free<total+peak+64*1024**2:
            raise FlashError("Additional storage required for physical recovery backup/readback; firmware is used in place")
        progress("Backing up the actual reconstruction ranges")
        for i,(op,(_,start,end)) in enumerate(zip(ops,ranges)):
            dest=job/f"backup-{i:05d}.bin"
            read(f"backup-{i:05d}",op,start,end-start+1,dest)
            report["backup"].append({"label":op["label"],"file":dest.name,"sha256":_digest(dest),"bytes":dest.stat().st_size})
            save()
        if any(_digest(job/x["file"])!=x["sha256"] for x in report["backup"]):
            raise FlashError("Physical backup changed")
        if q.discover(rawprogram)!=package:raise FlashError("Firmware package changed during backup")
        xml=job/"program.xml";program_xml(package,xml)
        patch=job/"patch.xml";count=patch_xml(package,patch)
        progress("Programming confirmed vendor board layout and firmware")
        log=run("program",[str(xml),*([str(patch)] if count else [])])
        if not q._acks(log,ops) or (count and not re.search(r"\b"+str(count)+r" patches applied\b",log)):
            raise FlashError("Incomplete programming or patch acknowledgments")
        report["completed"]=len(ops);report["patches"]=count;save()
        progress("Verifying both restored GPT copies")
        afterdir=job/"post-gpt";afterdir.mkdir()
        post,post_backup,_=q._live_layouts(package,qdl,serial,afterdir,current["chipset"])
        if post!=check["layouts"] or post_backup!=check["layouts"]:
            raise FlashError("Restored GPT differs from vendor preview")
        report["gpt_verified"]=True;save()
        for i,(op,(_,start,end)) in enumerate(zip(ops,ranges)):
            if gpt_label(op["label"]):continue
            dest=job/f"readback-{i:05d}.bin"
            read(f"readback-{i:05d}",op,start,end-start+1,dest)
            q._check_image(op,package,dest)
            report["readback"].append({"label":op["label"],"sha256":_digest(dest),"verified":True})
            save();dest.unlink()
        report["status"]="RECONSTRUCTION_READBACK_VERIFIED_NO_RESET"
    except Exception as exc:
        report["status"]="STOPPED_ON_ERROR";report["error"]=str(exc);save();raise
    save()
    return {"status":report["status"],"completed":report["completed"],
            "gpt_verified":True,"readback_verified":True,"boot_verified":False,
            "no_reboot":True,"evidence_path":str(job/"receipt.json")}

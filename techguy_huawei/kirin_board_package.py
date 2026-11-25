"""Inspect vendor Kirin Download.xml without assuming a model or chipset.

The existing authorized Fastboot worker handles ordinary firmware images.
Factory service entry, CRC commands, erases and boot-chain reconstruction
are distinct vendor-specific procedures, not ordinary partition flashes.
"""
from __future__ import annotations
from pathlib import Path
import re
from .qualcomm_board import xml_root
from .firmware_flash import (FlashError,FlashOperation,_digest,_source_relative,
                             _protected_partition,PARTITION_NAME,_model,_chipset)
from .fastboot_identity import canonical_chipset

def inspect(path:Path,model="",chipset=""):
    path=path.resolve()
    root=xml_root(path)
    if root.tag!="configurations":
        raise FlashError("Not a Huawei vendor Download.xml")
    configurations=root.findall("configuration")
    if len(configurations)!=1:
        raise FlashError("Select a package with one explicit vendor configuration")
    config=configurations[0]
    chip=_chipset(config.get("ap_platform",""))
    version=config.get("version","").strip()
    family=config.get("product_id","").strip().upper()
    m=re.match(r"^([A-Z]{2,6}-[A-Z0-9]{2,12})(?:[- ]|$)",version,re.I)
    target=m.group(1).upper() if m else ""
    if not family or not target or target.split("-")[0]!=family:
        raise FlashError("Vendor package does not declare an exact target model")
    if model and _model(model)!=target:
        raise FlashError("Selected model differs from vendor package target")
    if chipset and canonical_chipset(chipset)!=canonical_chipset(chip):
        raise FlashError("Selected chipset differs from vendor package target")
    if not canonical_chipset(chip).startswith(("kirin","hisi")):
        raise FlashError("Not a HiSilicon vendor configuration")
    stages=[]
    operations=[]
    excluded=[]
    for section in config:
        for row in section:
            if row.tag!="image":continue
            part=row.get("identifier","").casefold()
            name=row.get("name","") or part
            source=(row.text or "").strip()
            if not source:
                excluded.append({"section":section.tag,"name":name,"reason":"no file-backed firmware image"})
                continue
            relative=source.replace("\\","/")
            candidate=(path.parent/relative).resolve()
            if Path(relative).is_absolute() or re.match(r"^[A-Za-z]:",relative) or path.parent not in candidate.parents:
                raise FlashError("Firmware source escapes package folder")
            if not candidate.is_file():
                # The real vendor package references an optional DDR test image
                # not included in the archive. Record absence; selected repair
                # images still fail closed if missing.
                if section.tag=="bootloaderimage_ddr":
                    excluded.append({"section":section.tag,"name":name,"reason":"optional DDR test image absent"})
                    continue
                raise FlashError("Missing firmware image: "+relative)
            file=_source_relative(path.parent,relative)
            if (path.parent/relative).is_symlink():raise FlashError("Unsafe firmware image")
            item={"section":section.tag,"name":name,"partition":part,
                  "file":source,"size":file.stat().st_size,"sha256":_digest(file)}
            stages.append(item)
            if section.tag!="fastbootimage" or part=="huawei_crc_check" or _protected_partition(part) or not PARTITION_NAME.fullmatch(part):
                excluded.append({"section":section.tag,"name":name,"reason":"separate vendor service procedure"})
                continue
            # Restrict ordinary repair to standard Android firmware partitions;
            # vendor service-only partitions may require special commands.
            if not re.fullmatch(r"(?:boot|recovery|recovery_ramdisk|erecovery_ramdisk|ramdisk|kernel|system|vendor|product|cust|odm|super|dtbo|vbmeta|vendor_boot|init_boot)(?:_[ab])?",part):
                excluded.append({"section":section.tag,"name":name,"reason":"not a standard repair partition"})
                continue
            operations.append(FlashOperation(part,str(file),None,0,item["size"],item["sha256"]))
    if len({o.partition for o in operations})!=len(operations):
        raise FlashError("Duplicate ordinary repair partition; package requires explicit image mapping")
    return {"model":target,"chipset":chip,"version":version,"package_sha256":_digest(path),
            "stages":stages,"excluded":excluded,"operations":operations}

"""Huawei Qualcomm factory-package planning and QDL qualification.

The factory package is data, not an authorization to program the connected device.
This module separates package validation and transport dry-run from hardware proof.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any
import argparse
import json
import re
import subprocess
import xml.etree.ElementTree as ET

SCHEMA = "techguy.huawei.qualcomm-board-plan.v1"
UNIQUE_DATA = frozenset({
    "oeminfo", "persist", "modemst1", "modemst2", "fsg", "fsc", "sec",
    "devinfo", "keystore", "config", "ssd", "frp",
})
BOOT_CHAIN = frozenset({
    "sbl1", "sbl1bak", "aboot", "abootbak", "rpm", "rpmbak",
    "tz", "tzbak", "keymaster", "keymasterbak", "devcfg", "devcfgbak",
    "cmnlib", "cmnlibbak", "cmnlib64", "cmnlib64bak", "lksecapp",
    "lksecappbak", "primarygpt", "backupgpt",
})
DATA = frozenset({"userdata", "cache"})
EXPRESSION = re.compile(r"NUM_DISK_SECTORS-[0-9]+\.?")
MAX_XML_BYTES = 8 * 1024 * 1024


class BoardPlanError(ValueError):
    pass


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_member(root: Path, name: str) -> Path:
    if (not name or "\\" in name or ":" in name
            or len(PurePosixPath(name).parts) != 1
            or name in {".", ".."}):
        raise BoardPlanError("Invalid firmware member: " + name)
    path = root / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != root.resolve():
        raise BoardPlanError("Missing or unsafe firmware member: " + name)
    return path


def xml_root(path: Path) -> ET.Element:
    if not path.is_file() or path.stat().st_size > MAX_XML_BYTES:
        raise BoardPlanError("Invalid XML size or path")
    raw = path.read_bytes()
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)", raw, re.I):
        raise BoardPlanError("DTD and entity declarations are not accepted")
    try:
        return ET.fromstring(raw)
    except (ET.ParseError, ValueError, LookupError) as exc:
        raise BoardPlanError("Invalid XML: " + path.name) from exc


def number(node: ET.Element, key: str) -> int:
    value = node.get(key, "")
    if not re.fullmatch(r"[0-9]+", value):
        raise BoardPlanError("Invalid integer " + key)
    return int(value)


def location(node: ET.Element, key: str) -> int | str:
    value = node.get(key, "")
    if re.fullmatch(r"[0-9]+", value):
        return int(value)
    if EXPRESSION.fullmatch(value):
        return value
    raise BoardPlanError("Unsupported sector expression: " + value)


def partition_class(label: str) -> str:
    name = label.casefold()
    if name in UNIQUE_DATA:
        return "device_unique"
    if name in BOOT_CHAIN:
        return "boot_chain"
    if name in DATA:
        return "user_data"
    return "firmware"


def build_plan(folder: Path, program: str, patch: str, programmer: str) -> dict[str, Any]:
    folder = folder.resolve()
    program_file = safe_member(folder, program)
    patch_file = safe_member(folder, patch)
    loader = safe_member(folder, programmer)
    with loader.open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            raise BoardPlanError("This factory route requires an ELF programmer")
    root = xml_root(program_file)
    patches = xml_root(patch_file)
    if root.tag != "data" or patches.tag != "patches":
        raise BoardPlanError("Unexpected rawprogram or patch root")
    files: dict[str, Any] = {}
    operations: list[dict[str, Any]] = []
    for node in root:
        if node.tag != "program":
            raise BoardPlanError("Unsupported rawprogram directive " + node.tag)
        name = node.get("filename", "")
        label = node.get("label", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
            raise BoardPlanError("Missing or invalid partition label")
        sector_size = number(node, "SECTOR_SIZE_IN_BYTES")
        if sector_size not in {512, 4096}:
            raise BoardPlanError("Unsupported sector size")
        count = number(node, "num_partition_sectors")
        offset = number(node, "file_sector_offset")
        row = {
            "label": label, "filename": name, "sector_size": sector_size,
            "sectors": count, "file_sector_offset": offset,
            "start_sector": location(node, "start_sector"),
            "physical_partition_number": number(node, "physical_partition_number"),
            "sparse": node.get("sparse", "false"), "classification": partition_class(label),
            "operation": "program" if name else "empty_filename",
        }
        if row["sparse"] not in {"true", "false"}:
            raise BoardPlanError("Invalid sparse flag")
        if name:
            path = safe_member(folder, name)
            if name not in files:
                files[name] = {"size": path.stat().st_size, "sha256": digest(path)}
            size = files[name]["size"]
            if count <= 0 or size <= offset * sector_size:
                raise BoardPlanError("Invalid image geometry for " + name)
            # The factory allocation can exceed an unpadded MBN image.
            # Sparse images have an independent expanded size; delegate to QDL.
            if row["sparse"] == "false" and size - offset * sector_size > count * sector_size:
                raise BoardPlanError("Image exceeds declared sector allocation: " + name)
        operations.append(row)
    if not operations or not files:
        raise BoardPlanError("Empty programming plan")
    patch_rows = []
    for node in patches:
        if node.tag != "patch":
            raise BoardPlanError("Unsupported patch directive " + node.tag)
        target = node.get("filename", "")
        if target != "DISK":
            safe_member(folder, target)
        patch_rows.append({
            "target": target, "start_sector": location(node, "start_sector"),
            "byte_offset": number(node, "byte_offset"),
            "size_in_bytes": number(node, "size_in_bytes"),
            "physical_partition_number": number(node, "physical_partition_number"),
            "value": node.get("value", ""), "description": node.get("what", ""),
        })
    plan = {
        "schema": SCHEMA, "programmer": programmer, "program": program, "patch": patch,
        "manifest_hashes": {p.name: digest(p) for p in (loader, program_file, patch_file)},
        "files": files, "operations": operations, "patches": patch_rows,
        "summary": {
            "program_entries": len(operations),
            "file_backed_entries": sum(row["operation"] == "program" for row in operations),
            "empty_entries": sum(row["operation"] == "empty_filename" for row in operations),
            "image_files": len(files), "patch_entries": len(patch_rows),
            "write_classes": dict(Counter(row["classification"] for row in operations
                                           if row["operation"] == "program")),
            "unique_partitions": sorted({row["label"] for row in operations
                                         if row["operation"] == "program"
                                         and row["classification"] == "device_unique"}),
        },
    }
    plan["fingerprint"] = sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return plan


def dry_run(qdl: Path, folder: Path, plan: dict[str, Any], storage: str = "emmc",
            *, timeout: int = 120) -> dict[str, Any]:
    """Run the upstream tool's documented no-device-I/O mode, on exact files."""
    if storage not in {"emmc", "ufs"}:
        raise BoardPlanError("Unsupported storage")
    if not qdl.is_file():
        raise BoardPlanError("QDL executable is missing")
    current = build_plan(folder, plan["program"], plan["patch"], plan["programmer"])
    if current != plan:
        raise BoardPlanError("Package changed after plan creation")
    argv = [str(qdl.resolve()), "--dry-run", "--storage=" + storage,
            plan["programmer"], plan["program"], plan["patch"]]
    proc = subprocess.run(argv, cwd=folder, capture_output=True, text=True,
                          errors="replace", timeout=timeout, check=False, shell=False)
    log = proc.stdout + "\n" + proc.stderr
    return {"schema": "techguy.huawei.qdl-dry-run.v1", "plan": plan["fingerprint"],
            "qdl_sha256": digest(qdl), "returncode": proc.returncode,
            "dry_run": True, "hardware_verified": False, "log": log,
            "status": "PASS" if proc.returncode == 0 and
            "dry-run execution" in log.lower() else "FAIL"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--program", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--programmer", required=True)
    parser.add_argument("--qdl", type=Path)
    parser.add_argument("--storage", choices=("emmc", "ufs"), default="emmc")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = build_plan(args.folder, args.program, args.patch, args.programmer)
    result = {"plan": plan}
    if args.qdl:
        result["qualification"] = dry_run(args.qdl, args.folder, plan, args.storage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(plan["summary"], indent=2))
    return 0 if result.get("qualification", {}).get("status", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

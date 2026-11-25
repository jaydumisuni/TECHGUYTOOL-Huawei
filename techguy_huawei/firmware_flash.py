from __future__ import annotations

"""Package-driven Huawei Fastboot flashing.

No model, chipset, device serial, or firmware partition layout is hardcoded.
A package is inspected, bound to the live transport, and fingerprinted before
a separately confirmed write. Never performs erase/reboot/unlock/OEMINFO writes.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable
import json
import os
import re
import struct
import subprocess
import tempfile
import time
import uuid

from .fastboot_identity import model_from_build, lock_state, canonical_chipset, acknowledged

MAGIC = bytes.fromhex("55aa5aa5")
SCHEMA = "techguy.huawei.fastboot-package.v1"
HARD_BLOCK = frozenset({
    "oeminfo", "nvme", "persist", "modem_secure", "modemnvm_factory",
    "modemnvm_backup", "modemnvm_img", "modemnvm_update", "modemnvm_cust",
    "userdata", "frp", "certification", "secure_storage", "ptable",
    "xloader", "xloader_a", "xloader_b", "ufs_fw", "fastboot", "fastboot_a",
    "bootloader", "hisiufs_gpt", "gpt", "hdcp", "cache",
})
METADATA = frozenset({
    "CRC", "SHA256RSA", "BASE_VER", "BASE_VERLIST", "CUST_VER",
    "CUST_VERLIST", "PRELOAD_VER", "PRELOAD_VERLIST", "PACKAGE_TYPE",
    "PTABLE_CUST", "PTABLE_PRELOAD",
})
# A firmware may use completely different partition names. The actual
# operation mapping comes from its package or its explicit manifest.
PARTITION_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}\Z")
CHIPSET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}\Z")
MAX_PAYLOAD = 32 * 1024 ** 3


class FlashError(ValueError):
    pass


@dataclass(frozen=True)
class FlashOperation:
    partition: str
    source: str
    entry_index: int | None
    data_offset: int
    size: int
    sha256: str
    risk: str = "system"


@dataclass(frozen=True)
class FlashPlan:
    model: str
    chipset: str
    mode: str
    source_path: str
    serial_hash: str
    device_product: str
    device_reported_model: str
    operations: tuple[FlashOperation, ...]
    excluded: tuple[str, ...]
    fingerprint: str
    no_reboot: bool = True


def _digest(path: Path, *, offset: int = 0, size: int | None = None) -> str:
    h = sha256()
    with path.open("rb") as f:
        f.seek(offset)
        left = path.stat().st_size - offset if size is None else size
        if left < 0:
            raise FlashError("Invalid artifact offset")
        while left:
            b = f.read(min(8 * 1024 ** 2, left))
            if not b:
                raise FlashError("Firmware source ended unexpectedly")
            h.update(b)
            left -= len(b)
    return h.hexdigest()


def _exec(fastboot: str, args: list[str], timeout: int = 12) -> tuple[int, str]:
    p = subprocess.run([fastboot, *args], check=False, shell=False,
                       capture_output=True, text=True, timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return p.returncode, (p.stdout + "\n" + p.stderr).strip()


def _unique_device(fastboot: str) -> str:
    code, out = _exec(fastboot, ["devices"])
    matches = [m.group(1) for line in out.splitlines()
               if (m := re.fullmatch(r"\s*(\S+)\s+fastboot\s*", line, re.I))]
    if code or len(matches) != 1:
        raise FlashError("Exactly one responding Fastboot device is required")
    return matches[0]


def _device(fastboot: str, expected_chipset: str, expected_model: str) -> tuple[str, str, str]:
    serial = _unique_device(fastboot)
    code, lock = _exec(fastboot, ["-s", serial, "oem", "get-bootinfo"])
    if code or lock_state(lock) != "unlocked":
        raise FlashError("The selected Fastboot device has not proven unlocked")
    code, text = _exec(fastboot, ["-s", serial, "getvar", "product"])
    match = re.search(r"\bproduct:\s*([a-z0-9_.-]+)", text, re.I)
    if code or not match or "FAILED" in text.upper():
        raise FlashError("Could not verify chipset identity from Fastboot")
    product = match.group(1)
    if canonical_chipset(product) != canonical_chipset(expected_chipset):
        raise FlashError("Selected firmware chipset does not match live Fastboot chipset")
    code, build = _exec(fastboot, ["-s", serial, "oem", "get-build-number"])
    current = model_from_build(build) if code == 0 else ""
    if current and current != expected_model.upper():
        # AL00 -> L29 within the same hardware family is a deliberate
        # conversion, but never silently assume two model families are one.
        if current.split("-", 1)[0] != expected_model.upper().split("-", 1)[0]:
            raise FlashError("Connected handset model family differs from the selected target")
    return serial, product, current


def _app_entries(app: Path) -> list[tuple[str, int, int, int]]:
    if app.stat().st_size < 194:
        raise FlashError("Invalid UPDATE.APP (too small)")
    size = app.stat().st_size
    result = []
    with app.open("rb") as f:
        if f.read(92) != bytes(92):
            raise FlashError("Invalid UPDATE.APP prefix")
        position = 92
        while position + 102 <= size:
            f.seek(position)
            probe = f.read(102)
            if probe[:4] != MAGIC:
                # Huawei package records may carry padding.
                position += 1
                continue
            header = struct.unpack_from("<I", probe, 4)[0]
            length = struct.unpack_from("<I", probe, 24)[0]
            if not 98 <= header <= 64 * 1024 ** 2 or not 0 < length <= MAX_PAYLOAD:
                raise FlashError("Invalid UPDATE.APP entry header")
            data = position + header
            if data + length > size:
                raise FlashError("UPDATE.APP entry exceeds package size")
            name = probe[60:92].split(b"\0", 1)[0].decode("ascii", "strict").upper()
            result.append((name, len(result) + 1, data, length))
            position = data + length
    if not result:
        raise FlashError("UPDATE.APP contains no parseable entries")
    return result


def _model(text: str) -> str:
    value = text.strip().upper()
    if not MODEL_NAME.fullmatch(value):
        raise FlashError("Select a valid target model (e.g. ELE-L29)")
    return value


def _chipset(text: str) -> str:
    value = text.strip().lower().replace(" ", "")
    if not CHIPSET_NAME.fullmatch(value):
        raise FlashError("Select a valid chipset (e.g. kirin980)")
    return value


def _protected_partition(name: str) -> bool:
    base = re.sub(r"_(?:a|b)$", "", name.casefold())
    return (base in HARD_BLOCK or base.startswith(
        ("modemnvm", "userdata", "oeminfo", "nvme", "persist", "frp",
         "secure_storage", "modem_secure", "xloader", "ptable", "gpt",
         "fastboot", "bootloader")
    ))


def _source_relative(folder: Path, name: str) -> Path:
    if Path(name).is_absolute() or re.match(r"^[A-Za-z]:", name):
        raise FlashError("Firmware manifest source must be relative to its own folder")
    candidate = (folder / name).resolve()
    if candidate != folder.resolve() and folder.resolve() not in candidate.parents:
        raise FlashError("Firmware source escapes package folder")
    if not candidate.is_file():
        raise FlashError("Missing firmware image: " + name)
    return candidate


def _load_selection(
    path: Path, model: str, chipset: str, mode: str,
) -> tuple[str, str, list[FlashOperation], list[str]]:
    if path.suffix.lower()==".xml" and mode=="Repair":
        from .kirin_board_package import inspect
        vendor=inspect(path,model,chipset)
        if not vendor["operations"]:
            raise FlashError("No ordinary repair images in vendor package")
        return vendor["model"],vendor["chipset"],vendor["operations"],[
            x["section"]+":"+x["name"] for x in vendor["excluded"]]
    if mode == "Downgrade":
        raise FlashError("Downgrade is unavailable without verified anti-rollback compatibility")
    if mode not in {"Upgrade", "Full Flash", "Repair"}:
        raise FlashError("This execution engine supports system firmware, not board/unlock procedures")
    excluded: list[str] = []
    operations: list[FlashOperation] = []
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != SCHEMA:
            raise FlashError("Not a TECHGUY fastboot package manifest")
        manifest_model = _model(payload.get("model", ""))
        manifest_chipset = _chipset(payload.get("chipset", ""))
        if model and _model(model) != manifest_model:
            raise FlashError("Selected model does not match firmware manifest")
        if chipset and _chipset(chipset) != manifest_chipset:
            raise FlashError("Selected chipset does not match firmware manifest")
        model, chipset = manifest_model, manifest_chipset
        for raw in payload.get("operations", []):
            partition = str(raw.get("partition", "")).casefold().strip()
            if not PARTITION_NAME.fullmatch(partition):
                raise FlashError("Invalid partition identifier in manifest")
            if _protected_partition(partition):
                raise FlashError("Protected partition prohibited from generic firmware mode: " + partition)
            image = _source_relative(path.parent, str(raw.get("file", "")))
            index = raw.get("index")
            if index is None:
                off, length = 0, image.stat().st_size
            else:
                choices = [a for a in _app_entries(image) if a[1] == index]
                if len(choices) != 1 or choices[0][0] != raw.get("name", "").upper():
                    raise FlashError("UPDATE.APP entry index/name mismatch")
                _, _, off, length = choices[0]
            expected = str(raw.get("sha256", "")).lower()
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise FlashError("Missing SHA256 fingerprint for " + partition)
            if int(raw.get("size", length)) != length:
                raise FlashError("Manifest payload size mismatch")
            digest = _digest(image, offset=off, size=length)
            if digest != expected:
                raise FlashError("Package SHA256 mismatch for " + partition)
            operations.append(FlashOperation(partition, str(image), index, off, length, digest))
    elif path.name.upper() == "UPDATE.APP":
        if not model or not chipset:
            raise FlashError("UPDATE.APP needs selected model and chipset when no signed profile manifest is provided")
        model, chipset = _model(model), _chipset(chipset)
        entries = _app_entries(path)
        counts = {}
        for name, _, _, _ in entries:
            counts[name] = counts.get(name, 0) + 1
        for name, index, off, length in entries:
            partition = name.lower()
            if name in METADATA or _protected_partition(partition):
                excluded.append(name)
                continue
            if not PARTITION_NAME.fullmatch(partition):
                excluded.append(name)
                continue
            if counts[name] != 1:
                # e.g. VOG's SUPER is split into two payloads. A verified
                # merged image must be supplied through an explicit manifest.
                raise FlashError("Multi-entry partition requires a verified merged image: " + name)
            digest = _digest(path, offset=off, size=length)
            operations.append(FlashOperation(partition, str(path), index, off, length, digest))
    else:
        raise FlashError("Choose a verified fastboot package .json or an extracted UPDATE.APP")
    if not operations:
        raise FlashError("Firmware source has no writable system partitions")
    if len(operations) > 128:
        raise FlashError("Too many firmware operations")
    if len({o.partition for o in operations}) != len(operations):
        raise FlashError("Duplicate partition operations")
    return model, chipset, operations, excluded


def plan(
    package: str, model: str, chipset: str, mode: str, fastboot: str,
) -> FlashPlan:
    source = Path(package).expanduser().resolve()
    if not source.is_file() or source.stat().st_size == 0:
        raise FlashError("Choose a valid firmware package")
    explicitly_selected_model = bool(model.strip())
    # For standalone UPDATE.APP, retrieve missing values from the actual
    # connected device. A service loader may report the chip but hide model;
    # in that case the operator must select the exact model.
    if source.name.upper() == "UPDATE.APP" and (not model.strip() or not chipset.strip()):
        serial = _unique_device(fastboot)
        if not chipset.strip():
            code, response = _exec(fastboot, ["-s", serial, "getvar", "product"])
            found = re.search(r"\bproduct:\s*([A-Za-z0-9_.-]+)", response)
            if code or not found or "FAILED" in response.upper():
                raise FlashError("Chipset detection unavailable; select a verified chipset")
            chipset = found.group(1)
        if not model.strip():
            code, response = _exec(fastboot, ["-s", serial, "oem", "get-build-number"])
            found = model_from_build(response) if code == 0 else ""
            if not found:
                raise FlashError("Model detection unavailable; select the exact model manually")
            model = found
            explicitly_selected_model = True
    target_model, target_chipset, ops, excluded = _load_selection(
        source, model, chipset, mode
    )
    serial, actual_chipset, actual_model = _device(fastboot, target_chipset, target_model)
    if source.suffix.lower()==".xml":
        if actual_model!=target_model:
            raise FlashError("Vendor repair requires matching live model identity")
        for op in ops:
            code,reply=_exec(fastboot,["-s",serial,"getvar","partition-size:"+op.partition])
            m=re.search(r"partition-size:"+re.escape(op.partition)+r"\s*:\s*(0x[0-9a-f]+)",reply,re.I)
            if code or not m or "FAILED" in reply.upper():
                raise FlashError("Device did not report partition geometry: "+op.partition)
            cap=int(m.group(1),16)
            with Path(op.source).open("rb") as image:
                header=image.read(28)
            expanded=op.size
            if len(header)==28 and header[:4]==b"\x3a\xff\x26\xed":
                expanded=struct.unpack_from("<I",header,12)[0]*struct.unpack_from("<I",header,16)[0]
            if not 0<expanded<=cap:
                raise FlashError("Vendor image exceeds live partition: "+op.partition)

    if not explicitly_selected_model and not actual_model:
        raise FlashError("Fastboot cannot identify the model; select the exact target model manually")
    # Directory naming is not package authentication: matching is based on
    # explicit model selection or live model detection and verified payloads.
    data = {
        "source": str(source), "model": target_model, "chipset": actual_chipset,
        "mode": mode, "serial_hash": sha256(serial.encode()).hexdigest(),
        "operations": [asdict(x) for x in ops], "excluded": sorted(excluded),
    }
    fingerprint = sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    return FlashPlan(target_model, actual_chipset, mode, str(source),
                     data["serial_hash"][:12], actual_chipset, actual_model,
                     tuple(ops), tuple(sorted(excluded)), fingerprint)


def apply(
    package: str, model: str, chipset: str, mode: str, fastboot: str,
    expected_plan: str, evidence_dir: Path, progress: Callable[[str], None],
) -> dict:
    current = plan(package, model, chipset, mode, fastboot)
    if not expected_plan or current.fingerprint != expected_plan:
        raise FlashError("Flash plan changed; run preflight and confirm the new plan")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    serial = _unique_device(fastboot)
    if sha256(serial.encode()).hexdigest()[:12] != current.serial_hash:
        raise FlashError("Fastboot device changed")
    # No file content cleanup or reboot while writes are in progress.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = evidence_dir / f"firmware-flash-{stamp}-{uuid.uuid4().hex[:7]}.json"
    report = {"schema": "techguy.huawei.firmware-execution.v1",
              "model": current.model, "chipset": current.chipset,
              "fingerprint": current.fingerprint, "no_reboot": True,
              "status": "RUNNING", "operations": []}
    def checkpoint():
        temp = log_path.with_suffix(".tmp")
        temp.write_text(json.dumps(report,indent=2),encoding="utf8")
        temp.replace(log_path)
    checkpoint()
    try:
        for i, operation in enumerate(current.operations, 1):
            if _unique_device(fastboot) != serial:
                raise FlashError("Device detached or changed during firmware installation")
            progress(f"Flashing {i}/{len(current.operations)}: {operation.partition}")
            source = Path(operation.source)
            if _digest(source,offset=operation.data_offset,size=operation.size) != operation.sha256:
                raise FlashError("Firmware source changed since preflight")
            staging = evidence_dir / f".staging-{uuid.uuid4().hex}.img"
            if operation.data_offset or operation.size != source.stat().st_size:
                with source.open("rb") as f, staging.open("xb") as w:
                    f.seek(operation.data_offset)
                    remaining = operation.size
                    while remaining:
                        block = f.read(min(8 * 1024 ** 2, remaining))
                        if not block:
                            raise FlashError("Firmware source truncated")
                        w.write(block)
                        remaining -= len(block)
                image = staging
            else:
                image = source
            try:
                code, output = _exec(
                    fastboot, ["-s",serial,"-S","256M","flash",operation.partition,str(image)],
                    timeout=7200,
                )
            finally:
                if image == staging:
                    staging.unlink(missing_ok=True)
            verified = acknowledged(operation.partition, code, output)
            report["operations"].append({
                "partition": operation.partition,
                "sha256": operation.sha256, "size": operation.size,
                "ok": verified, "exit_code": code, "output": output[-3000:],
            })
            checkpoint()
            if not verified:
                raise FlashError("Fastboot did not acknowledge " + operation.partition)
            progress(f"Verified write {i}/{len(current.operations)}: {operation.partition}")
        report["status"] = "WRITES_COMPLETE_NO_REBOOT"
    except (OSError, subprocess.TimeoutExpired, FlashError) as exc:
        report["status"] = "STOPPED_ON_ERROR"
        report["error"] = f"{type(exc).__name__}: {exc}"
        checkpoint()
        raise
    checkpoint()
    return {"status": report["status"], "evidence_path": str(log_path),
            "completed": len(report["operations"]), "no_reboot": True}

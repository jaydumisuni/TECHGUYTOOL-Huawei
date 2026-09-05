from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Callable


class RecoveryIdentityStatus(str, Enum):
    READY = "READY"
    NEED_IDENTITY_EVIDENCE = "NEED_IDENTITY_EVIDENCE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class RecoveryIdentity:
    status: RecoveryIdentityStatus
    family: str | None
    build: str | None
    android_major: int | None
    board_id: str | None
    lock_state: str | None
    model: str | None
    region: str | None
    preload_region: str | None

    def to_public_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


def _text(result) -> str:
    return f"{getattr(result, 'stdout', '')}\n{getattr(result, 'stderr', '')}"


def _bootloader_value(text: str) -> str | None:
    for line in text.splitlines():
        match = re.search(r"\(bootloader\)\s*:?[ \t]*(.*?)\s*$", line, re.I)
        if match:
            value = match.group(1).strip()
            if value and value.upper() not in {"OKAY", "FAILED"}:
                return value
    return None


def _run_value(run: Callable, fastboot: str, serial: str, *args: str) -> str | None:
    result = run([fastboot, "-s", serial, *args], shell=False, check=False, capture_output=True, text=True)
    if getattr(result, "returncode", 1) != 0:
        return None
    return _bootloader_value(_text(result))


def resolve_fastboot_recovery_identity(run: Callable, fastboot: str, serial: str) -> RecoveryIdentity:
    build = _run_value(run, fastboot, serial, "oem", "get-build-number")
    bootinfo = _run_value(run, fastboot, serial, "oem", "get-bootinfo")
    family = None
    if build:
        match = re.match(r"([A-Z0-9]{3})-", build.upper())
        family = match.group(1) if match else None

    lock_state = None
    if bootinfo:
        upper = bootinfo.upper()
        if "UNLOCKED" in upper:
            lock_state = "UNLOCKED"
        elif "LOCKED" in upper:
            lock_state = "LOCKED"

    if family != "CLT":
        return RecoveryIdentity(
            RecoveryIdentityStatus.UNSUPPORTED, family, build, None, None, lock_state, None, None, None
        )

    android_raw = _run_value(run, fastboot, serial, "oem", "oeminforead-ANDROID_VERSION")
    board_id = _run_value(run, fastboot, serial, "oem", "oeminforead-BOARDID")
    model = _run_value(run, fastboot, serial, "oem", "get-product-model")
    region = _run_value(run, fastboot, serial, "oem", "oeminforead-CUST")
    preload = _run_value(run, fastboot, serial, "oem", "oeminforead-PRELOAD")

    android_major = None
    if android_raw:
        match = re.search(r"\d+", android_raw)
        android_major = int(match.group()) if match else None
    if model and not re.fullmatch(r"CLT-L(?:09|29)", model.upper()):
        model = None
    else:
        model = model.upper() if model else None
    if region and not re.fullmatch(r"C\d{3}", region.upper()):
        region = None
    else:
        region = region.upper() if region else None
    if preload and not re.fullmatch(r"C\d{3}R\d+", preload.upper()):
        preload = None
    else:
        preload = preload.upper() if preload else None

    status = RecoveryIdentityStatus.READY if model and region and preload and lock_state == "LOCKED" else RecoveryIdentityStatus.NEED_IDENTITY_EVIDENCE
    return RecoveryIdentity(status, family, build, android_major, board_id, lock_state, model, region, preload)

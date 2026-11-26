"""Read-only HarmonyOS/HDC identification.

HDC is not Fastboot. A WinUSB VID:PID observation proves only transport
presence. The retail model is accepted only from an authorized HDC shell
property response, never from a USB PID, name, photo or catalogue.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
import re
import subprocess
import tempfile
from typing import Callable

_ID = re.compile(r"[A-Za-z0-9._:-]{4,180}\Z")
_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _./+()\-]{1,119}\Z")
_FAILED = re.compile(r"(?i)\b(error|failed|unauthorized|permission denied|not found|unknown command|invalid|offline)\b")


@dataclass(frozen=True)
class HdcIdentity:
    status: str
    model: str = ""
    brand: str = ""
    build: str = ""
    target_key_sha256: str = ""
    reason: str = ""

    @property
    def identity_verified(self) -> bool:
        return self.status == "model_read" and bool(self.model)


def _execute(
    hdc: str, args: list[str], *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    timeout: int = 8,
) -> subprocess.CompletedProcess:
    # Never invoke a shell; the command is fixed and target keys are validated.
    # HDC starts a host-side daemon which can inherit pipe handles. Capturing
    # stdout with PIPE may hang even after the command client exits on Windows.
    # A temporary disk-backed handle closes cleanly independently of the daemon.
    command = [hdc, *args]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if runner is subprocess.run:
        with tempfile.TemporaryFile(mode="w+b") as sink:
            completed = runner(
                command, shell=False, check=False,
                stdout=sink, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                timeout=timeout, creationflags=flags,
            )
            sink.seek(0)
            output = sink.read(8192).decode("utf-8", "replace")
        return subprocess.CompletedProcess(command, completed.returncode, output, "")
    return runner(
        command, shell=False, check=False,
        capture_output=True, text=True, timeout=timeout,
        creationflags=flags,
    )


def _result_text(result: subprocess.CompletedProcess) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or ""))[:8192]


def _parse_usb_targets(raw: str) -> tuple[str, str]:
    """Return exactly one connected USB target, or a precise failure state.

    Official verbose output: key USB Connected device_name hdc.
    TCP devices are never selected by an automatic USB identification request.
    """
    rows = [x.strip() for x in raw.splitlines() if x.strip()]
    if any(x.casefold() in {"[empty]", "[empty]."} for x in rows):
        return "", "empty"
    usb = []
    for line in rows:
        parts = line.split()
        if len(parts) < 3 or not _ID.fullmatch(parts[0]):
            continue
        if parts[1].casefold() != "usb":
            continue
        state = parts[2].casefold()
        if state in {"connected", "ready"}:
            usb.append(parts[0])
        elif state in {"unauthorized", "offline", "unknown"}:
            return "", state
    if len(usb) > 1:
        return "", "multiple_usb_targets"
    if len(usb) == 1:
        return usb[0], "connected"
    # A host may retain historical UART COM target names even after Windows
    # reports no corresponding present PnP COM port. Do not attach those
    # targets to a currently-present WinUSB Huawei handset.
    if any(
        len(parts) >= 3 and parts[1].casefold() == "uart"
        for line in rows if (parts := line.split())
    ):
        return "", "non_usb_targets_only"
    return "", "empty_or_unrecognized"


def _read_property(hdc: str, key: str, name: str, runner) -> str:
    response = _execute(
        hdc, ["-t", key, "shell", "param", "get", name],
        runner=runner, timeout=8,
    )
    if response.returncode != 0:
        return ""
    lines = [s.strip() for s in _result_text(response).splitlines() if s.strip()]
    if len(lines) != 1:
        return ""
    candidate = lines[0]
    if _FAILED.search(candidate) or not _VALUE.fullmatch(candidate):
        return ""
    return candidate


def probe_hdc_identity(
    hdc: str, *, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> HdcIdentity:
    if not hdc:
        return HdcIdentity("missing_tool", reason="HDC executable not installed in verified SDK toolchain")
    try:
        version = _execute(hdc, ["-v"], runner=runner, timeout=6)
        match = re.search(r"\bVer:\s*(\d+)\.(\d+)\.(\d+)([a-z])\b",
                          _result_text(version), re.I)
        if version.returncode != 0 or match is None:
            return HdcIdentity("version_unknown", reason="HDC version could not be verified")
        actual = (int(match[1]), int(match[2]), int(match[3]), match[4].lower())
        if actual < (3, 1, 0, "a"):
            return HdcIdentity("unsupported_version",
                               reason=f"HDC {match.group(0)} is too old for HarmonyOS authorization; API 12 or later required")
        listing = _execute(hdc, ["list", "targets", "-v"], runner=runner)
        if listing.returncode != 0:
            return HdcIdentity("list_failed", reason="HDC target enumeration failed")
        key, state = _parse_usb_targets(_result_text(listing))
        if state != "connected":
            reason = (
                "HDC reports only UART targets; no HDC USB session exists for "
                "the attached HarmonyOS WinUSB interface"
                if state == "non_usb_targets_only"
                else "No single authorized HDC USB session"
            )
            return HdcIdentity(state, reason=reason)
        target_hash = sha256(key.encode("utf-8")).hexdigest()
        model = _read_property(hdc, key, "const.product.model", runner)
        if not model:
            return HdcIdentity(
                "property_unavailable", target_key_sha256=target_hash,
                reason="HDC connected, but authorized model property was not returned",
            )
        brand = _read_property(hdc, key, "const.product.brand", runner)
        if brand and brand.casefold() not in {"huawei", "honor"}:
            return HdcIdentity(
                "brand_mismatch", target_key_sha256=target_hash,
                reason="HDC reports a non-Huawei/Honor brand",
            )
        build = _read_property(hdc, key, "const.product.software.version", runner)
        return HdcIdentity("model_read", model, brand, build, target_hash)
    except subprocess.TimeoutExpired:
        return HdcIdentity("timeout", reason="HDC did not respond within read-only deadline")
    except OSError as exc:
        return HdcIdentity("tool_error", reason=f"HDC unavailable: {type(exc).__name__}")

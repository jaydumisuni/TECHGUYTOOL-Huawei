from __future__ import annotations

"""Resolve trusted Android platform-tools without relying on PATH.

The owner-approved Builder-managed shared Support package is preferred
only when its SHA-256 inventory verifies. Existing app-local and legacy
platform-tools paths remain fallback until Builder installs shared support.
This application never installs, upgrades, or deletes shared support.
"""

from pathlib import Path
import hashlib
import json
import os
from shutil import which

_SUPPORT_COMPANY = "THETECHGUY Digital Solutions"
_REQUIRED = ("adb.exe", "fastboot.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll")


def shared_support_root() -> Path | None:
    if os.name != "nt":
        return None
    x86 = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
    return Path(x86) / _SUPPORT_COMPANY / "Support"


def _verified_shared_dir() -> Path | None:
    support = shared_support_root()
    if support is None:
        return None
    tools = support / "Android" / "platform-tools"
    manifest = support / "manifests" / "android-platform-tools.json"
    try:
        inventory = json.loads(manifest.read_text(encoding="utf-8"))
        if inventory.get("schema") != "ttg.shared-support.android-platform-tools.v1":
            return None
        hashes = inventory.get("files")
        if not isinstance(hashes, dict) or not set(_REQUIRED).issubset(hashes):
            return None
        if not tools.is_dir() or tools.is_symlink():
            return None
        if {x.name for x in tools.iterdir()} != set(hashes):
            return None
        for name, expected in hashes.items():
            if not isinstance(name, str) or Path(name).name != name or not name:
                return None
            digest = str(expected).casefold()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                return None
            file = tools / name
            if not file.is_file() or file.is_symlink():
                return None
            if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                return None
        return tools
    except (OSError, ValueError, TypeError, PermissionError, json.JSONDecodeError):
        return None


def resolve_tool(app_root: Path, name: str) -> str | None:
    if name not in {"adb", "fastboot"}:
        return None
    executable = f"{name}.exe" if os.name == "nt" else name
    shared = _verified_shared_dir()
    locations = (
        *((shared / executable,) if shared is not None else ()),
        app_root / "runtime" / "platform-tools" / executable,
        Path("C:/Program Files/platform-tools") / executable,
    )
    for candidate in locations:
        if candidate.is_file():
            return str(candidate)
    return which(name) if os.name != "nt" else None


def tool_status(app_root: Path) -> dict[str, str | None]:
    return {name: resolve_tool(app_root, name) for name in ("adb", "fastboot")}

"""HDC executable resolution with independent package provenance.

The shared-support manifest pins every used byte; never trust arbitrary PATH
executables for this service route. This module never installs or updates HDC.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path

SCHEMA = "ttg.shared-support.harmonyos-hdc.v1"
FILES = ("hdc.exe",)


def resolve_hdc_tool(app_root: Path) -> str | None:
    """Resolve a locally verified OpenHarmony SDK HDC, if installed."""
    roots = [
        app_root / "runtime" / "harmonyos" / "toolchains-v7",
        app_root / "runtime" / "harmonyos" / "toolchains",
    ]
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        roots.insert(0, program_files / "THETECHGUY Digital Solutions" /
                     "Support" / "HarmonyOS" / "toolchains")
    for base in roots:
        manifest = base / "hdc-manifest.json"
        tool = base / "hdc.exe"
        if not manifest.is_file() or manifest.is_symlink() or not tool.is_file() or tool.is_symlink():
            continue
        try:
            doc = json.loads(manifest.read_text(encoding="utf-8"))
            if doc.get("schema") != SCHEMA:
                continue
            digests = doc.get("files")
            if not isinstance(digests, dict) or "hdc.exe" not in digests:
                continue
            if any(x not in ("hdc.exe", "libusb_shared.dll") for x in digests):
                continue
            if not isinstance(doc.get("source"), str) or not doc.get("source"):
                continue
            if any(
                not isinstance(value, str) or len(value) != 64 or
                any(ch not in "0123456789abcdef" for ch in value)
                for value in digests.values()
            ):
                continue
            if "libusb_shared.dll" in digests and not (base / "libusb_shared.dll").is_file():
                continue
            if any(
                (base / name).is_symlink() or
                sha256((base / name).read_bytes()).hexdigest() != digest
                for name, digest in digests.items()
            ):
                continue
            return str(tool)
        except (OSError, ValueError, TypeError):
            continue
    return None

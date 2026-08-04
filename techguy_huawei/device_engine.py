from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import which
from typing import Iterable
import os
import re
import subprocess
import uuid

from .action_health import ActionState
from .evidence import EvidenceEnvelope, EvidenceJournal


@dataclass(slots=True)
class EngineResult:
    ok: bool
    message: str
    health_state: ActionState
    payload: dict[str, object] | None = None


@dataclass(slots=True)
class DeviceSnapshot:
    connected: bool = False
    interface: str = "—"
    platform: str = "—"
    security: str = "—"
    model: str = "NO DEVICE CONNECTED"
    serial: str = ""
    session_id: str = ""


class DeviceEngine:
    """Read-first Huawei transport core.

    Commands are fixed arrays and never pass through a shell. Exactly one device
    is required before a device identity is accepted. Destructive service actions
    remain guarded until an approved engine adapter is installed.
    """

    def __init__(self, app_root: Path, journal: EvidenceJournal) -> None:
        self.app_root = app_root
        self.journal = journal
        self.snapshot = DeviceSnapshot(session_id=str(uuid.uuid4()))

    def _tool(self, name: str) -> str | None:
        candidates = [
            self.app_root / "runtime" / "platform-tools" / f"{name}.exe",
            self.app_root / "runtime" / "platform-tools" / name,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return which(name)

    def _run(self, action_id: str, args: Iterable[str], timeout: int = 12) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        command = list(args)
        completed = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        envelope = EvidenceEnvelope.create(
            session_id=self.snapshot.session_id,
            action_id=action_id,
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        self.journal.append(envelope)
        return completed, command

    @staticmethod
    def _adb_rows(output: str) -> list[str]:
        rows: list[str] = []
        for raw in output.splitlines():
            line = raw.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            rows.append(line)
        return rows

    @staticmethod
    def _fastboot_rows(output: str) -> list[str]:
        rows = []
        for raw in output.splitlines():
            line = raw.strip()
            if re.match(r"^\S+\s+fastboot(?:d)?$", line, flags=re.IGNORECASE):
                rows.append(line)
        return rows

    def probe(self) -> EngineResult:
        adb = self._tool("adb")
        fastboot = self._tool("fastboot")
        adb_rows: list[str] = []
        fastboot_rows: list[str] = []
        if adb:
            result, _ = self._run("read_device", [adb, "devices", "-l"])
            adb_rows = self._adb_rows(result.stdout)
        if fastboot:
            result, _ = self._run("read_device", [fastboot, "devices"])
            fastboot_rows = self._fastboot_rows(result.stdout)

        total = len(adb_rows) + len(fastboot_rows)
        if total == 0:
            self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
            missing = []
            if not adb:
                missing.append("ADB")
            if not fastboot:
                missing.append("Fastboot")
            if missing:
                return EngineResult(False, f"No device detected. Missing tools: {', '.join(missing)}.", ActionState.MISSING_DEPENDENCY)
            return EngineResult(False, "No Huawei device detected in ADB or Fastboot mode.", ActionState.READY)
        if total > 1:
            self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
            return EngineResult(False, "Multiple devices detected. Connect exactly one service device.", ActionState.GUARDED)

        if adb_rows:
            serial = adb_rows[0].split()[0]
            if "unauthorized" in adb_rows[0]:
                return EngineResult(False, "ADB device is unauthorized. Accept the RSA prompt on the phone.", ActionState.GUARDED)
            if "offline" in adb_rows[0]:
                return EngineResult(False, "ADB device is offline.", ActionState.FAILED)
            model = "Huawei Android Device"
            platform_name = "Android / ADB"
            security = "Authorized"
            if adb:
                props, _ = self._run("read_device", [adb, "-s", serial, "shell", "getprop", "ro.product.model"])
                candidate = props.stdout.strip()
                if candidate:
                    model = candidate
            self.snapshot = DeviceSnapshot(True, "ADB", platform_name, security, model, serial, str(uuid.uuid5(uuid.NAMESPACE_URL, serial)))
        else:
            serial = fastboot_rows[0].split()[0]
            self.snapshot = DeviceSnapshot(True, "Fastboot", "Huawei Fastboot", "Read-only", "Huawei Fastboot Device", serial, str(uuid.uuid5(uuid.NAMESPACE_URL, serial)))
        return EngineResult(True, f"Connected: {self.snapshot.model} via {self.snapshot.interface}.", ActionState.READY, asdict(self.snapshot))

    def guarded(self, label: str) -> EngineResult:
        return EngineResult(
            False,
            f"{label} is wired but guarded. Install an approved service adapter and complete ownership authorization before write access.",
            ActionState.GUARDED,
        )

    def package_preflight(self, package_path: str) -> EngineResult:
        path = Path(package_path)
        if not path.is_file():
            return EngineResult(False, "Select a firmware package first.", ActionState.GUARDED)
        if path.stat().st_size == 0:
            return EngineResult(False, "Firmware package is empty.", ActionState.FAILED)
        return EngineResult(True, f"Package selected: {path.name} ({path.stat().st_size:,} bytes).", ActionState.READY, {"path": str(path), "size": path.stat().st_size})

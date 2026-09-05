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
from .windows_usb import UsbDiscoveryError, discover_windows_huawei_usb


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
        usb_report = None
        if _is_windows():
            try:
                usb_report = discover_windows_huawei_usb()
            except UsbDiscoveryError as exc:
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False,
                    f"Huawei USB discovery unavailable: {exc.message}",
                    ActionState.FAILED,
                )
            if usb_report.state == "multiple_huawei_devices":
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False,
                    "Multiple Huawei devices detected. Select exactly one physical Huawei device.",
                    ActionState.GUARDED,
                    {"usb_discovery": usb_report.to_dict()},
                )
            if usb_report.present and usb_report.state not in {"adb", "normal_fastboot"}:
                return self._result_from_usb_report(usb_report)

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

        if _is_windows():
            if usb_report is None or not usb_report.present:
                adb_rows = self._verified_huawei_adb_rows(adb, adb_rows) if adb else []
                fastboot_rows = []
            elif usb_report.state == "adb":
                adb_rows = self._verified_huawei_adb_rows(adb, adb_rows) if adb else []
                fastboot_rows = []
            elif usb_report.state == "normal_fastboot":
                adb_rows = []

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
            return EngineResult(False, "No Huawei device detected in USB, ADB or Fastboot mode.", ActionState.READY)
        if total > 1:
            self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
            return EngineResult(False, "Multiple Huawei devices detected. Connect exactly one service device.", ActionState.GUARDED)

        if adb_rows:
            serial = adb_rows[0].split()[0]
            if "unauthorized" in adb_rows[0]:
                return EngineResult(False, "ADB device is unauthorized.", ActionState.GUARDED)
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

        payload: dict[str, object] = asdict(self.snapshot)
        if usb_report is not None and usb_report.present:
            payload["usb_discovery"] = usb_report.to_dict()
        return EngineResult(True, f"Connected: {self.snapshot.model} via {self.snapshot.interface}.", ActionState.READY, payload)

    def _verified_huawei_adb_rows(self, adb: str | None, rows: list[str]) -> list[str]:
        if not adb:
            return []
        verified: list[str] = []
        for row in rows:
            lowered = row.lower()
            if "unauthorized" in lowered or "offline" in lowered:
                continue
            serial = row.split()[0]
            result, _ = self._run(
                "read_device",
                [adb, "-s", serial, "shell", "getprop", "ro.product.manufacturer"],
            )
            manufacturer = result.stdout.strip().upper()
            if manufacturer in {"HUAWEI", "HONOR"}:
                verified.append(row)
        return verified

    def _result_from_usb_report(self, usb_report) -> EngineResult:
        labels = {
            "storage_only_pre_service": "Huawei USB / Pre-service",
            "mtp": "MTP",
            "recovery": "Recovery",
            "upgrade_mode": "Upgrade Mode",
            "huawei_usb_com_1_0": "HUAWEI USB COM 1.0",
            "unknown_huawei": "Huawei USB",
        }
        interface = labels.get(usb_report.state, "Huawei USB")
        session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, usb_report.fingerprint_sha256))
        self.snapshot = DeviceSnapshot(
            True,
            interface,
            "Huawei USB",
            "Read-only / identity pending",
            "Huawei device (identity pending)",
            "",
            session_id,
        )
        payload: dict[str, object] = asdict(self.snapshot)
        payload["usb_discovery"] = usb_report.to_dict()
        return EngineResult(
            True,
            f"Connected: {self.snapshot.model} via {interface}. {usb_report.decision_code}.",
            ActionState.READY,
            payload,
        )

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


def _is_windows() -> bool:
    return os.name == "nt"

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import platform
import sys

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from .action_health import ActionRegistry, ActionState
from .device_engine import DeviceEngine, EngineResult
from .evidence import EvidenceJournal
from .storage import AppPaths


class Backend(QObject):
    logTextChanged = Signal()
    deviceChanged = Signal()
    healthChanged = Signal()
    progressChanged = Signal()
    registrationChanged = Signal()
    firmwareChanged = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = app_root
        self.paths = AppPaths.resolve()
        self.engine = DeviceEngine(app_root, EvidenceJournal(self.paths.evidence / "operations.jsonl"))
        self._log_lines: list[str] = []
        self._progress = 0
        self._registered = self.paths.registration.is_file()
        self._firmware_path = ""
        self._heartbeat_count = 0
        self._ui_actions: set[str] = set()
        self._handlers = {
            "read_device": self.engine.probe,
            "open_terminal": self._open_terminal,
            "fix_drivers": lambda: self.engine.guarded("Driver repair"),
            "register_device": self._registration_status,
            "frp_repair": lambda: self.engine.guarded("FRP Repair"),
            "bootloader": lambda: self.engine.guarded("Bootloader service"),
            "huawei_id": lambda: self.engine.guarded("Huawei ID service"),
            "verlist": lambda: self.engine.guarded("Verlist repair"),
            "pair": lambda: self.engine.guarded("Bluetooth/Wi-Fi pairing repair"),
            "full_oeminfo": lambda: self.engine.guarded("Full OEMINFO read"),
            "flash_firmware": self._firmware_preflight,
            "board_repair": lambda: self.engine.guarded("Board repair"),
            "backup_restore": lambda: self.engine.guarded("Backup / Restore"),
        }
        self.registry = ActionRegistry(self._handlers, app_root / "data" / "action_manifest.json")
        self._startup_log()
        self._audit_runtime_wiring()
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._heartbeat)
        self.health_timer.start(5000)
        QTimer.singleShot(1500, self._audit_ui_bindings)

    def _stamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _append(self, text: str, level: str = "INFO") -> None:
        self._log_lines.append(f"[{self._stamp()}] [{level}] {text}")
        self._log_lines = self._log_lines[-200:]
        self.logTextChanged.emit()

    def _startup_log(self) -> None:
        self._append("TECHGUY TOOL — HUAWEI", "SYSTEM")
        self._append("Service & Recovery Edition")
        self._append("Initializing modules...")
        self._append("Action wiring ledger loaded.", "OK")
        self._append("Read-first device evidence core ready.", "OK")
        self._append("Write operations are guarded until approved adapters are installed.", "GUARD")
        self._append("Waiting for device connection...")

    def _audit_runtime_wiring(self) -> None:
        executable = self.app_root / "runtime" / "health" / ("techguy_health_core.exe" if sys.platform.startswith("win") else "techguy_health_core")
        report = self.registry.run_rust_audit(executable)
        if report is None:
            self._append("Rust action-health core not present; Python contract audit remains active.", "INFO")
        elif report.get("ok"):
            self._append(f"Rust action-health audit passed for {report.get('action_count', 0)} actions.", "OK")
        else:
            self._append(f"Rust action-health audit failed: {report}", "ERROR")

    def _audit_ui_bindings(self) -> None:
        missing = sorted(self.registry.expected_ids() - self._ui_actions)
        if missing:
            self._append("UI action binding audit missing: " + ", ".join(missing), "ERROR")
        else:
            self._append(f"UI action binding audit passed for {len(self._ui_actions)} actions.", "OK")

    def _heartbeat(self) -> None:
        self._heartbeat_count += 1
        if self._heartbeat_count % 12 == 0:
            self._audit_runtime_wiring()
            self._audit_ui_bindings()
        self.healthChanged.emit()

    def _open_terminal(self) -> EngineResult:
        self._append("Fastboot terminal requested. The embedded console uses fixed safe commands until a device is selected.")
        return EngineResult(True, "Terminal interface opened.", ActionState.READY)

    def _registration_status(self) -> EngineResult:
        return EngineResult(True, "This computer is registered." if self._registered else "This computer is not registered.", ActionState.READY)

    def _firmware_preflight(self) -> EngineResult:
        return self.engine.package_preflight(self._firmware_path)

    @Property(str, notify=logTextChanged)
    def logText(self) -> str:
        return "\n".join(self._log_lines)

    @Property(bool, notify=deviceChanged)
    def connected(self) -> bool:
        return self.engine.snapshot.connected

    @Property(str, notify=deviceChanged)
    def deviceModel(self) -> str:
        return self.engine.snapshot.model

    @Property(str, notify=deviceChanged)
    def deviceInterface(self) -> str:
        return self.engine.snapshot.interface

    @Property(str, notify=deviceChanged)
    def devicePlatform(self) -> str:
        return self.engine.snapshot.platform

    @Property(str, notify=deviceChanged)
    def deviceSecurity(self) -> str:
        return self.engine.snapshot.security

    @Property(str, notify=healthChanged)
    def healthSummary(self) -> str:
        return self.registry.summary()

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Property(bool, notify=registrationChanged)
    def registered(self) -> bool:
        return self._registered

    @Property(str, notify=registrationChanged)
    def computerId(self) -> str:
        import hashlib
        raw = f"{platform.node()}|{platform.machine()}|{sys.platform}"
        return "-".join(hashlib.sha256(raw.encode()).hexdigest().upper()[i:i+4] for i in range(0, 16, 4))

    @Property(str, notify=firmwareChanged)
    def firmwarePath(self) -> str:
        return self._firmware_path

    @Slot(str)
    def setFirmwarePath(self, path: str) -> None:
        self._firmware_path = path.removeprefix("file:///") if sys.platform.startswith("win") else path.removeprefix("file://")
        self.firmwareChanged.emit()
        self._append(f"Firmware package selected: {self._firmware_path}")

    @Slot(str)
    def registerUiAction(self, action_id: str) -> None:
        if action_id in self.registry.expected_ids():
            self._ui_actions.add(action_id)
        else:
            self._append(f"UI declared unknown action: {action_id}", "ERROR")

    @Slot(str, result=str)
    def runAction(self, action_id: str) -> str:
        self._append(f"Action requested: {action_id}")
        try:
            result = self.registry.invoke(action_id)
        except Exception as exc:
            self._append(str(exc), "ERROR")
            self.healthChanged.emit()
            return str(exc)
        assert isinstance(result, EngineResult)
        self._append(result.message, "OK" if result.ok else "GUARD" if result.health_state.value == "GUARDED" else "INFO")
        if action_id == "read_device":
            self.deviceChanged.emit()
        self.healthChanged.emit()
        return result.message

    @Slot(str, result=bool)
    def registerDevice(self, key: str) -> bool:
        if len(key.strip()) < 12:
            self._append("Registration key rejected: key is too short.", "ERROR")
            return False
        payload = {"computer_id": self.computerId, "registered_at": datetime.now().isoformat(), "key_hash": __import__("hashlib").sha256(key.encode()).hexdigest()}
        self.paths.registration.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._registered = True
        self.registrationChanged.emit()
        self._append("Device registration stored locally.", "OK")
        return True

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import json
import platform
import sys
from time import monotonic

from PySide6.QtCore import QObject, Property, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from .action_health import ActionRegistry, ActionState
from .device_engine import DeviceSnapshot, EngineResult
from .desktop_worker import HealthAuditWorker, PinoutWorker, ServiceWorker, UsbPresenceWorker
from .service_dispatch import SERVICE_OPERATIONS, ServiceRequest, ServiceResponse
from .service_loader_registry import resolve_loader
from .storage import AppPaths
from .operation_log import ActionLog
from .terminal_engine import TerminalCommand, parse_console, terminal_context_fingerprint
from .terminal_directory import try_directory_command
from .testpoint_catalog import (
    exact_testpoint_record,
    expected_service_interface,
    load_device_profiles,
    load_testpoint_catalog,
)


class Backend(QObject):
    logTextChanged = Signal()
    deviceChanged = Signal()
    healthChanged = Signal()
    progressChanged = Signal()
    registrationChanged = Signal()
    firmwareChanged = Signal()
    firmwareModeChanged = Signal()
    firmwareTargetChanged = Signal()
    firmwarePlanChanged = Signal()
    operationSelectionChanged = Signal()
    operationBusyChanged = Signal()
    terminalOutputChanged = Signal()
    terminalDirectoryChanged = Signal()
    terminalConfirmationChanged = Signal()
    actionLogSaved = Signal()
    serviceResultChanged = Signal()
    testpointRequired = Signal(str, str)
    serviceEntryChanged = Signal()
    pinoutChanged = Signal()
    pinoutBusyChanged = Signal()

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = app_root
        self.paths = AppPaths.resolve()
        self._device_snapshot = DeviceSnapshot()
        self._service_entry = ""
        self._last_read_status = "Press READ DEVICE to scan for a Huawei phone."
        # Each terminal session keeps its own directory. Never modify the GUI
        # process cwd; only ADB/Fastboot worker subprocesses inherit this path.
        self._terminal_cwd = str(app_root.resolve())
        self._pending_terminal: tuple[str, TerminalCommand, str, float, str] | None = None
        self._terminal_output = ""
        self._busy = False
        self._worker: ServiceWorker | None = None
        self._audit_worker: HealthAuditWorker | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        from .usb_presence import PresenceTracker
        self._usb_presence=PresenceTracker()
        self._usb_presence_worker=None
        # Separate pool: remote pinout searches never block USB service actions.
        self._pinout_pool = QThreadPool(self)
        self._pinout_pool.setMaxThreadCount(1)
        self._pinout_worker: PinoutWorker | None = None
        self._pinout_busy = False
        self._pinout_results: dict = {"source": "https://pinout.thetechguyds.com/", "results": []}
        self._pinout_image: dict = {}
        self._pinout_status = "Pinout library ready. Search by exact brand and model."
        self._log_lines: list[str] = []
        self._action_log_active = False
        self._last_action_log_path = ""
        self._last_action_record_path = ""
        self._last_service_result: dict = {}
        self._service_results: dict[str, dict] = {}
        self._progress = 0
        self._operation_status = ""
        self._read_display_active = False
        self._device_report = ""
        self._device_details = {}
        self._device_partitions = []
        self._partition_request = None
        self._partition_plan = {}
        self._registered = self.paths.registration.is_file()
        self._firmware_path = ""
        self._firmware_mode = "Upgrade"
        self._firmware_model = ""
        self._firmware_chipset = ""
        self._loader_variant = ""
        self._auto_target_serial = ""
        self._firmware_chipset_manually_selected = False
        self._firmware_plan_hash = ""
        self._heartbeat_count = 0
        self._ui_actions: set[str] = set()
        self._selected_operation_label = "No active operation"
        self._device_profiles = load_device_profiles(app_root)
        self._testpoint_catalog = load_testpoint_catalog(app_root)
        self._handlers = {
            "read_device": lambda: self._worker_only("Read Device"),
            "open_terminal": self._open_terminal,
            "fix_drivers": lambda: self._guarded("Driver repair"),
            "register_device": self._registration_status,
            "frp_repair": lambda: self._worker_only("Owner service"),
            "bootloader": lambda: self._worker_only("Owner service"),
            "huawei_id": lambda: self._worker_only("Owner service"),
            "verlist": lambda: self._worker_only("Verlist"),
            "pair": lambda: self._worker_only("Owner service"),
            "full_oeminfo": lambda: self._worker_only("Full OEMINFO"),
            "flash_firmware": lambda: self._worker_only("Firmware preflight"),
            "board_repair": lambda: self._worker_only("Board Repair"),
            "backup_restore": lambda: self._worker_only("Backup"),
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

    def _action_logs_dir(self) -> Path:
        # User-facing reports live directly under Logs/<local date>/.
        # Keep raw command evidence under the separate evidence directory.
        return getattr(self.paths, "logs", self.paths.evidence.parent / "Logs")

    def _start_action_display(self) -> None:
        # The previous action stays saved on disk. Only its visible text clears.
        self._log_lines.clear()
        self._read_display_active = False
        self._operation_status = ""
        self._progress = 0
        self.progressChanged.emit()
        self._action_log_active = True
        self.logTextChanged.emit()

    @Slot()
    def cancelEdlReconnect(self):
        if self._worker is not None and self._operation_status.startswith("EDL RECONNECT REQUIRED:"):
            event=getattr(self._worker,"reconnect_cancel",None)
            if event is not None:event.set()

    @Property(str, notify=serviceEntryChanged)
    def serviceEntryState(self):
        return self._service_entry

    @Slot()
    def cancelServiceEntry(self):
        if self._service_entry in {"waiting","com"} and self._worker is not None:
            event=getattr(self._worker,"reconnect_cancel",None)
            if event is not None:event.set()

    @Slot(str)
    def _on_operation_progress(self, line: str) -> None:
        self._operation_status = line
        from .kirin_repair_session import WAIT,COM,READY
        if line.startswith(WAIT):
            self._service_entry="waiting"
            self.serviceEntryChanged.emit()
            model=line[len(WAIT):].split("|",1)[0].strip()
            self.testpointRequired.emit(model,"Firmware Repair")
        elif line.startswith(COM):
            self._service_entry="com"
            self.serviceEntryChanged.emit()
        elif line.startswith(READY):
            self._service_entry=""
            self.serviceEntryChanged.emit()
        self.progressChanged.emit()
        if self._read_display_active:
            return
        self._log_lines.append(line)
        self._log_lines = self._log_lines[-400:]
        self.logTextChanged.emit()

    def _record_nonservice_action(self, action_id: str, result: EngineResult) -> None:
        record = ActionLog(self._action_logs_dir(), action_id)
        record.add(result.message)
        record.complete(result)
        self._last_action_log_path = str(record.log_path)
        self._last_action_record_path = str(record.record_path)
        self.actionLogSaved.emit()

    def _startup_log(self) -> None:
        self._append("TECHGUY TOOL — HUAWEI", "SYSTEM")
        self._append("Service & Recovery Edition")
        self._append("Initializing modules...")
        self._append("Action wiring ledger loaded.", "OK")
        self._append("Read-first device evidence core ready.", "OK")
        self._append("Write operations are guarded until approved adapters are installed.", "GUARD")
        self._append("Waiting for device connection...")

    def _audit_runtime_wiring(self) -> None:
        if self._audit_worker is not None:
            return
        executable = self.app_root / "runtime" / "health" / (
            "techguy_health_core.exe" if sys.platform.startswith("win") else "techguy_health_core"
        )
        worker = HealthAuditWorker(executable, self.app_root / "data" / "action_manifest.json")
        worker.signals.finished.connect(self._on_health_audit)
        self._audit_worker = worker
        self._pool.start(worker)

    @Slot(object)
    def _on_health_audit(self, report: dict | None) -> None:
        self._audit_worker = None
        if self._action_log_active:
            return
        if report is None:
            self._append("Rust action-health core not present; Python contract audit remains active.")
        elif report.get("ok"):
            self._append(f"Rust action-health audit passed for {report.get('action_count', 0)} actions.", "OK")
        else:
            self._append(f"Rust action-health audit failed: {report}", "ERROR")

    def _audit_ui_bindings(self) -> None:
        if self._action_log_active:
            return
        missing = sorted(self.registry.expected_ids() - self._ui_actions)
        if missing:
            self._append("UI action binding audit missing: " + ", ".join(missing), "ERROR")
        else:
            self._append(f"UI action binding audit passed for {len(self._ui_actions)} actions.", "OK")

    def _heartbeat(self) -> None:
        self._poll_usb_presence()
        self._heartbeat_count += 1
        if self._heartbeat_count % 12 == 0:
            self._audit_runtime_wiring()
            self._audit_ui_bindings()
        self.healthChanged.emit()

    def _poll_usb_presence(self):
        if not sys.platform.startswith("win") or self._busy or self._usb_presence_worker is not None:
            return
        worker=UsbPresenceWorker()
        worker.signals.finished.connect(self._on_usb_presence)
        self._usb_presence_worker=worker
        self._pool.start(worker)

    @Slot(object)
    def _on_usb_presence(self,report):
        self._usb_presence_worker=None
        # A manual action may have begun after the observation was queued.
        # Do not let an obsolete observation change its target or log.
        if self._busy:return
        action=self._usb_presence.update(report)
        if action=="scan":
            self._invalidate_firmware_plan()
            self._partition_plan={}
            self._partition_request=None
            self.serviceResultChanged.emit()
            self.runAction("read_device")
        elif action=="clear":
            self._device_snapshot=DeviceSnapshot()
            self._device_details={}
            self._device_report=""
            self._device_partitions=[]
            self._partition_plan={}
            self._partition_request=None
            self._invalidate_firmware_plan()
            if self._auto_target_serial:self._clear_detected_target()
            self._last_read_status=("Multiple Huawei devices detected." if report.state=="multiple_huawei_devices" else "No Huawei device detected.")
            self.deviceChanged.emit()
            self.serviceResultChanged.emit()

    def _open_terminal(self) -> EngineResult:
        self._append("Huawei terminal opened. ADB/Fastboot reads execute asynchronously; device-state changes require exact-command confirmation.")
        return EngineResult(True, "Terminal interface opened.", ActionState.READY)

    def _registration_status(self) -> EngineResult:
        return EngineResult(True, "This computer is registered." if self._registered else "This computer is not registered.", ActionState.READY)

    def _guarded(self, label: str) -> EngineResult:
        return EngineResult(False, f"{label} requires a verified service adapter.", ActionState.GUARDED)

    def _worker_only(self, label: str) -> EngineResult:
        return EngineResult(False, f"{label} requires the async service dispatcher.", ActionState.GUARDED)

    @Slot(result="QVariantList")
    def operationHistory(self):
        from .operation_history import records
        return records(self._action_logs_dir())

    @Slot(str,result=str)
    def readOperationLog(self,path):
        from .operation_history import read_log
        try:return read_log(self._action_logs_dir(),path)
        except (OSError,ValueError) as exc:return str(exc)

    @Slot(str,result=bool)
    def openOperationLog(self,path):
        from .operation_history import read_log
        try:
            read_log(self._action_logs_dir(),path)
            return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        except (OSError,ValueError):return False

    @Slot(str,"QVariantList",result=bool)
    def exportOperationHistory(self,path,rows):
        from .operation_history import export
        try:
            url=QUrl(path)
            export(self._action_logs_dir(),url.toLocalFile() if url.isLocalFile() else path,rows)
            return True
        except (OSError,ValueError,TypeError):return False

    @Property(str, notify=logTextChanged)
    def logText(self) -> str:
        return "\n".join(self._log_lines)

    @Property(str, constant=True)
    def logsFolderPath(self) -> str:
        return str(self._action_logs_dir())

    @Slot(result=bool)
    def openLogsFolder(self) -> bool:
        """Open the user report directory on demand, without changing the action log."""
        folder = self._action_logs_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))))
        except (OSError, RuntimeError) as exc:
            self._append(f"Could not open Logs folder: {exc}", "ERROR")
            return False
        if not opened:
            self._append("Could not open Logs folder in the file manager.", "ERROR")
        return opened

    @Property(str, notify=actionLogSaved)
    def lastActionLogPath(self) -> str:
        return self._last_action_log_path

    @Property(str, notify=actionLogSaved)
    def lastActionRecordPath(self) -> str:
        return self._last_action_record_path

    @Property(str, notify=serviceResultChanged)
    def lastServiceResultJson(self) -> str:
        return json.dumps(self._last_service_result, ensure_ascii=False, default=str)

    @Slot(str, result=str)
    def serviceResultJson(self, action_id: str) -> str:
        """Retrieve exact backend response without parsing the human action log."""
        return json.dumps(self._service_results.get(action_id, {}), ensure_ascii=False, default=str)

    @Property(bool, notify=deviceChanged)
    def connected(self) -> bool:
        return self._device_snapshot.connected

    @Property(str, notify=deviceChanged)
    def deviceModel(self) -> str:
        return self._device_snapshot.model

    @Property(str, notify=deviceChanged)
    def deviceInterface(self) -> str:
        return self._device_snapshot.interface

    @Property(str, notify=deviceChanged)
    def devicePlatform(self) -> str:
        return self._device_snapshot.platform

    @Property(str, notify=deviceChanged)
    def deviceSecurity(self) -> str:
        return self._device_snapshot.security

    @Property(str, notify=deviceChanged)
    def lastReadStatus(self) -> str:
        return self._last_read_status

    @Property(str, notify=terminalOutputChanged)
    def terminalOutput(self) -> str:
        return self._terminal_output

    @Property(str, notify=terminalDirectoryChanged)
    def terminalCurrentDirectory(self) -> str:
        return self._terminal_cwd

    @Property(bool, notify=terminalConfirmationChanged)
    def terminalConfirmationPending(self) -> bool:
        return self._pending_terminal is not None

    @Property(str, notify=terminalConfirmationChanged)
    def terminalPendingCommand(self) -> str:
        return self._pending_terminal[0] if self._pending_terminal else ""

    @Property(str, notify=terminalConfirmationChanged)
    def terminalPendingWarning(self) -> str:
        if not self._pending_terminal:
            return ""
        return (
            "This command may modify partitions, data or device boot state. "
            "Review the exact command and connected device before confirming. "
            "The terminal will not automatically reboot or relock."
        )

    @Property(str, notify=deviceChanged)
    def deviceReport(self) -> str:
        return self._device_report

    @Property("QVariantMap", notify=deviceChanged)
    def deviceDetails(self) -> dict:
        return dict(self._device_details)

    @Property("QVariantList", notify=deviceChanged)
    def devicePartitions(self) -> list:
        return list(self._device_partitions)

    @Slot()
    def copyDeviceReport(self) -> None:
        from PySide6.QtGui import QGuiApplication
        if self._device_report:
            QGuiApplication.clipboard().setText(self._device_report)

    @Slot(str, result=bool)
    def saveDeviceReport(self, destination: str) -> bool:
        from PySide6.QtCore import QUrl
        if not self._device_report:return False
        path=QUrl(destination).toLocalFile()
        if not path:return False
        try:
            Path(path).write_text(self._device_report,encoding="utf-8")
            return True
        except OSError as exc:
            self._operation_status="Could not save report: "+str(exc)
            self.progressChanged.emit()
            return False

    @Property(str, notify=deviceChanged)
    def deviceProductName(self) -> str:
        return self._device_snapshot.product_name

    @Property(str, notify=deviceChanged)
    def deviceSerial(self) -> str:
        return self._device_snapshot.serial

    @Property(str, notify=deviceChanged)
    def deviceBuild(self) -> str:
        return self._device_snapshot.build_number

    @Property(str, notify=deviceChanged)
    def deviceVendorCountry(self) -> str:
        return self._device_snapshot.vendor_country

    @Property(str, notify=deviceChanged)
    def deviceBootloader(self) -> str:
        return self._device_snapshot.bootloader_state

    @Property(str, notify=deviceChanged)
    def deviceMainVersion(self) -> str:
        return self._device_snapshot.main_version

    @Property(str, notify=deviceChanged)
    def deviceAndroidVersion(self) -> str:
        return self._device_snapshot.android_version

    @Property(str, notify=deviceChanged)
    def deviceEmuiVersion(self) -> str:
        return self._device_snapshot.emui_version

    @Property(str, notify=deviceChanged)
    def deviceSecurityPatch(self) -> str:
        return self._device_snapshot.security_patch

    @Property(str, notify=deviceChanged)
    def deviceBoardId(self) -> str:
        return self._device_snapshot.board_id

    @Property(str, notify=deviceChanged)
    def deviceFrpState(self) -> str:
        return self._device_snapshot.frp_state

    @Property(str, notify=healthChanged)
    def healthSummary(self) -> str:
        return self.registry.summary()

    @Property(str, notify=progressChanged)
    def operationStatus(self) -> str:
        return self._operation_status

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

    @Property(str, notify=firmwareModeChanged)
    def firmwareMode(self) -> str:
        return self._firmware_mode

    @Property(str, notify=firmwareTargetChanged)
    def firmwareModel(self) -> str:
        return self._firmware_model

    @Property(str, notify=firmwareTargetChanged)
    def firmwareChipset(self) -> str:
        return self._firmware_chipset

    @Property(str, notify=firmwareTargetChanged)
    def loaderVariant(self) -> str:
        return self._loader_variant

    @Property("QStringList", notify=firmwareTargetChanged)
    def loaderVariantOptions(self):
        base = resolve_loader(self.app_root, self._firmware_chipset)
        return list(base.candidate_families) if base.status == "loader_variant_required" else []

    def _selected_loader(self):
        from .service_loader_registry import resolve_variant
        return resolve_variant(self.app_root, self._firmware_chipset, self._loader_variant)

    @Slot(str, result=bool)
    def setLoaderVariant(self, value: str) -> bool:
        if self._busy:
            return False
        value = value.strip().lower()
        if value and value not in self.loaderVariantOptions:
            return False
        if value != self._loader_variant:
            self._loader_variant = value
            self._invalidate_firmware_plan()
            self.firmwareTargetChanged.emit()
        return True

    @Property(str, notify=firmwareTargetChanged)
    def selectedServiceLoaderJson(self) -> str:
        return json.dumps(self._selected_loader().to_dict())

    @Property(str, notify=firmwareTargetChanged)
    def selectedServiceLoaderLabel(self) -> str:
        selection = self._selected_loader()
        if selection.status == "verified_images_unstaged":
            return (f"Loader selected: {selection.cpu} / {selection.stage} "
                    f"({len(selection.image_names)} SHA-256 verified images; not sent)")
        if selection.status == "verified_container_available":
            return f"Loader available: {selection.cpu} ({len(selection.image_names)} verified containers; stage transport pending)"
        if selection.status == "loader_variant_required":
            return "Select exact loader variant: " + ", ".join(selection.candidate_families)
        if selection.status == "awaiting_chipset":
            return "Service loader: select/detect chipset"
        return f"Service loader: unavailable for {selection.chipset} ({selection.status})"

    @Property(bool, notify=firmwarePlanChanged)
    def firmwarePlanReady(self) -> bool:
        return bool(self._firmware_plan_hash) and not self._busy

    def _invalidate_firmware_plan(self) -> None:
        if self._firmware_plan_hash:
            self._firmware_plan_hash = ""
            self.firmwarePlanChanged.emit()

    def _catalog_chipset(self, model: str) -> str:
        """Only an exact catalogue match may imply a specific chipset."""
        import re
        for record in self._device_profiles.get("models", []):
            if not isinstance(record, dict):
                continue
            if str(record.get("model", "")).upper() != model.upper():
                continue
            if record.get("chipset"):
                return str(record["chipset"]).strip().lower()
            platform_name = str(record.get("platform", ""))
            match = re.fullmatch(r"(?:Kirin|hisi)\s*(\d{3,4})", platform_name, flags=re.I)
            if match:
                return "kirin" + match.group(1)
        return ""

    def _clear_detected_target(self):
        self._auto_target_serial = ""
        self._firmware_model = ""
        self._firmware_chipset = ""
        self._loader_variant = ""
        self._invalidate_firmware_plan()
        self.firmwareTargetChanged.emit()

    def _apply_detected_target(self,payload):
        from .detected_target import observed_target
        target=observed_target(self._device_snapshot,payload,self._catalog_chipset)
        if target.conflict:
            self._append("Detected chipset differs from catalogue; review target identity.","GUARD")
        if not target.model and not target.chipset:
            if self._auto_target_serial:self._clear_detected_target()
            return
        if not self._auto_target_serial and (self._firmware_model or self._firmware_chipset_manually_selected):
            return
        changed=(self._auto_target_serial,self._firmware_model,self._firmware_chipset)!=(self._device_snapshot.serial,target.model,target.chipset)
        self._auto_target_serial=self._device_snapshot.serial
        if changed:
            self._firmware_model=target.model
            self._firmware_chipset=target.chipset
            self._firmware_chipset_manually_selected=False
            self._loader_variant=""
            self._invalidate_firmware_plan()
            self.firmwareTargetChanged.emit()
        if target.loader_variant and target.loader_variant in self.loaderVariantOptions and self._loader_variant!=target.loader_variant:
            self._loader_variant=target.loader_variant
            self._invalidate_firmware_plan()
            self.firmwareTargetChanged.emit()

    @Slot(str)
    def setFirmwareModel(self, value: str) -> None:
        value = value.strip().upper()
        if value == self._firmware_model:
            return
        # A new model cannot silently retain the chipset of a different model.
        chip = self._catalog_chipset(value) if value else ""
        self._auto_target_serial = ""
        previous_model = self._firmware_model
        self._firmware_model = value
        self._loader_variant = ""
        if chip:
            self._firmware_chipset = chip
            self._firmware_chipset_manually_selected = False
        elif previous_model or not value or not self._firmware_chipset_manually_selected:
            self._firmware_chipset = ""
            self._firmware_chipset_manually_selected = False
        self._invalidate_firmware_plan()
        self.firmwareTargetChanged.emit()
        self._append(f"Target model selected: {value or 'Auto/unknown'}; chipset: {chip or 'not selected'}.")

    @Slot(str)
    def setFirmwareChipset(self, value: str) -> None:
        value = value.strip().lower().replace(" ", "")
        if value == self._firmware_chipset:
            self._firmware_chipset_manually_selected = bool(value)
            return
        # An explicit loader choice must not replace the hardware chipset.
        cpu = value.replace("kirin","hisi",1) if value.startswith("kirin") else value
        if cpu in self.loaderVariantOptions:
            self.setLoaderVariant(cpu)
            return
        self._auto_target_serial = ""
        self._loader_variant = ""
        self._firmware_chipset_manually_selected = bool(value)
        known = self._catalog_chipset(self._firmware_model)
        from .fastboot_identity import canonical_chipset
        if value and known and canonical_chipset(known) != canonical_chipset(value):
            family = resolve_loader(self.app_root, known)
            cpu = value.replace("kirin","hisi",1) if value.startswith("kirin") else value
            if cpu not in family.candidate_families:
                self._append("Chipset conflicts with the selected model; clearing the model selection.", "GUARD")
                self._firmware_model = ""
        self._firmware_chipset = value
        self._invalidate_firmware_plan()
        self.firmwareTargetChanged.emit()
        self._append(f"Target chipset selected: {value or 'Detect from device/package'}.")

    @Slot(str)
    def selectDeviceProfile(self, model: str) -> None:
        """One shared selector for Service Center, Flash and reference pages."""
        self.setFirmwareModel(model)

    @Slot(result=bool)
    def confirmFirmwareFlash(self) -> bool:
        if self._busy or not self._firmware_plan_hash:
            return False
        self._start_action_display()
        self.registry.begin_async("flash_firmware")
        self._busy = True
        self.operationBusyChanged.emit()
        self.firmwarePlanChanged.emit()
        worker = ServiceWorker(ServiceRequest(
            action_id="flash_firmware",
            project_root=self.app_root,
            evidence_journal=self.paths.evidence / "operations.jsonl",
            firmware_path=self._firmware_path,
            firmware_mode=self._firmware_mode,
            firmware_model=self._firmware_model,
            firmware_chipset=self._firmware_chipset,
            firmware_apply=True,
            firmware_plan_hash=self._firmware_plan_hash,
            action_log_dir=self._action_logs_dir(),
        ))
        self._firmware_plan_hash = ""
        self.firmwarePlanChanged.emit()
        worker.signals.progress.connect(self._on_operation_progress)
        worker.signals.finished.connect(self._on_service_finished)
        self._worker = worker
        self._pool.start(worker)
        return True

    @Property(bool, notify=operationBusyChanged)
    def operationBusy(self) -> bool:
        return self._busy

    @Property(str, constant=True)
    def deviceProfilesJson(self) -> str:
        profiles = dict(self._device_profiles)
        try:
            inventory = json.loads((self.app_root / "data" / "kirin_loader_inventory.json").read_text(encoding="utf-8"))
            profiles["loader_families"] = [
                {"cpu": row["cpu"], "container_count": len(row["files"])}
                for row in inventory["families"]
            ]
        except (OSError, ValueError, KeyError, TypeError):
            profiles["loader_families"] = []
        return json.dumps(profiles, sort_keys=True)

    @Property(str, constant=True)
    def testpointCatalogJson(self) -> str:
        return json.dumps(self._testpoint_catalog, sort_keys=True)

    @Property(str, notify=operationSelectionChanged)
    def selectedOperationLabel(self) -> str:
        return self._selected_operation_label

    @Slot(str)
    def setFirmwarePath(self, path: str) -> None:
        url = QUrl(path)
        self._firmware_path = url.toLocalFile() if url.isLocalFile() else path
        self._invalidate_firmware_plan()
        self.firmwareChanged.emit()
        self._append(f"Firmware package selected: {self._firmware_path}")

    @Slot(str)
    def setFirmwareMode(self, mode: str) -> None:
        if mode not in {"Upgrade", "Downgrade", "Full Flash", "Board Firmware", "Repair"}:
            self._append("Unknown firmware service mode: " + mode, "ERROR")
            return
        self._firmware_mode = mode
        self._invalidate_firmware_plan()
        self.firmwareModeChanged.emit()
        self._append("Firmware mode selected: " + mode + ". A new preflight is required.")

    @Slot(str, str)
    def setSelectedOperation(self, action_id: str, label: str) -> None:
        if action_id not in self.registry.expected_ids():
            self._append(f"UI selected unknown operation: {action_id}", "ERROR")
            return
        normalized = label.strip() or action_id
        if normalized != self._selected_operation_label:
            self._selected_operation_label = normalized
            self.operationSelectionChanged.emit()

    @Slot(str, result=str)
    def expectedServiceInterface(self, model_id: str) -> str:
        for model in self._device_profiles.get("models", []):
            if isinstance(model, dict) and str(model.get("model", "")) == model_id:
                return expected_service_interface(str(model.get("platform", "")))
        return "Unsupported / unknown service interface"

    @Slot(str, result=str)
    def testpointRecordJson(self, model_id: str) -> str:
        record = exact_testpoint_record(self._testpoint_catalog, model_id)
        return json.dumps(record or {}, sort_keys=True)

    @Property(bool, notify=pinoutBusyChanged)
    def pinoutBusy(self) -> bool:
        return self._pinout_busy

    @Property(str, notify=pinoutChanged)
    def pinoutStatus(self) -> str:
        return self._pinout_status

    @Property(str, notify=pinoutChanged)
    def pinoutResultsJson(self) -> str:
        return json.dumps(self._pinout_results, ensure_ascii=False)

    @Property(str, notify=pinoutChanged)
    def pinoutImageJson(self) -> str:
        return json.dumps(self._pinout_image, ensure_ascii=False)

    @Property(str, notify=pinoutChanged)
    def pinoutImageUrl(self) -> str:
        return str(self._pinout_image.get("local_url", ""))

    def _queue_pinout_worker(self, worker: PinoutWorker) -> bool:
        if self._pinout_busy:
            self._pinout_status = "The pinout library is processing another request."
            self.pinoutChanged.emit()
            return False
        self._pinout_busy = True
        self.pinoutBusyChanged.emit()
        worker.signals.finished.connect(self._on_pinout_finished)
        self._pinout_worker = worker
        self._pinout_pool.start(worker)
        return True

    @Slot(str, str, result=bool)
    def browsePinouts(self, brand: str, pinout_type: str) -> bool:
        """List available pinout image references without device operations."""
        if not brand.strip() or pinout_type not in {"test-point", "isp-pinout"}:
            self._pinout_status = "Choose a valid brand and pinout image type."
            self.pinoutChanged.emit()
            return False
        if self._pinout_busy:
            return False
        self._pinout_results = {"source": "https://pinout.thetechguyds.com/", "results": []}
        self._pinout_image = {}
        self._pinout_status = "Loading pinout image library..."
        self.pinoutChanged.emit()
        worker = PinoutWorker(
            self.paths.root / "cache" / "pinouts",
            "browse",
            brand=brand.strip(),
            kind=pinout_type,
        )
        return self._queue_pinout_worker(worker)

    @Slot(str, str, str, result=bool)
    def searchPinouts(self, brand: str, model: str, pinout_type: str) -> bool:
        """Search the trusted site without blocking the Qt UI thread."""
        if not brand.strip() or not model.strip() or pinout_type not in {"test-point", "isp-pinout"}:
            self._pinout_status = "Brand, model and valid pinout type are required."
            self.pinoutChanged.emit()
            return False
        if self._pinout_busy:
            return False
        self._pinout_results = {"source": "https://pinout.thetechguyds.com/", "results": []}
        self._pinout_image = {}
        self._pinout_status = "Searching the trusted pinout library..."
        self.pinoutChanged.emit()
        worker = PinoutWorker(
            self.paths.root / "cache" / "pinouts",
            "search",
            brand=brand.strip(),
            query=model.strip(),
            kind=pinout_type,
        )
        return self._queue_pinout_worker(worker)

    @Slot(str, str, result=bool)
    def loadPinoutImage(self, record_id: str, image_id: str) -> bool:
        """Fetch only an image belonging to a validated pinout record."""
        if self._pinout_busy:
            return False
        self._pinout_image = {}
        self._pinout_status = "Loading pinout image..."
        self.pinoutChanged.emit()
        worker = PinoutWorker(
            self.paths.root / "cache" / "pinouts",
            "image",
            record_id=record_id,
            image_id=image_id,
        )
        return self._queue_pinout_worker(worker)

    @Slot(object)
    def _on_pinout_finished(self, response: dict) -> None:
        if response.get("ok"):
            result = response["result"]
            if response["operation"] in {"search", "browse"}:
                self._pinout_results = result
                count = result.get("result_count", 0)
                if response["operation"] == "browse":
                    self._pinout_status = (
                        f"{count} image records available; select a model to view."
                        + (" (cached catalogue)" if result.get("stale_catalog") else "")
                    )
                else:
                    self._pinout_status = (
                        f"{count} pinout result(s); {result.get('exact_count', 0)} exact match(es)."
                        + (" (cached catalogue)" if result.get("stale_catalog") else "")
                    )
            else:
                self._pinout_image = result
                self._pinout_status = "Pinout image verified and available locally."
        else:
            self._pinout_status = "Pinout library: " + response.get("message", "Request failed.")
        # Result properties become visible before the idle event.
        self._pinout_worker = None
        self._pinout_busy = False
        self.pinoutChanged.emit()
        self.pinoutBusyChanged.emit()

    @Slot(str)
    def registerUiAction(self, action_id: str) -> None:
        if action_id in self.registry.expected_ids():
            self._ui_actions.add(action_id)
        else:
            self._append(f"UI declared unknown action: {action_id}", "ERROR")

    def _clear_pending_terminal(self) -> None:
        if self._pending_terminal is not None:
            self._pending_terminal = None
            self.terminalConfirmationChanged.emit()

    def _start_terminal_worker(
        self,
        text: str,
        *,
        approved: bool = False,
        fingerprint: str = "",
        serial: str = "",
        working_directory: str = "",
    ) -> None:
        self._start_action_display()
        self._terminal_output = (self._terminal_output + "\n" if self._terminal_output else "") + "> " + text + "\n"
        self._terminal_output = self._terminal_output[-18000:]
        self.terminalOutputChanged.emit()
        self._busy = True
        self.operationBusyChanged.emit()
        request = ServiceRequest(
            action_id="terminal_write" if approved else "terminal_read",
            project_root=self.app_root,
            evidence_journal=self.paths.evidence / "operations.jsonl",
            terminal_line=text,
            action_log_dir=self._action_logs_dir(),
            terminal_approved=approved,
            terminal_fingerprint=fingerprint,
            terminal_expected_serial=serial,
            terminal_working_directory=Path(working_directory or self._terminal_cwd),
        )
        worker = ServiceWorker(request)
        worker.signals.progress.connect(self._on_operation_progress)
        worker.signals.finished.connect(self._on_service_finished)
        self._worker = worker
        self._pool.start(worker)

    @Slot(str)
    def submitTerminalLine(self, line: str) -> None:
        text = line.strip()
        if not text:
            return
        if self._busy:
            self._terminal_output += "\nService worker is busy; command not run.\n"
            self.terminalOutputChanged.emit()
            return
        # Every new command supersedes an unapproved previous write.
        self._clear_pending_terminal()
        try:
            directory_action = try_directory_command(text, Path(self._terminal_cwd))
        except ValueError as exc:
            message = str(exc)
            self._terminal_output = (self._terminal_output + "\n" if self._terminal_output else "") + "> " + text + "\n" + message + "\n"
            self._terminal_output = self._terminal_output[-18000:]
            self.terminalOutputChanged.emit()
            self._append("Terminal navigation rejected: " + message, "GUARD")
            return
        if directory_action is not None:
            next_directory, output = directory_action
            old = self._terminal_cwd
            self._terminal_cwd = str(next_directory)
            if self._terminal_cwd != old:
                self.terminalDirectoryChanged.emit()
            self._terminal_output = (self._terminal_output + "\n" if self._terminal_output else "") + "> " + text + "\n" + output + "\n"
            self._terminal_output = self._terminal_output[-18000:]
            self.terminalOutputChanged.emit()
            return
        try:
            command = parse_console(text)
        except ValueError as exc:
            message = str(exc)
            self._terminal_output += "\n" + message + "\n"
            self.terminalOutputChanged.emit()
            self._start_action_display()
            self._append(message, "GUARD")
            self._record_nonservice_action(
                "terminal_read", EngineResult(False, message, ActionState.GUARDED)
            )
            return
        if command.requires_confirmation:
            serial = self._device_snapshot.serial if self._device_snapshot.connected else ""
            command = replace(command, fingerprint=terminal_context_fingerprint(
                command, Path(self._terminal_cwd)
            ))
            self._pending_terminal = (text, command, serial, monotonic(), self._terminal_cwd)
            self.terminalConfirmationChanged.emit()
            self._terminal_output += (
                "\nConfirmation required — no write executed.\n"
                + self.terminalPendingWarning + "\n"
            )
            self.terminalOutputChanged.emit()
            return
        self._start_terminal_worker(text)

    @Slot(result=bool)
    def confirmTerminalCommand(self) -> bool:
        if self._busy or self._pending_terminal is None:
            return False
        text, command, serial, prepared_at, approved_directory = self._pending_terminal
        self._clear_pending_terminal()
        if approved_directory != self._terminal_cwd:
            self._terminal_output += "\nWorking directory changed; submit and approve command again.\n"
            self.terminalOutputChanged.emit()
            return False
        if monotonic() - prepared_at > 120:
            self._terminal_output += "\nConfirmation expired. Submit the command again.\n"
            self.terminalOutputChanged.emit()
            return False
        self._start_terminal_worker(
            text,
            approved=True,
            fingerprint=command.fingerprint,
            serial=serial,
            working_directory=approved_directory,
        )
        return True

    @Slot()
    def cancelTerminalCommand(self) -> None:
        self._clear_pending_terminal()
        self._terminal_output += "\nPending command cancelled; nothing was executed.\n"
        self.terminalOutputChanged.emit()

    @Property("QVariantMap", notify=serviceResultChanged)
    def partitionPlan(self) -> dict:
        return dict(self._partition_plan)

    @Slot(str, str, str, result=bool)
    def startPartition(self, operation: str, name: str, source: str) -> bool:
        if self._busy or not self._device_snapshot.connected or operation not in {"backup","write","restore","erase"}:
            return False
        url=QUrl(source)
        source=url.toLocalFile() if url.isLocalFile() else source
        if operation=="restore" and not name:
            try:
                from .partition_service import SCHEMA
                path=Path(source)
                if not path.is_file() or path.stat().st_size>65536:return False
                data=json.loads(path.read_text(encoding="utf8"))
                if data.get("schema")!=SCHEMA:return False
                name=str(data.get("partition",""))
            except (OSError,ValueError,TypeError):
                return False
        if not name or (operation in {"write","restore"} and not source):return False
        snap=self._device_snapshot
        self._partition_plan={}
        self._partition_request=ServiceRequest(
            action_id="backup_restore",project_root=self.app_root,
            evidence_journal=self.paths.evidence/"operations.jsonl",action_log_dir=self._action_logs_dir(),
            partition_operation=operation,partition_name=name,partition_source=source,
            partition_serial=snap.serial,partition_model=snap.model,partition_chipset=snap.platform)
        self._launch_partition(self._partition_request)
        return True

    def _launch_partition(self,request):
        self._start_action_display()
        self.registry.begin_async("backup_restore")
        self._busy=True
        self.operationBusyChanged.emit()
        self.healthChanged.emit()
        worker=ServiceWorker(request)
        worker.signals.progress.connect(self._on_operation_progress)
        worker.signals.finished.connect(self._on_service_finished)
        self._worker=worker
        self._pool.start(worker)

    @Slot(result=bool)
    def confirmPartition(self) -> bool:
        if self._busy or not self._partition_request or not self._partition_plan:return False
        from dataclasses import replace
        request=replace(self._partition_request,partition_fingerprint=self._partition_plan["fingerprint"])
        self._partition_plan={}
        self._partition_request=None
        self._launch_partition(request)
        return True

    @Slot()
    def cancelPartition(self):
        self._partition_plan={}
        self._partition_request=None
        self.serviceResultChanged.emit()

    @Slot(str, result=str)
    def runAction(self, action_id: str) -> str:
        if action_id not in self.registry.expected_ids():
            message = f"Unknown operation: {action_id}"
            self._append(message, "ERROR")
            return message
        if action_id in SERVICE_OPERATIONS:
            if self._busy:
                return "Huawei service worker is busy; no operation queued."
            self._start_action_display()
            if action_id == "flash_firmware":
                self._invalidate_firmware_plan()
            self.registry.begin_async(action_id)
            if action_id == "read_device":
                self._read_display_active = True
                self._device_report = ""
                self._device_details = {}
                self._device_partitions = []
                self._partition_plan = {}
                self._partition_request = None
                self._device_snapshot = DeviceSnapshot()
                self._operation_status = "Detecting device..."
                self.progressChanged.emit()
                self._last_read_status = "Reading Huawei USB / Fastboot identity..."
                self.deviceChanged.emit()
            self._busy = True
            self.operationBusyChanged.emit()
            self.healthChanged.emit()
            request = ServiceRequest(
                action_id=action_id,
                project_root=self.app_root,
                evidence_journal=self.paths.evidence / "operations.jsonl",
                firmware_path=self._firmware_path,
                firmware_mode=self._firmware_mode,
                firmware_model=self._firmware_model,
                firmware_chipset=self._firmware_chipset,
                action_log_dir=self._action_logs_dir(),
                service_wait=action_id=="flash_firmware" and self._firmware_mode=="Repair",
                service_expected_serial=self._device_snapshot.serial if action_id!="read_device" and self._device_snapshot.interface in {"Fastboot","ADB"} else "",
            )
            worker = ServiceWorker(request)
            worker.signals.progress.connect(self._on_operation_progress)
            worker.signals.finished.connect(self._on_service_finished)
            self._worker = worker
            self._pool.start(worker)
            return f"Started {action_id} in service worker."

        self._start_action_display()
        self._append(f"Action requested: {action_id}")
        try:
            result = self.registry.invoke(action_id)
        except Exception as exc:
            self._append(str(exc), "ERROR")
            self.healthChanged.emit()
            return str(exc)
        assert isinstance(result, EngineResult)
        self._append(result.message, "OK" if result.ok else "GUARD" if result.health_state is ActionState.GUARDED else "INFO")
        self._record_nonservice_action(action_id, result)
        self.healthChanged.emit()
        return result.message

    @Slot(object)
    def _on_service_finished(self, response: ServiceResponse) -> None:
        payload = response.result.payload if isinstance(response.result.payload, dict) else {}
        self._last_service_result = {
            "action_id": response.action_id,
            "ok": response.result.ok,
            "state": response.result.health_state.value,
            "message": response.result.message,
            "payload": payload,
            "preflight_only": bool(payload.get("preflight_only")),
            "write_authorized": payload.get("write_authorized") is True,
            "elapsed_ms": response.elapsed_ms,
            "log_path": response.log_path,
        }
        self._service_results[response.action_id] = self._last_service_result
        if response.action_id=="backup_restore":
            self._partition_plan=dict(payload.get("partition_plan",{})) if response.result.ok else {}
            if not self._partition_plan:self._partition_request=None

        if response.action_id == "flash_firmware":
            from .fastboot_identity import canonical_chipset
            fresh = payload.get("fingerprint") if payload.get("preflight_only") is True else ""
            # A selection can change while the worker is reading a large
            # package. Never arm a confirmation for a stale model/chipset.
            selection_matches = (
                (not self._firmware_model or
                 payload.get("model", "").upper() == self._firmware_model)
                and (not self._firmware_chipset or
                     canonical_chipset(payload.get("chipset", "")) == canonical_chipset(self._firmware_chipset))
                and payload.get("mode") == self._firmware_mode
            )
            self._firmware_plan_hash = (
                fresh if isinstance(fresh, str) and response.result.ok
                and selection_matches else ""
            )
            self.firmwarePlanChanged.emit()
        self.serviceResultChanged.emit()
        if response.action_id in {"terminal_read", "terminal_write"}:
            self._terminal_output += response.result.message + "\n"
            self._terminal_output = self._terminal_output[-18000:]
            self.terminalOutputChanged.emit()
        else:
            self.registry.complete_async(response.action_id, response.result)
        if response.action_id == "read_device":
            self._device_snapshot = response.device_snapshot or DeviceSnapshot()
            self._last_read_status = response.result.message
            from .operation_log import device_read_lines, full_device_report
            self._device_details = dict(payload.get("xray",{}).get("details",{}))
            self._device_partitions = [dict(row) for row in payload.get("partition_inventory",payload.get("xray",{}).get("partitions",[])) if isinstance(row,dict) and row.get("name")]
            self._device_report = full_device_report(self._device_snapshot,response.result)
            self._log_lines = device_read_lines(self._device_snapshot,response.result)
            self.logTextChanged.emit()
            self._read_display_active = False
            if response.result.ok:
                self._apply_detected_target(payload)
            elif self._auto_target_serial:
                self._clear_detected_target()
            self.deviceChanged.emit()
        if response.log_path:
            self._last_action_log_path = response.log_path
            self._last_action_record_path = response.record_path
            self.actionLogSaved.emit()
            # Every line, including the completion result and elapsed time,
            # came from the worker's durable per-action log.
        else:
            self._append(
                response.result.message,
                "OK" if response.result.ok else "GUARD" if response.result.health_state is ActionState.GUARDED else "INFO",
            )
        self._worker = None
        self._busy = False
        if self._service_entry:
            self._service_entry=""
            self.serviceEntryChanged.emit()
        self._progress = 100 if response.result.ok else 0
        self._operation_status = "Complete" if response.result.ok else "Operation ended"
        self.progressChanged.emit()
        self.operationBusyChanged.emit()
        # Property is derived from both plan hash AND busy state. The first
        # notification fired while busy; notify again after the worker ends.
        if response.action_id == "flash_firmware":
            self.firmwarePlanChanged.emit()
        self.healthChanged.emit()

    @Slot(str, result=bool)
    def registerDevice(self, key: str) -> bool:
        if self._busy:
            return False  # Never interrupt a running action's log.
        self._start_action_display()
        if len(key.strip()) < 12:
            message = "Registration key rejected: key is too short."
            self._append(message, "ERROR")
            self._record_nonservice_action(
                "register_device", EngineResult(False, message, ActionState.GUARDED)
            )
            return False
        payload = {"computer_id": self.computerId, "registered_at": datetime.now().isoformat(), "key_hash": __import__("hashlib").sha256(key.encode()).hexdigest()}
        self.paths.registration.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._registered = True
        self.registrationChanged.emit()
        message = "Device registration stored locally."
        self._append(message, "OK")
        # Only result/status is logged. The original registration key never is.
        self._record_nonservice_action(
            "register_device", EngineResult(True, message, ActionState.READY)
        )
        return True

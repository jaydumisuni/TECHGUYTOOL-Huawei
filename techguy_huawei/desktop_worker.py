from __future__ import annotations

"""Qt worker adapter. All Huawei engine calls execute outside the GUI thread."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from threading import Event
from .edl_reconnect import session
from .action_health import ActionState
from .device_engine import EngineResult
from .service_dispatch import ServiceRequest, ServiceResponse, execute


class WorkerSignals(QObject):
    finished = Signal(object)
    progress = Signal(str)


class ServiceWorker(QRunnable):
    def __init__(self, request: ServiceRequest) -> None:
        super().__init__()
        self.request = request
        self.reconnect_cancel = Event()
        self.signals = WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        try:
            with session(self.reconnect_cancel,self.signals.progress.emit):
                response = execute(self.request, progress=self.signals.progress.emit, cancel=self.reconnect_cancel)
        except Exception as exc:
            response = ServiceResponse(
                self.request.action_id,
                EngineResult(
                    False,
                    f"Service worker failed: {type(exc).__name__}: {exc}",
                    ActionState.FAILED,
                ),
            )
        self.signals.finished.emit(response)


class UsbPresenceWorker(QRunnable):
    """Read USB inventory off the GUI thread; never launch a repair."""
    def __init__(self):
        super().__init__()
        self.signals=WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self):
        from .usb_presence import observe
        try: report=observe()
        except Exception: report=None
        self.signals.finished.emit(report)


class HealthAuditWorker(QRunnable):
    """Run the Rust action-health executable without blocking Qt's GUI thread."""

    def __init__(self, executable, manifest) -> None:
        super().__init__()
        self.executable = executable
        self.manifest = manifest
        self.signals = WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        import json
        import os
        import subprocess

        report = None
        if self.executable.is_file():
            try:
                proc = subprocess.run(
                    [str(self.executable), str(self.manifest)],
                    shell=False,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    # Rust audit is a background console executable, not a UI terminal.
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                report = (
                    json.loads(proc.stdout) if proc.returncode == 0
                    else {"ok": False, "error": proc.stderr.strip() or "Health audit failed"}
                )
            except Exception as exc:
                report = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        self.signals.finished.emit(report)


class PinoutWorker(QRunnable):
    """Independent image/catalog worker: no device commands and no QML I/O."""

    def __init__(
        self,
        cache_root,
        operation: str,
        *,
        brand: str = "",
        query: str = "",
        kind: str = "test-point",
        record_id: str = "",
        image_id: str = "",
    ) -> None:
        super().__init__()
        self.cache_root = cache_root
        self.operation = operation
        self.brand = brand
        self.query = query
        self.kind = kind
        self.record_id = record_id
        self.image_id = image_id
        self.signals = WorkerSignals()
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        from .pinout_provider import PinoutProvider, PinoutProviderError
        try:
            provider = PinoutProvider(self.cache_root)
            if self.operation == "search":
                result = provider.search(self.brand, self.query, self.kind)
            elif self.operation == "browse":
                result = provider.browse(self.brand, self.kind)
            elif self.operation == "image":
                result = provider.fetch_image(self.record_id, self.image_id)
            else:
                raise PinoutProviderError("Unknown pinout request.")
            self.signals.finished.emit({
                "ok": True,
                "operation": self.operation,
                "result": result,
                "message": "Pinout " + self.operation + " completed.",
            })
        except (PinoutProviderError, OSError, ValueError) as exc:
            self.signals.finished.emit({
                "ok": False,
                "operation": self.operation,
                "result": {},
                "message": str(exc),
            })
        except Exception as exc:
            # A provider defect must never strand the UI in a busy state.
            self.signals.finished.emit({
                "ok": False,
                "operation": self.operation,
                "result": {},
                "message": "Pinout worker failed: " + type(exc).__name__,
            })

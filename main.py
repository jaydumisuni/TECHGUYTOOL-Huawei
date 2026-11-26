from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
import tempfile
import traceback

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from techguy_huawei.backend import Backend


def app_root() -> Path:
    # Nuitka onefile resolves __file__ inside its extraction directory, which is
    # where included data files live. In source mode this remains the repo root.
    return Path(__file__).resolve().parent


def _diagnostic_path() -> Path:
    configured = os.environ.get("TECHGUY_STARTUP_DIAGNOSTIC_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / "TECHGUYTOOL_Huawei_startup_error.json"


def _write_diagnostic(stage: str, *, errors: list[str] | None = None, exception: BaseException | None = None) -> None:
    payload: dict[str, object] = {
        "schema": "techguytool-huawei.startup-diagnostic.v1",
        "stage": stage,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "app_root": str(app_root()),
        "frozen": bool(getattr(sys, "frozen", False)),
        "qml_errors": list(errors or []),
    }
    if exception is not None:
        payload["exception_type"] = type(exception).__name__
        payload["exception"] = str(exception)
        payload["traceback"] = "".join(traceback.format_exception(exception))
    try:
        path = _diagnostic_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        # Diagnostics must never become a new startup failure.
        pass


def main() -> int:
    qml_errors: list[str] = []
    _write_diagnostic("before_qt_application")
    try:
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        app = QGuiApplication(sys.argv)
        _write_diagnostic("qt_application_ready")
        app.setOrganizationName("THETECHGUY DIGITAL SOLUTIONS")
        app.setApplicationName("TECHGUYTOOL Huawei")
        root = app_root()
        icon = root / "assets" / "brand" / "techguy_logo.svg"
        if icon.is_file():
            app.setWindowIcon(QIcon(str(icon)))
        engine = QQmlApplicationEngine()
        engine.warnings.connect(lambda warnings: qml_errors.extend(error.toString() for error in warnings))
        backend = Backend(root)
        _write_diagnostic("backend_ready")
        engine.rootContext().setContextProperty("backend", backend)
        # In source mode never load a stale compiled QML resource module.
        if not getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None):
            qml = root / "qml" / "Main.qml"
            _write_diagnostic("loading_filesystem_qml")
            engine.load(QUrl.fromLocalFile(str(qml)))
        else:
            try:
                from techguy_huawei import resources_rc  # type: ignore
                _ = resources_rc
                _write_diagnostic("loading_compiled_qml")
                engine.load(QUrl("qrc:/qml/Main.qml"))
            except ImportError:
                qml = root / "qml" / "Main.qml"
                _write_diagnostic("loading_filesystem_qml")
                engine.load(QUrl.fromLocalFile(str(qml)))
        if not engine.rootObjects():
            _write_diagnostic("qml_root_missing", errors=qml_errors)
            return 1
        _write_diagnostic("qml_root_ready", errors=qml_errors)
        if os.environ.get("TECHGUY_STARTUP_PROBE") == "1":
            return 0
        return app.exec()
    except BaseException as exc:
        _write_diagnostic("startup_exception", errors=qml_errors, exception=exc)
        return 1


def xray_worker(arguments: list[str]) -> int:
    from contextlib import redirect_stdout, redirect_stderr
    from techguy_huawei.xray_read_device import bundled_source
    if len(arguments) != 1:
        return 2
    job = Path(arguments[0]).resolve()
    if not job.is_dir():
        return 2
    with (job / "scanner-summary.json").open("w", encoding="utf-8") as out, (job / "scanner-stderr.txt").open("w", encoding="utf-8") as err:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                source = bundled_source(app_root())
                sys.path.insert(0, str(source))
                from ttg_device_xray.cli import main as scan
                return scan(["scan", "--deep", "--mission", "huawei-read-device", "--output", str(job)])
            except Exception:
                traceback.print_exc()
                return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--xray-worker":
        raise SystemExit(xray_worker(sys.argv[2:]))
    raise SystemExit(main())

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QSG_RHI_BACKEND", "software")
os.environ.setdefault("QT_OPENGL", "software")

import shiboken6
from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, Qt, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QPainter, QRawFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.backend import Backend

APPROVED_STATES = [
    ("Firmware Flash", "01-firmware-flash.png"),
    ("Settings", "02-settings.png"),
    ("About", "03-about.png"),
    ("Fix Drivers", "04-fix-drivers.png"),
    ("Register Device", "05-register-device.png"),
    ("Testpoint / Pinout Library", "06-testpoint-pinout-library.png"),
    ("Terminal", "07-terminal.png"),
]


def load_visual_qa_fonts(app: QGuiApplication) -> dict[str, object]:
    """Make the headless Windows renderer use the same UI fonts as a real desktop."""
    loaded_files: list[str] = []
    loaded_families: list[str] = []
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        font_dir = windir / "Fonts"
        for filename in ("segoeui.ttf", "seguisym.ttf", "seguiemj.ttf", "consola.ttf"):
            path = font_dir / filename
            if not path.is_file():
                continue
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id < 0:
                raise SystemExit(f"Failed to register required visual-QA font: {path}")
            loaded_files.append(str(path))
            loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))

    available = set(QFontDatabase.families())
    for required_family in ("Segoe UI", "Consolas"):
        if required_family not in available:
            raise SystemExit(f"{required_family} is unavailable to the visual-QA renderer")

    app.setFont(QFont("Segoe UI", 10))
    raw = QRawFont.fromFont(QFont("Segoe UI", 12))
    if not raw.isValid():
        raise SystemExit("Segoe UI did not resolve to a valid raw font")
    required = "TECHGUY TOOL HUAWEI Service Center Firmware Flash Testpoint Pinout 0123456789"
    missing = sorted({char for char in required if not char.isspace() and not raw.supportsCharacter(char)})
    if missing:
        raise SystemExit(f"Segoe UI is missing required Latin glyphs: {missing!r}")

    return {
        "loaded_files": loaded_files,
        "loaded_families": sorted(set(loaded_families)),
        "default_family": app.font().family(),
    }


def as_quick_window(window: object) -> QQuickWindow:
    if isinstance(window, QQuickWindow):
        return window
    pointer = shiboken6.getCppPointer(window)[0]
    quick_window = shiboken6.wrapInstance(pointer, QQuickWindow)
    if quick_window is None:
        raise SystemExit("Could not wrap a QML window as QQuickWindow")
    return quick_window


def find_named(root: QObject, name: str) -> QObject:
    obj = root.findChild(QObject, name, Qt.FindChildrenRecursively)
    if obj is None:
        raise SystemExit(f"Visual-QA object was not found: {name}")
    return obj


def invoke(obj: QObject, method: str) -> None:
    if not QMetaObject.invokeMethod(obj, method, Qt.DirectConnection):
        raise SystemExit(f"Could not invoke {method} on {obj.objectName()}")
    QCoreApplication.processEvents()
    QTest.qWait(350)


def capture_main(window: QQuickWindow, path: Path) -> tuple[int, int]:
    image = window.grabWindow()
    if image.isNull():
        raise SystemExit(f"Failed to capture {path.name}")
    if not image.save(str(path), "PNG"):
        raise SystemExit(f"Failed to save {path}")
    return image.width(), image.height()


def capture_terminal(main_window: QQuickWindow, terminal: QObject, path: Path) -> tuple[int, int]:
    invoke(terminal, "show")
    terminal_window = as_quick_window(terminal)
    QCoreApplication.processEvents()
    QTest.qWait(500)
    main_image = main_window.grabWindow()
    terminal_image = terminal_window.grabWindow()
    if main_image.isNull() or terminal_image.isNull():
        raise SystemExit("Failed to capture terminal composition")

    x = 160
    y = 640
    painter = QPainter(main_image)
    painter.fillRect(x - 1, y - 29, terminal_image.width() + 2, 29, Qt.black)
    painter.setPen(Qt.lightGray)
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(x + 10, y - 10, "TECHGUY Fastboot Terminal")
    painter.drawImage(x, y, terminal_image)
    painter.end()
    invoke(terminal, "hide")
    if not main_image.save(str(path), "PNG"):
        raise SystemExit(f"Failed to save {path}")
    return main_image.width(), main_image.height()


def main() -> int:
    output = ROOT / "visual-qa"
    output.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    app = QGuiApplication(sys.argv[:1])
    font_evidence = load_visual_qa_fonts(app)
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda items: warnings.extend(item.toString() for item in items))
    backend = Backend(ROOT)
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        raise SystemExit("Main.qml did not create a root object")

    root = engine.rootObjects()[0]
    root.setProperty("width", 1586)
    root.setProperty("height", 992)
    root.setProperty("visible", True)
    QCoreApplication.processEvents()
    QTest.qWait(700)
    main_window = as_quick_window(root)

    settings = find_named(root, "settingsMenu")
    about = find_named(root, "aboutDialog")
    drivers = find_named(root, "driverDialog")
    register = find_named(root, "registerDialog")
    testpoint = find_named(root, "testpointDialog")
    terminal = find_named(root, "terminalDialog")

    captures: list[dict[str, object]] = []
    warning_cursor = len(warnings)

    def record(title: str, filename: str, size: tuple[int, int]) -> None:
        nonlocal warning_cursor
        state_warnings = warnings[warning_cursor:]
        warning_cursor = len(warnings)
        captures.append(
            {
                "title": title,
                "file": filename,
                "width": size[0],
                "height": size[1],
                "qml_warnings": state_warnings,
            }
        )

    root.setProperty("pageTitle", "Firmware Flash")
    root.setProperty("pageIndex", 2)
    QCoreApplication.processEvents()
    QTest.qWait(500)
    record("Firmware Flash", APPROVED_STATES[0][1], capture_main(main_window, output / APPROVED_STATES[0][1]))

    root.setProperty("pageTitle", "Service Center")
    root.setProperty("pageIndex", 0)
    QCoreApplication.processEvents()
    QTest.qWait(500)

    invoke(settings, "open")
    record("Settings", APPROVED_STATES[1][1], capture_main(main_window, output / APPROVED_STATES[1][1]))
    invoke(settings, "close")

    invoke(about, "open")
    record("About", APPROVED_STATES[2][1], capture_main(main_window, output / APPROVED_STATES[2][1]))
    invoke(about, "close")

    invoke(drivers, "open")
    record("Fix Drivers", APPROVED_STATES[3][1], capture_main(main_window, output / APPROVED_STATES[3][1]))
    invoke(drivers, "close")

    invoke(register, "open")
    record("Register Device", APPROVED_STATES[4][1], capture_main(main_window, output / APPROVED_STATES[4][1]))
    invoke(register, "close")

    invoke(testpoint, "open")
    record("Testpoint / Pinout Library", APPROVED_STATES[5][1], capture_main(main_window, output / APPROVED_STATES[5][1]))
    invoke(testpoint, "close")

    record("Terminal", APPROVED_STATES[6][1], capture_terminal(main_window, terminal, output / APPROVED_STATES[6][1]))

    manifest = {
        "schema": "techguytool-huawei.final-ui-capture.v4",
        "source_revision": os.environ.get("GITHUB_SHA", "local"),
        "expected_size": [1586, 992],
        "renderer": "qt-quick-software-scenegraph",
        "font_evidence": font_evidence,
        "approved_state_order": [title for title, _ in APPROVED_STATES],
        "captures": captures,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    bad = [entry for entry in captures if entry["width"] != 1586 or entry["height"] != 992 or entry["qml_warnings"]]
    if bad:
        print(json.dumps(bad, indent=2))
        raise SystemExit("Approved-state capture dimensions or QML warning contract failed")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QRawFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.backend import Backend

STATES = [
    (0, "Service Center", "service-center.png"),
    (1, "Device Information", "device-information.png"),
    (2, "Firmware Flash", "firmware-flash.png"),
    (3, "Partition Manager", "partition-manager.png"),
    (4, "Backup & Restore", "backup-restore.png"),
    (5, "Operation History", "operation-history.png"),
]


def load_visual_qa_fonts(app: QGuiApplication) -> dict[str, object]:
    """Make the headless Windows renderer use the same UI fonts as a real desktop.

    The offscreen platform can otherwise resolve a family name but render missing-glyph
    boxes. Explicit application-font registration makes the visual artifact meaningful.
    """
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
    if "Segoe UI" not in available:
        raise SystemExit("Segoe UI is unavailable to the visual-QA renderer")
    if "Consolas" not in available:
        raise SystemExit("Consolas is unavailable to the visual-QA renderer")

    app.setFont(QFont("Segoe UI", 10))
    raw = QRawFont.fromFont(QFont("Segoe UI", 12))
    if not raw.isValid():
        raise SystemExit("Segoe UI did not resolve to a valid raw font")
    required = "TECHGUY TOOL HUAWEI Service Center Firmware Flash 0123456789"
    missing = sorted({char for char in required if not char.isspace() and not raw.supportsCharacter(char)})
    if missing:
        raise SystemExit(f"Segoe UI is missing required Latin glyphs: {missing!r}")

    return {
        "loaded_files": loaded_files,
        "loaded_families": sorted(set(loaded_families)),
        "default_family": app.font().family(),
    }


def as_quick_window(window: object) -> QQuickWindow:
    pointer = shiboken6.getCppPointer(window)[0]
    quick_window = shiboken6.wrapInstance(pointer, QQuickWindow)
    if quick_window is None:
        raise SystemExit("Could not wrap the QML ApplicationWindow as QQuickWindow")
    return quick_window


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

    window = engine.rootObjects()[0]
    window.setProperty("width", 1586)
    window.setProperty("height", 992)
    window.setProperty("visible", True)
    QCoreApplication.processEvents()
    QTest.qWait(700)
    quick_window = as_quick_window(window)

    captures: list[dict[str, object]] = []
    warning_cursor = len(warnings)
    for index, title, filename in STATES:
        window.setProperty("pageTitle", title)
        window.setProperty("pageIndex", index)
        QCoreApplication.processEvents()
        QTest.qWait(700)
        image = quick_window.grabWindow()
        if image.isNull():
            raise SystemExit(f"Failed to capture {title}")
        target = output / filename
        if not image.save(str(target), "PNG"):
            raise SystemExit(f"Failed to save {target}")
        state_warnings = warnings[warning_cursor:]
        warning_cursor = len(warnings)
        captures.append(
            {
                "page_index": index,
                "title": title,
                "file": filename,
                "width": image.width(),
                "height": image.height(),
                "qml_warnings": state_warnings,
            }
        )

    manifest = {
        "schema": "techguytool-huawei.final-ui-capture.v2",
        "source_revision": os.environ.get("GITHUB_SHA", "local"),
        "expected_size": [1586, 992],
        "renderer": "qt-quick-software-scenegraph",
        "font_evidence": font_evidence,
        "captures": captures,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    bad = [entry for entry in captures if entry["width"] != 1586 or entry["height"] != 992 or entry["qml_warnings"]]
    if bad:
        print(json.dumps(bad, indent=2))
        raise SystemExit("Visual capture dimensions or QML warning contract failed")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

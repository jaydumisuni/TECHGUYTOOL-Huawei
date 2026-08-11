from __future__ import annotations

import json
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
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


def main() -> int:
    output = ROOT / "visual-qa"
    output.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    app = QGuiApplication(sys.argv[:1])
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
    QTest.qWait(500)

    captures: list[dict[str, object]] = []
    warning_cursor = len(warnings)
    for index, title, filename in STATES:
        window.setProperty("pageTitle", title)
        window.setProperty("pageIndex", index)
        QCoreApplication.processEvents()
        QTest.qWait(500)
        image = window.grabWindow()
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
        "schema": "techguytool-huawei.final-ui-capture.v1",
        "source_revision": os.environ.get("GITHUB_SHA", "local"),
        "expected_size": [1586, 992],
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

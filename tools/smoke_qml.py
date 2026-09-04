from __future__ import annotations

import os
from pathlib import Path
import sys

import shiboken6

os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from techguy_huawei.backend import Backend


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "proof"


def as_quick_window(window: object) -> QQuickWindow:
    if isinstance(window, QQuickWindow):
        return window
    pointer = shiboken6.getCppPointer(window)[0]
    quick_window = shiboken6.wrapInstance(pointer, QQuickWindow)
    if quick_window is None:
        raise RuntimeError("Could not wrap QML root window as QQuickWindow")
    return quick_window


def main() -> int:
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    backend = Backend(ROOT)
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("QML root object was not created", file=sys.stderr)
        return 1
    window = as_quick_window(engine.rootObjects()[0])
    PROOF.mkdir(parents=True, exist_ok=True)

    def capture() -> None:
        image = window.grabWindow()
        if image.isNull():
            print("QML window capture returned a null image", file=sys.stderr)
            app.exit(2)
            return
        output = PROOF / "qml-main.png"
        if not image.save(str(output)):
            print(f"Failed to save {output}", file=sys.stderr)
            app.exit(3)
            return
        print(f"QML smoke proof saved: {output} ({image.width()}x{image.height()})")
        app.quit()

    QTimer.singleShot(1200, capture)
    QTimer.singleShot(15000, lambda: app.exit(4))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

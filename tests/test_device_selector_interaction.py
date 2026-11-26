from pathlib import Path
from types import SimpleNamespace
from PySide6.QtCore import QObject,Qt,QPoint,QPointF,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem
import techguy_huawei.backend as bm
from techguy_huawei.backend import Backend

import pytest


def test_selector_mouse_keyboard_search_and_dropdown(monkeypatch):
    import os,sys,subprocess
    if os.environ.get("TTG_ISOLATED_QT_SELECTOR")!="1":
        env=dict(os.environ,TTG_ISOLATED_QT_SELECTOR="1",QT_QPA_PLATFORM="offscreen",QT_QUICK_CONTROLS_STYLE="Basic")
        proc=subprocess.run([sys.executable,"-m","pytest","-q",str(Path(__file__).resolve())],env=env,capture_output=True,text=True,timeout=45)
        assert proc.returncode==0,proc.stdout+proc.stderr
        return

    r=Path(__file__).resolve().parents[1]
    tmp=r/".workspace"/".tmp"/"selector-qt-test"
    tmp.mkdir(parents=True,exist_ok=True)
    monkeypatch.setattr(bm.AppPaths, 'resolve', lambda:SimpleNamespace(root=tmp,evidence=tmp,logs=tmp,registration=tmp/'registration.json'))
    monkeypatch.setattr(bm.Backend, '_audit_runtime_wiring', lambda self:None)
    app=QGuiApplication.instance() or QGuiApplication([])
    backend=Backend(r)
    backend.health_timer.stop()
    engine=QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend",backend)
    warnings=[]
    engine.warnings.connect(lambda errors:warnings.extend(str(x) for x in errors))
    engine.load(QUrl.fromLocalFile(str(r/"qml"/"Main.qml")))
    win=engine.rootObjects()[0]
    app.processEvents()
    header=win.findChild(QObject,"serviceCenterDeviceTargetSelector")
    print("DEBUG_QML_WARNINGS",warnings,flush=True)
    print("DEBUG_OBJECTS",[(x.objectName(),x.metaObject().className()) for x in win.findChildren(QObject) if "device" in x.objectName().lower() or "page" in x.objectName().lower() or "search" in x.objectName().lower()][:50],flush=True)
    assert header is not None,"Service Center selector did not instantiate"
    toggle=win.findChild(QQuickItem,"deviceSelectorChipset")
    search=win.findChild(QQuickItem,"deviceTargetSearchInput")
    popup=win.findChild(QObject,"deviceTargetSuggestions")
    assert toggle is not None and search is not None and popup is not None
    def center(item):
        pos=item.mapToScene(QPointF(item.width()/2,item.height()/2))
        return QPoint(int(pos.x()),int(pos.y()))
    print("UI_LOADED",{"warnings":warnings,"header_mode":header.property("selectedBy"),"chipset_button_scene":(center(toggle).x(),center(toggle).y()),"input_scene":(center(search).x(),center(search).y())},flush=True)
    QTest.mouseClick(win, Qt.LeftButton,Qt.NoModifier,center(toggle))
    app.processEvents()
    print("AFTER_CHIPSET_CLICK",header.property("selectedBy"),flush=True)
    assert header.property("selectedBy")=="CHIPSET","Chipset button click not routed"
    QTest.mouseClick(win, Qt.LeftButton,Qt.NoModifier,center(search))
    app.processEvents()
    for letter in "kirin980":
        QTest.keyClick(win, Qt.Key(ord(letter.upper())), Qt.NoModifier)
    app.processEvents()
    print("AFTER_SEARCH_TEXT",header.property("queryText"),"popup_visible",popup.property("visible"),flush=True)
    QTest.keyClick(win,Qt.Key_Return)
    app.processEvents()
    print("AFTER_CHIPSET_SUBMIT",backend.firmwareChipset,header.property("selectedBy"),flush=True)
    assert backend.firmwareChipset=="kirin980","Chipset submit did not reach backend"
    model=win.findChild(QQuickItem,"deviceSelectorModel")
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(model))
    app.processEvents()
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(search))
    app.processEvents()
    for letter in "ELE-L29":
        code = Qt.Key_Minus if letter=="-" else Qt.Key(ord(letter.upper()))
        QTest.keyClick(win, code, Qt.ShiftModifier if letter.isupper() else Qt.NoModifier)
    app.processEvents()
    QTest.keyClick(win,Qt.Key_Return)
    app.processEvents()
    print("AFTER_MODEL_SUBMIT",backend.firmwareModel,backend.firmwareChipset,flush=True)
    assert backend.firmwareModel=="ELE-L29" and backend.firmwareChipset=="kirin980","Model mapping did not bind"

    # Exercise actual suggestion-item clicks, not only typed exact ids.
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(toggle))
    app.processEvents()
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(search))
    app.processEvents()
    for char in "970":QTest.keyClick(win,ord(char))
    app.processEvents()
    choices=win.findChild(QQuickItem,"deviceTargetSuggestionList")
    assert popup.property("visible") is True
    pos=choices.mapToScene(QPointF(55,20))
    print("CHIP_SUGGESTION_CLICK",pos.x(),pos.y(),"popupWidth",popup.property("width"),flush=True)
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,QPoint(int(pos.x()),int(pos.y())))
    app.processEvents()
    print("AFTER_CHIP_SUGGESTION",backend.firmwareModel,backend.firmwareChipset,flush=True)
    assert backend.firmwareModel=="" and backend.firmwareChipset=="kirin970"
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(model))
    app.processEvents()
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(search))
    app.processEvents()
    for char in "P30":QTest.keyClick(win,ord(char))
    app.processEvents()
    assert popup.property("visible") is True
    pos=choices.mapToScene(QPointF(55,20))
    QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,QPoint(int(pos.x()),int(pos.y())))
    app.processEvents()
    print("AFTER_MODEL_SUGGESTION",backend.firmwareModel,backend.firmwareChipset,flush=True)
    assert backend.firmwareModel=="VOG-L29" and backend.firmwareChipset=="kirin980"
    # Verify the same interactive selector is instantiated on every routed page.
    for index in (1,2,3,4,5):
        win.setProperty("pageIndex",index)
        for _ in range(3):app.processEvents()
        h=win.findChild(QObject,"sharedDeviceSearchHeader")
        assert h is not None,(index,[w for w in warnings if "DeviceSearchHeader" in w])
        assert h.property("interactiveTarget")==True,index
    print("SIX_PAGES_SELECTOR_ACTIVE_PASS",flush=True)

    print("UI_CLICK_AND_SEARCH_PASS",flush=True)

    backend.setFirmwareChipset("kirin980")
    backend.setFirmwareModel("XYZ-L99")
    assert backend.firmwareModel=="XYZ-L99" and backend.firmwareChipset==""
    backend.setFirmwareModel("")
    backend.setFirmwareChipset("kirin980")
    backend.setFirmwareModel("XYZ-L99")
    assert backend.firmwareChipset=="kirin980"
    from PySide6.QtCore import QMetaObject
    dialog=win.findChild(QObject,"registerDialog")
    QMetaObject.invokeMethod(dialog,"open")
    QTest.qWait(150);app.processEvents()
    content=dialog.property("contentItem")
    buttons=[child for child in content.findChildren(QQuickItem) if "GlowButton" in child.metaObject().className() and child.property("text") in {"CANCEL","REGISTER DEVICE"}]
    assert len(buttons)==2
    for button in buttons:
        y=button.mapToItem(content,QPointF(0,0)).y()
        assert y>=0 and y+button.height()<=content.height()+1
    dialog.setProperty("visible",False)
    win.close()
    print("MANUAL_MODEL_ORDER_PASS",flush=True)

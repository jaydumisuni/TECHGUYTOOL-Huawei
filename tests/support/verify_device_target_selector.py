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

r=Path(r"D:\projects\TECHGUYTOOL-Huawei")
tmp=r/".workspace"/".tmp"/"selector-qt-test"
tmp.mkdir(parents=True,exist_ok=True)
bm.AppPaths.resolve=lambda:SimpleNamespace(root=tmp,evidence=tmp,logs=tmp,registration=tmp/"registration.json")
bm.Backend._audit_runtime_wiring=lambda self:None
app=QGuiApplication([])
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

# An unlisted exact model remains selectable without a fake catalogue record.
win.setProperty("pageIndex",0)
for _ in range(3):app.processEvents()
QTest.qWait(200)
for _ in range(3):app.processEvents()
manual_model=win.findChild(QQuickItem,"deviceSelectorModel")
manual_chip=win.findChild(QQuickItem,"deviceSelectorChipset")
manual_input=win.findChild(QQuickItem,"deviceTargetSearchInput")
print("MANUAL_BEFORE",win.property("pageIndex"),manual_input.property("text"),manual_input.property("activeFocus"),(center(manual_input).x(),center(manual_input).y()),flush=True)
QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(manual_model))
app.processEvents()
print("MANUAL_AFTER_TAB",manual_input.property("text"),manual_input.property("activeFocus"),flush=True)
QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(manual_input))
app.processEvents()
print("MANUAL_AFTER_FIELD",manual_input.property("text"),manual_input.property("activeFocus"),flush=True)
for char in "HON-X99":
    QTest.keyClick(win,Qt.Key_Minus if char=="-" else ord(char.upper()))
app.processEvents()
print("MANUAL_AFTER_TYPING",manual_input.property("text"),manual_input.property("activeFocus"),flush=True)
QTest.keyClick(win,Qt.Key_Return)
app.processEvents()
print("MANUAL_MODEL_OBSERVED",backend.firmwareModel,backend.firmwareChipset,manual_input.property("text"),flush=True)
assert backend.firmwareModel=="HON-X99" and backend.firmwareChipset==""
QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(manual_chip))
app.processEvents()
QTest.mouseClick(win,Qt.LeftButton,Qt.NoModifier,center(manual_input))
app.processEvents()
for char in "kirin990":QTest.keyClick(win,ord(char.upper()))
app.processEvents()
QTest.keyClick(win,Qt.Key_Return)
app.processEvents()
assert backend.firmwareModel=="HON-X99" and backend.firmwareChipset=="kirin990"
print("UNLISTED_MODEL_EXACT_CHIPSET_SELECTION_PASS",flush=True)

print("UI_CLICK_AND_SEARCH_PASS",flush=True)

backend.setFirmwareChipset("kirin980")
backend.setFirmwareModel("XYZ-L99")
assert backend.firmwareModel=="XYZ-L99" and backend.firmwareChipset==""
backend.setFirmwareModel("")
backend.setFirmwareChipset("kirin980")
backend.setFirmwareModel("XYZ-L99")
assert backend.firmwareChipset=="kirin980"
print("MANUAL_MODEL_ORDER_PASS",flush=True)

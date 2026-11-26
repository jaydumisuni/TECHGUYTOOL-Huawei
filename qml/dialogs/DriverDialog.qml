import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Dialog {
    id: root
    objectName: "driverDialog"
    property var scanResult: ({})
    function refreshDriverResult() {
        try { scanResult = JSON.parse(backend.serviceResultJson("fix_drivers")) }
        catch (e) { scanResult = ({}) }
    }
    function interfaceStatus(name) {
        var rows = (scanResult.payload || {}).interfaces || []
        var tokens = name === "Huawei USB COM 1.0" ? /USB COM|USB SER/i :
                     name === "Huawei Android USB" ? /ADB|Android USB/i :
                     name === "Huawei Fastboot" ? /Fastboot|Bootloader/i : /QDLoader|9008/i
        var hits = rows.filter(function(row){return tokens.test(row.name || "")})
        return hits.length ? hits.map(function(row){return row.status || "Unknown"}).join(", ") :
               scanResult.ok ? "Not present" : "Check required"
    }
    Connections { target: backend; function onServiceResultChanged() { root.refreshDriverResult() } }
    onOpened: refreshDriverResult()
    width: 538
    height: 455
    modal: true
    focus: true
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    padding: 0
    closePolicy: Popup.CloseOnEscape
    background: GlassPanel { panelOpacity: 0.98; borderColor: "#5784a8" }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.preferredWidth: 25 }
            Text { text: "FIX DRIVERS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 22; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            Button { flat: true; text: "×"; font.pixelSize: 24; onClicked: root.close() }
        }
        Repeater {
            model: [
                {name: "Huawei USB COM 1.0", icon: "usb", glyph: "♧"},
                {name: "Huawei Android USB", icon: "driver", glyph: "♙"},
                {name: "Huawei Fastboot", icon: "terminal", glyph: ">_"},
                {name: "Qualcomm HS-USB QDLoader", icon: "connection", glyph: "⌕"}
            ]
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 47
                radius: 6
                color: "#0b1828"
                border.width: 1
                border.color: "#3b5870"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 15
                    anchors.rightMargin: 15
                    Image { source: Qt.resolvedUrl("../../assets/ui-icons/" + modelData.icon + ".svg"); Layout.preferredWidth: 33; Layout.preferredHeight: 30; fillMode: Image.PreserveAspectFit }
                    Text { text: modelData.name; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; Layout.fillWidth: true }
                    Text { text: root.interfaceStatus(modelData.name); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                }
            }
        }
        Text { text: "Uses existing Windows drivers; missing packages require signed drivers."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#20364d" }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "ⓘ"; color: Theme.muted; font.pixelSize: 20 }
            Text { text: root.scanResult.message || "Check and rediscover connected driver interfaces"; wrapMode: Text.WordWrap; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            GlowButton { primary: false; text: "CANCEL"; Layout.preferredWidth: 175; onClicked: root.close() }
            GlowButton { text: "FIX DRIVERS"; enabled: !backend.operationBusy; Layout.preferredWidth: 250; onClicked: backend.runAction("fix_drivers") }
        }
    }
}

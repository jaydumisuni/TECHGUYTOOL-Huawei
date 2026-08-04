import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Dialog {
    id: root
    width: 520
    height: 440
    modal: true
    focus: true
    anchors.centerIn: parent
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
                {name: "Huawei USB COM 1.0", glyph: "♧"},
                {name: "Huawei Android USB", glyph: "♙"},
                {name: "Huawei Fastboot", glyph: ">_"},
                {name: "Qualcomm HS-USB QDLoader", glyph: "⌕"}
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
                    Text { text: modelData.glyph; color: "#8cb5ff"; font.family: "Segoe UI Symbol"; font.pixelSize: 21; Layout.preferredWidth: 33; horizontalAlignment: Text.AlignHCenter }
                    Text { text: modelData.name; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; Layout.fillWidth: true }
                    Text { text: "Check required"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                }
            }
        }
        CheckBox { text: "Remove conflicting driver versions"; font.family: Theme.fontFamily; font.pixelSize: 13 }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#20364d" }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "ⓘ"; color: Theme.muted; font.pixelSize: 20 }
            Text { text: "Connect a device before running driver repair"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.fillWidth: true }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            GlowButton { primary: false; text: "CANCEL"; Layout.preferredWidth: 175; onClicked: root.close() }
            GlowButton { text: "SCAN & FIX DRIVERS"; Layout.preferredWidth: 250; onClicked: backend.runAction("fix_drivers") }
        }
    }
}

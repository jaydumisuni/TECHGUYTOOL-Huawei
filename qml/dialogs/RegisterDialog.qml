import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Dialog {
    id: root
    objectName: "registerDialog"
    width: 520
    // 390 px clips the 48 px action buttons once the two text fields,
    // status row and approved spacing are laid out by Qt Quick Controls.
    // Keep the action row fully inside the dialog in both live and QA renders.
    height: 440
    modal: true
    focus: true
    anchors.centerIn: parent
    padding: 0
    closePolicy: Popup.CloseOnEscape
    background: GlassPanel { panelOpacity: 0.98; borderColor: "#5d6e93" }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 25
        spacing: 13
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.preferredWidth: 30 }
            Text { text: "REGISTER DEVICE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 22; font.weight: Font.Medium; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            Text { text: "♢"; color: Theme.text; font.family: "Segoe UI Symbol"; font.pixelSize: 30; Layout.preferredWidth: 30 }
        }
        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 10
                Text { text: "Device Registration"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 16 }
                Text { text: "Register this computer for TECHGUY TOOL Huawei access."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Text { text: "Computer ID"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                TextField { Layout.fillWidth: true; text: backend.computerId; readOnly: true; selectByMouse: true }
                Text { text: "Registration Key"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                TextField { id: keyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "Enter registration key" }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Status:"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13 }
                    Text { text: backend.registered ? "Registered" : "Not registered"; color: backend.registered ? Theme.green : Theme.red; font.family: Theme.fontFamily; font.pixelSize: 13 }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    GlowButton { primary: false; text: "CANCEL"; Layout.preferredWidth: 135; onClicked: root.close() }
                    GlowButton { text: "REGISTER DEVICE"; Layout.preferredWidth: 200; onClicked: { if (backend.registerDevice(keyField.text)) root.close() } }
                }
            }
        }
    }
}

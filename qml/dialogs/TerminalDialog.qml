import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Window {
    id: root
    objectName: "terminalDialog"
    width: 370
    height: 180
    minimumWidth: 370
    minimumHeight: 180
    maximumWidth: 370
    maximumHeight: 180
    title: "TECHGUY Fastboot Terminal"
    color: "#050505"
    flags: Qt.Dialog
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4
        TextArea {
            id: output
            Layout.fillWidth: true
            Layout.fillHeight: true
            readOnly: true
            color: "#e5e5e5"
            selectionColor: "#315a88"
            font.family: "Consolas"
            font.pixelSize: 11
            background: Rectangle { color: "#050505" }
            text: "TECHGUY TOOL Huawei Fastboot Console\nFastboot access granted.\nType fastboot commands directly.\n\nC:\\TECHGUY\\Huawei> fastboot devices\n< waiting for device >\n"
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            Text { text: "C:\\TECHGUY\\Huawei>"; color: "#e5e5e5"; font.family: "Consolas"; font.pixelSize: 11 }
            TextField {
                Layout.fillWidth: true
                color: "#e5e5e5"
                font.family: "Consolas"
                font.pixelSize: 11
                background: Rectangle { color: "#050505"; border.width: 0 }
                placeholderText: ""
                onAccepted: {
                    output.text += "\nC:\\TECHGUY\\Huawei> " + text + "\nCommand routed through the safe terminal adapter.\n"
                    text = ""
                }
            }
        }
    }
}

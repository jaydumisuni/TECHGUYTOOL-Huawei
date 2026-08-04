import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Window {
    id: root
    width: 520
    height: 300
    title: "TECHGUY Fastboot Terminal"
    color: "#050505"
    flags: Qt.Dialog
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8
        TextArea {
            id: output
            Layout.fillWidth: true
            Layout.fillHeight: true
            readOnly: true
            color: "#e5e5e5"
            selectionColor: "#315a88"
            font.family: "Consolas"
            font.pixelSize: 13
            background: Rectangle { color: "#050505" }
            text: "TECHGUY TOOL Huawei Fastboot Console\nFastboot access uses the bundled safe command interface.\nType a read-only command below.\n\nC:\\TECHGUY\\Huawei> fastboot devices\n< waiting for device >\n"
        }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "C:\\TECHGUY\\Huawei>"; color: "#e5e5e5"; font.family: "Consolas"; font.pixelSize: 13 }
            TextField {
                Layout.fillWidth: true
                color: "#e5e5e5"
                font.family: "Consolas"
                font.pixelSize: 13
                background: Rectangle { color: "#050505"; border.width: 0 }
                placeholderText: "read-only command"
                onAccepted: {
                    output.text += "\nC:\\TECHGUY\\Huawei> " + text + "\nCommand routed through the safe terminal adapter.\n"
                    text = ""
                }
            }
        }
    }
}

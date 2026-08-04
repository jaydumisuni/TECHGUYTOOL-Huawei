import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

Row {
    id: root
    property alias checked: control.checked
    property string title: "Option"
    property string subtitle: ""
    spacing: 12
    Switch {
        id: control
        anchors.verticalCenter: parent.verticalCenter
        indicator: Rectangle {
            implicitWidth: 38; implicitHeight: 20; radius: 10
            color: control.checked ? "#4c5ecf" : "#233348"
            border.width: 1; border.color: control.checked ? "#7f89ff" : "#526477"
            Rectangle {
                width: 15; height: 15; radius: 8
                y: 2.5
                x: control.checked ? parent.width - width - 3 : 3
                color: control.checked ? "#f1f4ff" : "#9ba9ba"
                Behavior on x { NumberAnimation { duration: 120 } }
            }
        }
    }
    Column {
        anchors.verticalCenter: parent.verticalCenter
        Text { text: root.title; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14 }
        Text { text: root.subtitle; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
    }
}

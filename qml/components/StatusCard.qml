import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property string glyph: "□"
    property string iconName: ""
    property string title: "Connection"
    property string value: "Not Connected"
    radius: 8
    color: "#0b1828"
    border.width: 1
    border.color: "#31506d"
    implicitWidth: 196
    implicitHeight: 76
    Row {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12
        Item {
            width: 44; height: 44
            anchors.verticalCenter: parent.verticalCenter
            Image {
                anchors.centerIn: parent
                width: 31; height: 31
                source: root.iconName ? Qt.resolvedUrl("../../assets/ui-icons/" + root.iconName + ".svg") : ""
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: root.iconName !== ""
            }
            Text {
                anchors.fill: parent
                visible: root.iconName === ""
                text: root.glyph
                color: "#91b5ff"
                font.family: "Segoe UI Symbol"
                font.pixelSize: 31
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Text { text: root.title; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
            Text { text: root.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; elide: Text.ElideRight; width: 112 }
        }
    }
}

import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property string glyph: "□"
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
        Text {
            width: 44
            text: root.glyph
            color: "#91b5ff"
            font.family: "Segoe UI Symbol"
            font.pixelSize: 31
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignHCenter
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Text { text: root.title; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
            Text { text: root.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; elide: Text.ElideRight; width: 112 }
        }
    }
}

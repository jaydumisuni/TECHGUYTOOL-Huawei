import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property string glyph: "□"
    property string title: "Connection"
    property string value: "Not Connected"
    radius: 8
    color: "#071522"
    border.width: 1
    border.color: "#477594"
    implicitWidth: 196
    implicitHeight: 76

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#211a3a" }
            GradientStop { position: 0.52; color: "#07121f" }
            GradientStop { position: 1.00; color: "#082b3c" }
        }
        opacity: 0.28
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 7
        anchors.rightMargin: 7
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#8069d8" }
            GradientStop { position: 1.00; color: "#48c9ff" }
        }
        opacity: 0.60
    }

    Row {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12
        Text {
            width: 44
            text: root.glyph
            color: "#8dc8ff"
            font.family: "Segoe UI Symbol"
            font.pixelSize: 32
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignHCenter
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Text { text: root.title; color: "#b8c4d2"; font.family: Theme.fontFamily; font.pixelSize: 13 }
            Text { text: root.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.Medium; elide: Text.ElideRight; width: 112 }
        }
    }
}

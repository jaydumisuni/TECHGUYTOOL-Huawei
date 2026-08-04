import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

Button {
    id: root
    property string glyph: "□"
    property string subtitle: ""
    property bool active: false
    implicitWidth: 236
    implicitHeight: 103
    hoverEnabled: true

    background: Rectangle {
        radius: 9
        color: root.down ? "#15243a" : (root.hovered ? "#11243a" : "#0b1828")
        border.width: root.active ? 2 : 1
        border.color: root.active ? Theme.purple : (root.hovered ? Theme.cyan : "#36526d")
        Rectangle {
            visible: root.active
            width: 6
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            radius: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.purple }
                GradientStop { position: 1.0; color: Theme.cyan }
            }
        }
    }
    contentItem: Row {
        anchors.fill: parent
        anchors.leftMargin: 17
        anchors.rightMargin: 12
        spacing: 14
        Text {
            width: 48
            text: root.glyph
            color: root.active ? "#d27cff" : "#6d9cff"
            font.family: "Segoe UI Symbol"
            font.pixelSize: 39
            horizontalAlignment: Text.AlignHCenter
            anchors.verticalCenter: parent.verticalCenter
        }
        Column {
            width: root.width - 90
            spacing: 5
            anchors.verticalCenter: parent.verticalCenter
            Text {
                width: parent.width
                text: root.text
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 18
                font.weight: Font.Medium
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: root.subtitle
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
        }
    }
}

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

Button {
    id: root
    property string glyph: "□"
    property bool selected: false
    signal selectedClicked()
    height: 68
    width: parent ? parent.width : 280
    hoverEnabled: true
    onClicked: selectedClicked()

    background: Rectangle {
        radius: 8
        color: root.selected ? "#10253b" : (root.hovered ? "#0d1a2a" : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? Theme.cyan : "transparent"
        Rectangle {
            visible: root.selected
            width: 4
            radius: 2
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            color: Theme.cyan
        }
    }
    contentItem: Row {
        anchors.fill: parent
        anchors.leftMargin: 25
        spacing: 19
        Text {
            width: 33
            text: root.glyph
            color: root.selected ? Theme.cyan : "#d5dce4"
            font.family: "Segoe UI Symbol"
            font.pixelSize: 28
            horizontalAlignment: Text.AlignHCenter
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.text
            color: root.selected ? Theme.text : "#d3d8df"
            font.family: Theme.fontFamily
            font.pixelSize: 18
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}

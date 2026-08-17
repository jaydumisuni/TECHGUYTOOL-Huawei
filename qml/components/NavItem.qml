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
        id: navBackground
        radius: 8
        color: root.selected ? "#091b2d" : (root.hovered ? "#0a1725" : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? "#69d8ff" : "transparent"

        Rectangle {
            visible: root.selected
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, parent.radius - 1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#251842" }
                GradientStop { position: 0.42; color: "#0a1b31" }
                GradientStop { position: 1.00; color: "#0b304a" }
            }
            opacity: 0.62
        }

        Rectangle {
            visible: root.selected
            anchors.fill: parent
            anchors.margins: 2
            radius: Math.max(0, parent.radius - 2)
            color: "transparent"
            border.width: 1
            border.color: "#477fb0"
            opacity: 0.52
        }

        Rectangle {
            visible: root.selected
            width: 5
            radius: 2.5
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#a75cff" }
                GradientStop { position: 0.48; color: "#48c7ff" }
                GradientStop { position: 1.0; color: "#31e5ff" }
            }
        }

        Rectangle {
            visible: root.selected
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#a45cff" }
                GradientStop { position: 0.55; color: "#79d5ff" }
                GradientStop { position: 1.00; color: "#2cc8ff" }
            }
            opacity: 0.90
        }
    }

    contentItem: Row {
        anchors.fill: parent
        anchors.leftMargin: 25
        spacing: 19
        Text {
            width: 33
            text: root.glyph
            color: root.selected ? "#75ddff" : "#d8e2ec"
            font.family: "Segoe UI Symbol"
            font.pixelSize: 30
            horizontalAlignment: Text.AlignHCenter
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: root.text
            color: root.selected ? Theme.text : "#dce2ea"
            font.family: Theme.fontFamily
            font.pixelSize: 19
            font.weight: root.selected ? Font.Medium : Font.Normal
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}

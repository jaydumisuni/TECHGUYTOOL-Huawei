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
        color: root.selected ? "#10253b" : (root.hovered ? "#0d1a2a" : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? "#63d5ff" : "transparent"

        Rectangle {
            visible: root.selected
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, parent.radius - 1)
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#18264a" }
                GradientStop { position: 0.46; color: "#0c2034" }
                GradientStop { position: 1.00; color: "#123450" }
            }
            opacity: 0.48
        }

        Rectangle {
            visible: root.selected
            width: 5
            radius: 2.5
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#7e73ff" }
                GradientStop { position: 0.48; color: "#35bdff" }
                GradientStop { position: 1.0; color: "#31e0ff" }
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
                GradientStop { position: 0.00; color: "#776cff" }
                GradientStop { position: 0.55; color: "#53c9ff" }
                GradientStop { position: 1.00; color: "#20a7ff" }
            }
            opacity: 0.72
        }
    }

    contentItem: Row {
        anchors.fill: parent
        anchors.leftMargin: 25
        spacing: 19
        Text {
            width: 33
            text: root.glyph
            color: root.selected ? "#57c8ff" : "#d5dce4"
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

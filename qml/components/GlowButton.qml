import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

Button {
    id: root
    property bool primary: true
    property color accentA: Theme.purple
    property color accentB: Theme.cyan
    implicitHeight: 48
    implicitWidth: 180
    font.family: Theme.fontFamily
    font.pixelSize: 16
    font.weight: Font.Medium

    background: Rectangle {
        radius: 7
        border.width: 1
        border.color: root.enabled ? (root.hovered ? "#a8e5ff" : "#7299e8") : (root.primary ? "#6174ae" : "#3c4e62")
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0.0
                color: root.primary
                    ? Qt.rgba(root.accentA.r, root.accentA.g, root.accentA.b, root.enabled ? (root.down ? 0.60 : 0.80) : 0.48)
                    : "#122033"
            }
            GradientStop {
                position: 1.0
                color: root.primary
                    ? Qt.rgba(root.accentB.r, root.accentB.g, root.accentB.b, root.enabled ? (root.down ? 0.48 : 0.64) : 0.40)
                    : "#0c1726"
            }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -3
            radius: parent.radius + 3
            color: "transparent"
            border.width: root.primary ? 1 : (root.hovered && root.enabled ? 1 : 0)
            border.color: root.primary ? Qt.rgba(0.36, 0.72, 1.0, root.enabled ? 0.26 : 0.14) : Qt.rgba(0.25, 0.75, 1.0, 0.24)
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            height: 1
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#d68bff" }
                GradientStop { position: 1.0; color: "#6ee3ff" }
            }
            opacity: root.primary ? (root.enabled ? 0.72 : 0.42) : 0.0
        }
    }
    contentItem: Text {
        text: root.text
        color: root.enabled ? Theme.text : (root.primary ? "#d7dce8" : "#8894a2")
        font.family: root.font.family
        font.pixelSize: root.font.pixelSize
        font.weight: root.font.weight
        font.letterSpacing: 1.1
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: root.enabled ? 1.0 : 0.86
    }
}

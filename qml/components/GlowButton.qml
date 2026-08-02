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
        border.color: root.enabled ? (root.hovered ? "#9adfff" : "#5f7fd8") : "#324152"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: root.enabled && root.primary ? Qt.rgba(root.accentA.r, root.accentA.g, root.accentA.b, root.down ? 0.58 : 0.76) : "#122033" }
            GradientStop { position: 1.0; color: root.enabled && root.primary ? Qt.rgba(root.accentB.r, root.accentB.g, root.accentB.b, root.down ? 0.45 : 0.60) : "#0c1726" }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: -4
            radius: parent.radius + 4
            color: "transparent"
            border.width: root.hovered && root.enabled ? 2 : 0
            border.color: Qt.rgba(0.25, 0.75, 1.0, 0.30)
        }
    }
    contentItem: Text {
        text: root.text
        color: root.enabled ? Theme.text : "#7c8793"
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        letterSpacing: 1.1
    }
}

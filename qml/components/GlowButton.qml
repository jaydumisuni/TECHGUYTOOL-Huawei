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
            GradientStop { position: 0.00; color: root.enabled && root.primary ? (root.down ? "#6422a2" : "#a035df") : "#122033" }
            GradientStop { position: 0.15; color: root.enabled && root.primary ? (root.down ? "#2d1b77" : "#4d26a3") : "#102033" }
            GradientStop { position: 0.40; color: root.enabled && root.primary ? (root.down ? "#0b164e" : "#102060") : "#102033" }
            GradientStop { position: 0.60; color: root.enabled && root.primary ? (root.down ? "#071938" : "#041b4b") : "#0c1726" }
            GradientStop { position: 0.86; color: root.enabled && root.primary ? (root.down ? "#09284a" : "#06315f") : "#0c1726" }
            GradientStop { position: 1.00; color: root.enabled && root.primary ? (root.down ? "#073659" : "#07527c") : "#0c1726" }
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
        font.family: root.font.family
        font.pixelSize: root.font.pixelSize
        font.weight: root.font.weight
        font.letterSpacing: 1.1
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}

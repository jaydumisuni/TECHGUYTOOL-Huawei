import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property color panelColor: Theme.panel
    property color borderColor: Theme.borderSoft
    property real panelOpacity: 0.84
    radius: 12
    color: Qt.rgba(panelColor.r, panelColor.g, panelColor.b, panelOpacity)
    border.width: 1
    border.color: borderColor

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        border.width: 1
        border.color: "#143f5e"
        opacity: 0.6
    }
}

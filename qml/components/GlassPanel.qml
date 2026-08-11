import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property color panelColor: Theme.panel
    property color borderColor: Theme.borderSoft
    property real panelOpacity: 0.74
    radius: 12
    color: Qt.rgba(panelColor.r, panelColor.g, panelColor.b, panelOpacity)
    border.width: 1
    border.color: borderColor

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#16233f" }
            GradientStop { position: 0.44; color: "#071222" }
            GradientStop { position: 1.0; color: "#050a15" }
        }
        opacity: 0.18
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        border.width: 1
        border.color: "#205a82"
        opacity: 0.72
    }
}

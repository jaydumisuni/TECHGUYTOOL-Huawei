import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property color panelColor: Theme.panel
    property color borderColor: Theme.border
    property real panelOpacity: 0.86
    radius: 12
    color: Qt.rgba(panelColor.r, panelColor.g, panelColor.b, panelOpacity)
    border.width: 1
    border.color: borderColor
    clip: true

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#301443" }
            GradientStop { position: 0.18; color: "#10182b" }
            GradientStop { position: 0.66; color: "#06131f" }
            GradientStop { position: 1.00; color: "#082a40" }
        }
        opacity: 0.30
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        radius: Math.max(0, parent.radius - 2)
        color: "transparent"
        border.width: 1
        border.color: "#58a6d0"
        opacity: 0.44
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.17, 78)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#8d35ff" }
            GradientStop { position: 1.00; color: "transparent" }
        }
        opacity: 0.085
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.16, 72)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "transparent" }
            GradientStop { position: 1.00; color: "#16b9ff" }
        }
        opacity: 0.095
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#ad5aff" }
            GradientStop { position: 0.50; color: "#8fc9ff" }
            GradientStop { position: 1.00; color: "#38d6ff" }
        }
        opacity: 0.70
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: root.radius
        anchors.rightMargin: root.radius
        height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#6b32b7" }
            GradientStop { position: 0.52; color: "#326b9d" }
            GradientStop { position: 1.00; color: "#19a7d8" }
        }
        opacity: 0.34
    }
}

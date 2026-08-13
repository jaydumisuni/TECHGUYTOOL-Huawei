import QtQuick 2.15
import ".."

Rectangle {
    id: root
    property color panelColor: Theme.panel
    property color borderColor: Theme.borderSoft
    property real panelOpacity: 0.70
    radius: 12
    color: Qt.rgba(panelColor.r, panelColor.g, panelColor.b, panelOpacity)
    border.width: 1
    border.color: borderColor
    clip: true

    // Approved glass body: dark translucent centre with a faint purple-to-cyan tint.
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#251337" }
            GradientStop { position: 0.20; color: "#10172a" }
            GradientStop { position: 0.68; color: "#071421" }
            GradientStop { position: 1.00; color: "#08253a" }
        }
        opacity: 0.24
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: Math.max(0, parent.radius - 1)
        color: "transparent"
        border.width: 1
        border.color: "#3f7eaa"
        opacity: 0.64
    }

    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.20, 92)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "#7b2cff" }
            GradientStop { position: 1.00; color: "transparent" }
        }
        opacity: 0.055
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.min(parent.width * 0.18, 86)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: "transparent" }
            GradientStop { position: 1.00; color: "#16a8ff" }
        }
        opacity: 0.07
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
            GradientStop { position: 0.00; color: "#995cff" }
            GradientStop { position: 0.48; color: "#8bbdff" }
            GradientStop { position: 1.00; color: "#2ed0ff" }
        }
        opacity: 0.42
    }

    Image {
        visible: root.width >= 290 && root.width <= 330 && root.height > 600
        source: "../../assets/brand/techguy_mascot.png"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.bottomMargin: 10
        height: 370
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
        cache: true
        z: 20
    }
}

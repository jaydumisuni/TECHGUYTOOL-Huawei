import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

Button {
    id: root
    property string glyph: "□"
    property string subtitle: ""
    property bool active: false
    property bool vertical: false
    implicitWidth: 236
    implicitHeight: root.vertical ? 148 : 103
    hoverEnabled: true

    background: Rectangle {
        id: tileBackground
        radius: 9
        color: root.down ? "#13263c" : (root.hovered ? "#0e2237" : "#071522")
        border.width: root.active ? 2 : 1
        border.color: root.active ? "#c85fff" : (root.hovered ? "#5bd4ff" : "#497899")

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, parent.radius - 1)
            color: "transparent"
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: root.active ? "#692379" : "#1a2440" }
                GradientStop { position: 0.48; color: "#06121f" }
                GradientStop { position: 1.00; color: root.active ? "#123653" : "#0a2a3e" }
            }
            opacity: root.active ? 0.42 : 0.28
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: Math.max(0, parent.radius - 2)
            color: "transparent"
            border.width: 1
            border.color: root.active ? "#8154ad" : "#356988"
            opacity: root.active ? 0.58 : 0.40
        }

        Rectangle {
            visible: root.active
            width: 6
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            radius: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#d275ff" }
                GradientStop { position: 0.48; color: Theme.purple }
                GradientStop { position: 1.0; color: Theme.cyan }
            }
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
                GradientStop { position: 0.00; color: root.active ? "#c27cff" : "#688dcc" }
                GradientStop { position: 1.00; color: root.active ? "#64dcff" : "#3aa7cc" }
            }
            opacity: root.active ? 0.90 : 0.60
        }
    }

    contentItem: Item {
        Row {
            visible: !root.vertical
            anchors.fill: parent
            anchors.leftMargin: 17
            anchors.rightMargin: 12
            spacing: 14
            Text {
                width: 48
                text: root.glyph
                color: root.active ? "#e29aff" : "#85bcff"
                font.family: "Segoe UI Symbol"
                font.pixelSize: 40
                horizontalAlignment: Text.AlignHCenter
                anchors.verticalCenter: parent.verticalCenter
            }
            Column {
                width: root.width - 90
                spacing: 5
                anchors.verticalCenter: parent.verticalCenter
                Text {
                    width: parent.width
                    text: root.text
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 18
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: root.subtitle
                    color: Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }
        }

        Column {
            visible: root.vertical
            anchors.centerIn: parent
            width: Math.max(80, parent.width - 24)
            spacing: 5
            Text {
                width: parent.width
                text: root.glyph
                color: root.active ? "#e29aff" : "#85bcff"
                font.family: "Segoe UI Symbol"
                font.pixelSize: 35
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                width: parent.width
                text: root.text
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 16
                font.weight: Font.Medium
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: root.subtitle
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                maximumLineCount: 3
                elide: Text.ElideRight
            }
        }
    }
}

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
        color: root.down ? "#15243a" : (root.hovered ? "#11243a" : "#0b1828")
        border.width: root.active ? 2 : 1
        border.color: root.active ? "#c05dff" : (root.hovered ? "#50c8ff" : "#3e6482")

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: Math.max(0, parent.radius - 1)
            color: "transparent"
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: root.active ? "#59206b" : "#18243b" }
                GradientStop { position: 0.50; color: "#071321" }
                GradientStop { position: 1.00; color: root.active ? "#102a4a" : "#0b2435" }
            }
            opacity: root.active ? 0.31 : 0.17
        }

        Rectangle {
            visible: root.active
            width: 6
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            radius: 3
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#c861ff" }
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
                GradientStop { position: 0.00; color: root.active ? "#b86dff" : "#537cab" }
                GradientStop { position: 1.00; color: root.active ? "#4ecbff" : "#2e7194" }
            }
            opacity: root.active ? 0.68 : 0.32
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
                color: root.active ? "#d885ff" : "#74a5ff"
                font.family: "Segoe UI Symbol"
                font.pixelSize: 39
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
                color: root.active ? "#d885ff" : "#74a5ff"
                font.family: "Segoe UI Symbol"
                font.pixelSize: 34
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

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Text {
            text: "PARTITION MANAGER"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 22
            font.weight: Font.Medium
        }

        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                radius: 7
                color: "#081322"
                border.width: 1
                border.color: "#3c5676"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    Text { text: "⌕"; color: "#9cb7d7"; font.pixelSize: 23 }
                    Text { Layout.fillWidth: true; text: "Search Huawei / Honor model..."; color: "#8798ad"; font.family: Theme.fontFamily; font.pixelSize: 13 }
                    Text { text: "⌄"; color: Theme.text; font.pixelSize: 18 }
                }
            }
            Rectangle {
                Layout.preferredWidth: 250
                Layout.preferredHeight: 35
                radius: 6
                color: "#0b1727"
                border.width: 1
                border.color: "#3b5270"
                Row {
                    anchors.fill: parent
                    Rectangle {
                        width: parent.width / 2; height: parent.height; radius: 6
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: "#5a33ad" }
                            GradientStop { position: 1; color: "#10598f" }
                        }
                        Text { anchors.centerIn: parent; text: "MODEL"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    Rectangle {
                        width: parent.width / 2; height: parent.height; color: "transparent"
                        Text { anchors.centerIn: parent; text: "CHIPSET"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        Text { text: "Switch to Chipset to browse Kirin platform families"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            GlowButton { text: "↻  REFRESH"; Layout.preferredWidth: 148; Layout.preferredHeight: 42; onClicked: backend.runAction("read_device") }
            GlowButton { text: "▤  READ"; Layout.preferredWidth: 142; Layout.preferredHeight: 42; onClicked: backend.runAction("read_device") }
            Button {
                text: "✎  WRITE"; enabled: false; Layout.preferredWidth: 145; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                text: "♲  ERASE"; enabled: false; Layout.preferredWidth: 145; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Item { Layout.fillWidth: true }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 0
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38; color: "#0a1726"; border.width: 1; border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                        Text { text: "□"; color: Theme.muted; font.pixelSize: 16; Layout.preferredWidth: 28 }
                        Text { text: "PARTITION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 190 }
                        Text { text: "LUN"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 70 }
                        Text { text: "START"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: "SIZE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 100 }
                        Text { text: "STATUS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 90 }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.centerIn: parent
                        spacing: 10
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.connected ? "Partition inventory requires the certified Xray partition provider." : "Connect and read a device to begin partition discovery."; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Write and erase remain disabled until physical certification grants that exact authority."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 9
                Text { text: "SELECTED PARTITION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 18
                    ColumnLayout { Layout.fillWidth: true
                        Text { text: "Partition      —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "LUN            —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Start          —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    ColumnLayout { Layout.fillWidth: true
                        Text { text: "Size           —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "File System    —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Type           —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }
    }
}

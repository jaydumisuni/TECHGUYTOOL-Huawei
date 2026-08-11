import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        Text {
            text: "PARTITION MANAGER"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 21
            font.weight: Font.Medium
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                radius: 7
                color: "#081322"
                border.width: 1
                border.color: "#3c5676"
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    Text { text: "⌕"; color: "#9cb7d7"; font.pixelSize: 22 }
                    Text { Layout.fillWidth: true; text: "Search Huawei / Honor model..."; color: "#8798ad"; font.family: Theme.fontFamily; font.pixelSize: 13 }
                    Text { text: "⌄"; color: Theme.text; font.pixelSize: 17 }
                }
            }
            Rectangle {
                Layout.preferredWidth: 266
                Layout.preferredHeight: 36
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

        Text { text: "Switch to Chipset to browse Kirin platform families"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            GlowButton { text: "↻  REFRESH"; Layout.preferredWidth: 150; Layout.preferredHeight: 42; onClicked: backend.runAction("read_device") }
            GlowButton { text: "▤  READ"; Layout.preferredWidth: 150; Layout.preferredHeight: 42; onClicked: backend.runAction("read_device") }
            Button {
                text: "✎  WRITE"; enabled: false; Layout.preferredWidth: 150; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                text: "♲  ERASE"; enabled: false; Layout.preferredWidth: 150; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Item { Layout.fillWidth: true }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 292
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 0
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    color: "#0a1726"
                    border.width: 1
                    border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                        Text { text: "□"; color: Theme.muted; font.pixelSize: 15; Layout.preferredWidth: 28 }
                        Text { text: "PARTITION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 185 }
                        Text { text: "LUN"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 65 }
                        Text { text: "START"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.fillWidth: true }
                        Text { text: "SIZE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 105 }
                        Text { text: "STATUS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 85 }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.centerIn: parent
                        spacing: 8
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: backend.connected ? "No certified partition inventory has been returned yet." : "Connect and read a device to begin partition discovery."
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "Partition rows appear only from verified read evidence."
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 165
            panelOpacity: 0.62
            RowLayout {
                anchors.fill: parent
                anchors.margins: 13
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 9
                    Text { text: "SELECTED PARTITION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Partition        —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                            Text { text: "LUN              —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                            Text { text: "Start            —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Size             —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                            Text { text: "File System      —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                            Text { text: "Type             —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.fillHeight: true
                    color: "#2e4661"
                }

                RowLayout {
                    Layout.preferredWidth: 245
                    Layout.fillHeight: true
                    spacing: 12
                    Item {
                        Layout.preferredWidth: 92
                        Layout.preferredHeight: 92
                        Rectangle {
                            anchors.centerIn: parent
                            width: 84; height: 84; radius: 42
                            color: "transparent"
                            border.width: 10
                            border.color: "#52667c"
                            Rectangle {
                                anchors.centerIn: parent
                                width: 58; height: 58; radius: 29
                                color: "#0b1727"
                                Text { anchors.centerIn: parent; text: "—\nUsed"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "■  Used      —"; color: "#b06cff"; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "■  Free       —"; color: "#4ba9ff"; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "■  Total      —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Button {
                Layout.fillWidth: true; Layout.preferredHeight: 46; enabled: false; text: "⇧  BACKUP PARTITION"
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.fillWidth: true; Layout.preferredHeight: 46; enabled: false; text: "⇩  RESTORE PARTITION"
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
    }
}

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Item {
    id: root
    property string selectedAction: "frp_repair"
    property string selectedLabel: "FRP REPAIR"
    signal terminalRequested()

    function selectOperation(actionId, label) {
        selectedAction = actionId
        selectedLabel = label
        backend.setSelectedOperation(actionId, label)
    }

    Component.onCompleted: backend.setSelectedOperation(selectedAction, selectedLabel)

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 248
            RowLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 22
                Text {
                    text: "▯"
                    color: "#d8dee7"
                    font.family: "Segoe UI Symbol"
                    font.pixelSize: 74
                    Layout.preferredWidth: 92
                    horizontalAlignment: Text.AlignHCenter
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: backend.connected ? backend.deviceModel : "NO DEVICE CONNECTED"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 22
                            font.weight: Font.Medium
                            Layout.fillWidth: true
                        }
                        Rectangle {
                            width: 54; height: 24; radius: 5
                            color: "#0d2236"; border.width: 1; border.color: "#2c6996"
                            Text { anchors.centerIn: parent; text: "AUTO"; color: Theme.cyan; font.family: Theme.fontFamily; font.pixelSize: 11; font.letterSpacing: 0.8 }
                        }
                    }
                    Text {
                        text: backend.connected ? "Connected through " + backend.deviceInterface + ". Read evidence is available." : "Connect a Huawei device in normal mode or fastboot mode\nusing a USB cable."
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        lineHeight: 1.35
                        Layout.fillWidth: true
                    }
                    Item { Layout.preferredHeight: 4 }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "SELECT DEVICE BY"; color: "#d7dce4"; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 0.6 }
                        Rectangle {
                            Layout.preferredWidth: 290; Layout.preferredHeight: 34; radius: 7
                            color: "#0b1727"; border.width: 1; border.color: "#3a4e70"
                            Row {
                                anchors.fill: parent
                                Rectangle {
                                    width: parent.width / 2; height: parent.height; radius: 6
                                    gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#5030a0" } GradientStop { position: 1; color: "#12528e" } }
                                    Text { anchors.centerIn: parent; text: "MODEL"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 1 }
                                }
                                Rectangle {
                                    width: parent.width / 2; height: parent.height; color: "transparent"
                                    Text { anchors.centerIn: parent; text: "CHIPSET"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 0.8 }
                                }
                            }
                        }
                        Item { Layout.fillWidth: true }
                        GlowButton {
                            text: "Read Device"
                            Layout.preferredWidth: 134
                            Layout.preferredHeight: 45
                            onClicked: backend.runAction("read_device")
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 47
                        radius: 7
                        color: "#081322"
                        border.width: 1
                        border.color: "#405876"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            Text { text: "⌕"; color: "#9cb7d7"; font.family: "Segoe UI Symbol"; font.pixelSize: 25 }
                            Text { text: "Search Huawei / Honor model..."; color: "#8092a8"; font.family: Theme.fontFamily; font.pixelSize: 14; Layout.fillWidth: true }
                            Text { text: "⌄"; color: Theme.text; font.family: "Segoe UI Symbol"; font.pixelSize: 20 }
                        }
                    }
                    Text { text: "Switch to Chipset to browse Kirin platform families"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                }
            }
        }

        GridLayout {
            id: operationGrid
            Layout.fillWidth: true
            Layout.preferredHeight: 322
            columns: 3
            columnSpacing: 10
            rowSpacing: 10

            OperationTile { Layout.fillWidth: true; text: "FRP Repair"; subtitle: "Remove FRP lock from devices."; glyph: "♙"; active: root.selectedAction === "frp_repair"; onClicked: root.selectOperation("frp_repair", "FRP REPAIR") }
            OperationTile { Layout.fillWidth: true; text: "Bootloader"; subtitle: "Unlock or relock the bootloader."; glyph: "♙"; active: root.selectedAction === "bootloader"; onClicked: root.selectOperation("bootloader", "BOOTLOADER") }
            OperationTile { Layout.fillWidth: true; text: "Huawei ID"; subtitle: "Remove or manage Huawei ID."; glyph: "♙"; active: root.selectedAction === "huawei_id"; onClicked: root.selectOperation("huawei_id", "HUAWEI ID") }
            OperationTile { Layout.fillWidth: true; text: "Verlist"; subtitle: "Read and repair device verification status."; glyph: "◇"; active: root.selectedAction === "verlist"; onClicked: root.selectOperation("verlist", "VERLIST") }
            OperationTile { Layout.fillWidth: true; text: "Pair"; subtitle: "Repair and manage Bluetooth/Wi-Fi pairing."; glyph: "↗"; active: root.selectedAction === "pair"; onClicked: root.selectOperation("pair", "PAIR") }
            OperationTile { Layout.fillWidth: true; text: "Full OEMINFO"; subtitle: "Read full OEM information from device."; glyph: "▤"; active: root.selectedAction === "full_oeminfo"; onClicked: root.selectOperation("full_oeminfo", "FULL OEMINFO") }
            OperationTile { Layout.fillWidth: true; text: "Flash Firmware"; subtitle: "Flash stock or custom firmware."; glyph: "▣"; active: root.selectedAction === "flash_firmware"; onClicked: root.selectOperation("flash_firmware", "FLASH FIRMWARE") }
            OperationTile { Layout.fillWidth: true; text: "Board Repair"; subtitle: "Repair board functions and calibrations."; glyph: "⚒"; active: root.selectedAction === "board_repair"; onClicked: root.selectOperation("board_repair", "BOARD REPAIR") }
            OperationTile { Layout.fillWidth: true; text: "Backup / Restore"; subtitle: "Backup or restore device partitions."; glyph: "☁"; active: root.selectedAction === "backup_restore"; onClicked: root.selectOperation("backup_restore", "BACKUP / RESTORE") }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 154
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "SELECTED OPERATION: "; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 1 }
                    Text { text: root.selectedLabel; color: Theme.purple; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 1 }
                    Item { Layout.fillWidth: true }
                    Text { text: "♢"; color: Theme.green; font.family: "Segoe UI Symbol"; font.pixelSize: 24 }
                    Text { text: "Backup before write enabled"; color: Theme.green; font.family: Theme.fontFamily; font.pixelSize: 13 }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "DEVICE / PLATFORM"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; font.letterSpacing: 0.8 }
                        ComboBox { Layout.fillWidth: true; model: ["Auto Detect", "Huawei / Honor", "Kirin Platform"]; currentIndex: 0 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "SERVICE MODE"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; font.letterSpacing: 0.8 }
                        ComboBox { Layout.fillWidth: true; model: ["Auto (Recommended)", "ADB", "Fastboot", "Upgrade Mode", "Rescue"]; currentIndex: 0 }
                    }
                }
                GlowButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 53
                    text: backend.connected ? "START " + root.selectedLabel : "CONNECT DEVICE TO CONTINUE"
                    enabled: backend.connected
                    onClicked: backend.runAction(root.selectedAction)
                }
            }
        }
    }
}
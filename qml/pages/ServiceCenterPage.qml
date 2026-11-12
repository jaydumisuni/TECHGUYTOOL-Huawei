import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Item {
    id: root
    // Tiles are one-click actions, not a selection followed by a START step.
    // The backend retains custody of authorization, device state, errors and audit.
    property string invokedAction: ""
    property string backendReply: ""
    property bool statusTracking: false
    readonly property string liveStatus: {
        var backendStatus = typeof backend.operationStatus === "string" ?
                            backend.operationStatus.trim() : ""
        if (backendStatus.length) return backendStatus
        if (statusTracking) {
            // Backends without a dedicated status property still publish
            // truthful state transitions through their existing log signal.
            var lines = String(backend.logText || "").trim().split("\n")
            var latest = lines.length ? lines[lines.length - 1] : ""
            latest = latest.replace(/^\[[^\]]+\]\s*/, "").replace(/^\[[^\]]+\]\s*/, "")
            if (latest.length) return latest
            if (backendReply.length) return backendReply
        }
        return backend.connected ? "DEVICE CONNECTED — READY" : "WAITING FOR DEVICE"
    }
    signal terminalRequested()

    function invokeOperation(actionId, label) {
        // No frontend connectivity gate: ask the backend once and let it
        // decide whether the real operation is ready or must be guarded.
        invokedAction = actionId
        statusTracking = true
        if (typeof backend.setSelectedOperation === "function")
            backend.setSelectedOperation(actionId, label)
        var result = backend.runAction(actionId)
        backendReply = result === undefined || result === null ? "" : String(result)
    }

    function readDevice() {
        statusTracking = true
        var result = backend.runAction("read_device")
        backendReply = result === undefined || result === null ? "" : String(result)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 264
            RowLayout {
                anchors.fill: parent
                anchors.margins: 22
                spacing: 22
                Image {
                    source: Qt.resolvedUrl("../../assets/ui-icons/phone.svg")
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Layout.preferredWidth: 92
                    Layout.preferredHeight: 84
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            objectName: "deviceOperationStatus"
                            text: root.liveStatus
                            elide: Text.ElideRight
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
                        text: backend.connected ?
                              backend.deviceModel + " • " + backend.deviceInterface :
                              "Connect a Huawei device in normal mode or fastboot mode\nusing a USB cable."
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
                            objectName: "readDeviceButton"
                            text: "Read Device"
                            Layout.preferredWidth: 134
                            Layout.preferredHeight: 45
                            onClicked: root.readDevice()
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
                            Image { source: Qt.resolvedUrl("../../assets/ui-icons/search.svg"); Layout.preferredWidth: 24; Layout.preferredHeight: 24; fillMode: Image.PreserveAspectFit }
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
            Layout.fillHeight: true
            Layout.minimumHeight: 322
            columns: 3
            columnSpacing: 10
            rowSpacing: 10

            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFrpRepair"; enabled: backend.operationBusy !== true; text: "FRP Repair"; subtitle: "Remove FRP lock from devices."; glyph: "♙"; iconName: "frp-repair"; active: root.invokedAction === "frp_repair"; onClicked: root.invokeOperation("frp_repair", "FRP REPAIR") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBootloader"; enabled: backend.operationBusy !== true; text: "Bootloader"; subtitle: "Unlock or relock the bootloader."; glyph: "♙"; iconName: "bootloader"; active: root.invokedAction === "bootloader"; onClicked: root.invokeOperation("bootloader", "BOOTLOADER") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationHuaweiId"; enabled: backend.operationBusy !== true; text: "Huawei ID"; subtitle: "Remove or manage Huawei ID."; glyph: "♙"; iconName: "huawei-id"; active: root.invokedAction === "huawei_id"; onClicked: root.invokeOperation("huawei_id", "HUAWEI ID") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationVerlist"; enabled: backend.operationBusy !== true; text: "Verlist"; subtitle: "Read and repair device verification status."; glyph: "◇"; iconName: "verlist"; active: root.invokedAction === "verlist"; onClicked: root.invokeOperation("verlist", "VERLIST") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationPair"; enabled: backend.operationBusy !== true; text: "Pair"; subtitle: "Repair and manage Bluetooth/Wi-Fi pairing."; glyph: "↗"; iconName: "pair"; active: root.invokedAction === "pair"; onClicked: root.invokeOperation("pair", "PAIR") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFullOeminfo"; enabled: backend.operationBusy !== true; text: "Full OEMINFO"; subtitle: "Read full OEM information from device."; glyph: "▤"; iconName: "full-oeminfo"; active: root.invokedAction === "full_oeminfo"; onClicked: root.invokeOperation("full_oeminfo", "FULL OEMINFO") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFlashFirmware"; enabled: backend.operationBusy !== true; text: "Flash Firmware"; subtitle: "Flash stock or custom firmware."; glyph: "▣"; iconName: "flash-firmware"; active: root.invokedAction === "flash_firmware"; onClicked: root.invokeOperation("flash_firmware", "FLASH FIRMWARE") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBoardRepair"; enabled: backend.operationBusy !== true; text: "Board Repair"; subtitle: "Repair board functions and calibrations."; glyph: "⚒"; iconName: "board-repair"; active: root.invokedAction === "board_repair"; onClicked: root.invokeOperation("board_repair", "BOARD REPAIR") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBackupRestore"; enabled: backend.operationBusy !== true; text: "Backup / Restore"; subtitle: "Backup or restore device partitions."; glyph: "☁"; iconName: "backup"; active: root.invokedAction === "backup_restore"; onClicked: root.invokeOperation("backup_restore", "BACKUP / RESTORE") }
        }

    }
}
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
    signal boardRepairRequested()
    signal firmwareRequested()
    signal backupRequested()

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
                        GlowButton {
                            objectName: "readDeviceButton"
                            text: "Read Device"
                            Layout.preferredWidth: 126
                            Layout.preferredHeight: 42
                            enabled: !backend.operationBusy
                            onClicked: root.readDevice()
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
                    DeviceSearchHeader {
                        objectName: "serviceCenterDeviceTargetSelector"
                        Layout.fillWidth: true
                        interactiveTarget: true
                        pageTitle: ""
                        placeholder: "Search Huawei / Honor model..."
                    }
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

            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFrpRepair"; enabled: backend.operationBusy !== true; text: "FRP Repair"; subtitle: "Official account recovery assistance."; glyph: "♙"; iconName: "frp-repair"; active: root.invokedAction === "frp_repair"; onClicked: root.invokeOperation("frp_repair", "FRP REPAIR") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBootloader"; enabled: backend.operationBusy !== true; text: "Bootloader"; subtitle: "Inspect bootloader state and official service options."; glyph: "♙"; iconName: "bootloader"; active: root.invokedAction === "bootloader"; onClicked: root.invokeOperation("bootloader", "BOOTLOADER") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationHuaweiId"; enabled: backend.operationBusy !== true; text: "Huawei ID"; subtitle: "Open authorized Android account settings."; glyph: "♙"; iconName: "huawei-id"; active: root.invokedAction === "huawei_id"; onClicked: root.invokeOperation("huawei_id", "HUAWEI ID") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationVerlist"; enabled: backend.operationBusy !== true; text: "Verlist"; subtitle: "Read and repair device verification status."; glyph: "◇"; iconName: "verlist"; active: root.invokedAction === "verlist"; onClicked: root.invokeOperation("verlist", "VERLIST") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationPair"; enabled: backend.operationBusy !== true; text: "Pair"; subtitle: "Open Bluetooth pairing settings on the device."; glyph: "↗"; iconName: "pair"; active: root.invokedAction === "pair"; onClicked: root.invokeOperation("pair", "PAIR") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFullOeminfo"; enabled: backend.operationBusy !== true; text: "Full OEMINFO"; subtitle: "Read full OEM information from device."; glyph: "▤"; iconName: "full-oeminfo"; active: root.invokedAction === "full_oeminfo"; onClicked: root.invokeOperation("full_oeminfo", "FULL OEMINFO") }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationFlashFirmware"; enabled: backend.operationBusy !== true; text: "Flash Firmware"; subtitle: "Flash stock or custom firmware."; glyph: "▣"; iconName: "flash-firmware"; active: root.invokedAction === "flash_firmware"; onClicked: root.firmwareRequested() }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBoardRepair"; enabled: backend.operationBusy !== true; text: "Board Repair"; subtitle: "Repair board functions and calibrations."; glyph: "⚒"; iconName: "board-repair"; active: root.invokedAction === "board_repair"; onClicked: root.boardRepairRequested() }
            OperationTile { Layout.fillWidth: true; Layout.fillHeight: true; objectName: "operationBackupRestore"; enabled: backend.operationBusy !== true; text: "Backup / Restore"; subtitle: "Backup or restore device partitions."; glyph: "☁"; iconName: "backup"; active: root.invokedAction === "backup_restore"; onClicked: root.backupRequested() }
        }

    }
}
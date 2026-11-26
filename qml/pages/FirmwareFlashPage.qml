import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property bool advancedWorkflows: false
    property var flashPayload: ({})
    property var flashPartitions: []
    function refreshFlashResult() {
        try {
            var result = JSON.parse(backend.serviceResultJson("flash_firmware"))
            flashPayload = result.payload || ({})
            var ops = flashPayload.partitions || []
            flashPartitions = ops.slice(0, 6).map(function(item) { return item.partition })
        } catch (ignored) {
            flashPayload = ({})
            flashPartitions = []
        }
    }
    Connections {
        target: backend
        function onServiceResultChanged() { root.refreshFlashResult() }
        function onFirmwareChanged() { root.flashPayload = ({}); root.flashPartitions = [] }
        function onFirmwareTargetChanged() { root.flashPayload = ({}); root.flashPartitions = [] }
        function onFirmwareModeChanged() { root.flashPayload = ({}); root.flashPartitions = [] }
    }
    Component.onCompleted: refreshFlashResult()
    Dialog {
        id: flashConfirm
        title: "Confirm direct firmware write"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 430
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: backend.confirmFirmwareFlash()
        contentItem: Text {
            wrapMode: Text.WordWrap
            color: Theme.text
            font.family: Theme.fontFamily
            text: "Write " + (root.flashPayload.partitions || []).length
                 + " verified partitions to " + (root.flashPayload.model || "the connected device")
                 + " (" + (root.flashPayload.chipset || "unverified chipset")
                 + (root.flashPayload.vendor_reconstruction ? ")? Restore the vendor GPT layout and selected firmware. Existing data may become inaccessible. Device-unique regions are preserved; backup and readback before completion. No automatic reset." : root.flashPayload.same_layout ? ")? Program selected firmware on the existing layout. GPT, device-unique data and userdata excluded; backup and readback before completion. No automatic reset." : root.flashPayload.board_recovery ? ")? Factory board restoration replaces firmware and userdata. Backs up selected regions, verifies GPT and boot/recovery, then resets. Excludes six device-unique partitions." : root.flashPayload.userdata_replaced ? ")? This replaces USERDATA and CACHE. Factory boot chain retained. Stops on error; no automatic reboot." : ")? Stops on error. No OEMINFO write, unlock, erase or automatic reboot.")
        }
    }
    FileDialog {
        id: packageDialog
        title: "Select Huawei firmware package"
        nameFilters: ["Huawei firmware / board XML (*.json *.APP *.app *.xml)", "Archive (preflight only) (*.zip)", "All files (*)"]
        onAccepted: backend.setFirmwarePath(selectedFile.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        anchors.bottomMargin: 32
        spacing: 8
        DeviceSearchHeader {
            pageTitle: "FIRMWARE FLASH"
            placeholder: "Search Model..."
            interactiveTarget: true
            hint: "Switch to Chipset to browse platform families"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            Button {
                objectName: "flashOverviewTab"
                text: "OVERVIEW"
                Layout.preferredWidth: 130
                Layout.preferredHeight: 32
                onClicked: root.advancedWorkflows=false
            }
            Button {
                objectName: "flashAdvancedTab"
                text: "APP / XML WORKFLOWS"
                Layout.preferredWidth: 210
                Layout.preferredHeight: 32
                onClicked: root.advancedWorkflows=true
            }
            Item { Layout.fillWidth: true }
            Text {
                text: root.advancedWorkflows ? "PACKAGE CONFIGURATION" : "HUAWEI FLASH SERVICE"
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: 11
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
            visible: !root.advancedWorkflows
            SectionLabel { number: 1; text: "PACKAGE SOURCE" }
            RowLayout {
                Layout.fillWidth: true
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 43
                    radius: 6
                    color: "#0a1525"
                    border.width: 1
                    border.color: "#2d425f"
                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        text: backend.firmwarePath.length ? backend.firmwarePath : "No file selected"
                        color: backend.firmwarePath.length ? Theme.text : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                        elide: Text.ElideMiddle
                        width: parent.width - 30
                    }
                }
                GlowButton {
                    text: "BROWSE"
                    Layout.preferredWidth: 126
                    Layout.preferredHeight: 43
                    onClicked: packageDialog.open()
                }
            }
            SectionLabel { number: 2; text: "PACKAGE SUMMARY" }
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 61
                Layout.minimumHeight: 61
                Layout.maximumHeight: 61
                spacing: 0
                Repeater {
                    model: ["MODEL", "CHIPSET", "PARTITIONS", "PLAN STATUS"]
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#0a1525"
                        border.width: 1
                        border.color: "#314a66"
                        Column {
                            anchors.centerIn: parent
                            spacing: 7
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData
                                color: Theme.muted
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: index === 0 ? (root.flashPayload.model || backend.firmwareModel || "-")
                                     : index === 1 ? (root.flashPayload.chipset || backend.firmwareChipset || "-")
                                     : index === 2 ? String((root.flashPayload.partitions || []).length)
                                     : (backend.firmwarePlanReady ? "VERIFIED" : "NOT READY")
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: 15
                            }
                        }
                    }
                }
            }
            SectionLabel { number: 3; text: "SERVICE MODE" }
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 150
                Layout.minimumHeight: 150
                Layout.maximumHeight: 150
                spacing: 10
                Repeater {
                    model: [
                        {title: "Upgrade", icon: "upgrade", glyph: "⇧", sub: "Update to newer compatible firmware"},
                        {title: "Downgrade", icon: "downgrade", glyph: "⇩", sub: "Install an approved earlier build"},
                        {title: "Full Flash", icon: "full-flash", glyph: "▤", sub: "Flash all selected partitions"},
                        {title: "Board Firmware", icon: "board-firmware", glyph: "▣", sub: "Load factory board software"},
                        {title: "Repair", icon: "repair", glyph: "⚒", sub: "Reinstall damaged system components"}
                    ]
                    OperationTile {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        vertical: true
                        text: modelData.title
                        glyph: modelData.glyph
                        iconName: modelData.icon
                        subtitle: modelData.sub
                        active: index === 0
                        onClicked: {
                            if (typeof backend.setFirmwareMode === "function")
                                backend.setFirmwareMode(modelData.title)
                            advancedPanel.workflowIndex = index === 0 || index === 1 ? 0 :
                                                          index === 3 ? 3 : 2
                            root.advancedWorkflows = !(modelData.title === "Repair" || modelData.title === "Board Firmware")
                        }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 178
                Layout.minimumHeight: 178
                Layout.maximumHeight: 178
                spacing: 14
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5
                        SectionLabel { number: 4; text: "PARTITIONS" }
                        Repeater {
                            model: root.flashPartitions
                            CheckBox {
                                text: modelData
                                checked: true
                                enabled: false // Only the verified package determines writes
                                font.family: Theme.fontFamily
                                font.pixelSize: 13
                            }
                        }
                    }
                }
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10
                        SectionLabel { number: 5; text: "SAFE OPTIONS" }
                        ToggleRow { title: "Verify package"; subtitle: "SHA-256 checked before each write."; checked: backend.firmwarePlanReady; enabled: false }
                        ToggleRow { title: "Preserve identity"; subtitle: "OEMINFO, NVME, secure storage excluded."; checked: true; enabled: false }
                        ToggleRow { title: "Reboot after flash"; subtitle: "Disabled: retain Fastboot for inspection."; checked: false; enabled: false }
                    }
                }
            }
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 66
                Layout.minimumHeight: 66
                Layout.maximumHeight: 66
                text: backend.firmwarePlanReady ? (root.flashPayload.board_recovery ? "CONFIRM BOARD RECOVERY" : "CONFIRM DIRECT FASTBOOT FLASH") : "VERIFY SELECTED FIRMWARE"
                enabled: !backend.operationBusy && backend.firmwarePath.length > 0
                onClicked: {
                    if (backend.firmwarePlanReady) flashConfirm.open()
                    else backend.runAction("flash_firmware")
                }
            }
        }
        FlashWorkflowPanel {
            id: advancedPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.advancedWorkflows
            onBackRequested: root.advancedWorkflows=false
        }

    }
}

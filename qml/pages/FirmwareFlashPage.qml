import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property bool advancedWorkflows: false
    FileDialog {
        id: packageDialog
        title: "Select Huawei firmware package"
        nameFilters: ["Huawei firmware (*.zip *.app *.xml *.bin *.img)", "All files (*)"]
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
                    model: ["MODEL", "BUILD", "VENDOR / COUNTRY", "ANDROID VERSION"]
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
                                text: "—"
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
                            root.advancedWorkflows = true
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
                            model: ["boot", "recovery", "system", "vendor", "cust", "preload"]
                            CheckBox {
                                text: modelData
                                checked: true
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
                        ToggleRow { title: "Verify package"; subtitle: "Verify package integrity before flashing."; checked: true }
                        ToggleRow { title: "Backup OEMINFO"; subtitle: "Backup OEM information before flashing."; checked: true }
                        ToggleRow { title: "Reboot after flash"; subtitle: "Automatically reboot device when done."; checked: true }
                    }
                }
            }
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 66
                Layout.minimumHeight: 66
                Layout.maximumHeight: 66
                text: "LOAD FIRMWARE PACKAGE"
                onClicked: backend.runAction("flash_firmware")
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

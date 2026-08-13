import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    FileDialog {
        id: packageDialog
        title: "Select Huawei firmware package"
        nameFilters: ["Huawei firmware (*.zip *.app *.xml *.bin *.img)", "All files (*)"]
        onAccepted: backend.setFirmwarePath(selectedFile.toString())
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "FIRMWARE FLASH"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 22
                font.weight: Font.Medium
                Layout.fillWidth: true
            }
            Text {
                text: "SELECT DEVICE BY"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 12
            }
            Rectangle {
                width: 200
                height: 34
                radius: 6
                color: "#0b1727"
                border.width: 1
                border.color: "#3b5270"
                Row {
                    anchors.fill: parent
                    Rectangle {
                        width: 100
                        height: 34
                        radius: 6
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: "#5a33ad" }
                            GradientStop { position: 1; color: "#10598f" }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "MODEL"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                        }
                    }
                    Rectangle {
                        width: 100
                        height: 34
                        color: "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: "CHIPSET"
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 45
            radius: 7
            color: "#081322"
            border.width: 1
            border.color: "#3c5676"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                Text { text: "⌕"; color: "#9cb7d7"; font.pixelSize: 24 }
                Text {
                    text: "Search Model..."
                    color: "#8798ad"
                    font.family: Theme.fontFamily
                    font.pixelSize: 14
                    Layout.fillWidth: true
                }
                Text { text: "⌄"; color: Theme.text; font.pixelSize: 18 }
            }
        }
        Text {
            text: "Switch to Chipset to browse platform families"
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#243c55" }
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
                    {title: "Upgrade", glyph: "⇧", sub: "Update to newer compatible firmware"},
                    {title: "Downgrade", glyph: "⇩", sub: "Install an approved earlier build"},
                    {title: "Full Flash", glyph: "▤", sub: "Flash all selected partitions"},
                    {title: "Board Firmware", glyph: "▣", sub: "Load factory board software"},
                    {title: "Repair", glyph: "⚒", sub: "Reinstall damaged system components"}
                ]
                OperationTile {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    vertical: true
                    text: modelData.title
                    glyph: modelData.glyph
                    subtitle: modelData.sub
                    active: index === 0
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
            Layout.preferredHeight: 52
            Layout.minimumHeight: 52
            Layout.maximumHeight: 52
            text: "LOAD FIRMWARE PACKAGE"
            onClicked: backend.runAction("flash_firmware")
        }
    }
}

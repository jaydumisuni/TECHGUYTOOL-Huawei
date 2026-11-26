import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property string reportText: backend.deviceReport
    Dialog {
        id: detailDialog
        title: "X-Ray Device Details"
        modal: true
        anchors.centerIn: Overlay.overlay
        width: Math.min(780, Overlay.overlay.width - 50)
        height: Math.min(620, Overlay.overlay.height - 50)
        standardButtons: Dialog.Close
        contentItem: ScrollView {
            TextArea {
                text: root.reportText
                readOnly: true
                wrapMode: TextEdit.Wrap
                font.family: "Consolas"
                font.pixelSize: 13
                color: Theme.text
                selectByMouse: true
            }
        }
    }
    FileDialog {
        id: saveReportDialog
        title: "Save device report"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Text report (*.txt)"]
        defaultSuffix: "txt"
        onAccepted: backend.saveDeviceReport(selectedFile.toString())
    }

    function iconForGlyph(glyph) {
        var mapping = {
            "▯": "phone", "◇": "security", "▦": "platform",
            "↕": "usb-interface", "▤": "firmware-flash",
            "▥": "device-information", "◴": "operation-history",
            "◉": "partition-manager", "◎": "board-repair",
            "▣": "monitor"
        }
        return Qt.resolvedUrl("../../assets/ui-icons/" +
                              (mapping[glyph] || "info") + ".svg")
    }

    function display(value) {
        return value && value.length ? value : "—"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8
        DeviceSearchHeader {
            pageTitle: "DEVICE INFORMATION"
            placeholder: "Search Huawei / Honor model..."
            hint: "Switch to Chipset to browse Kirin platform families"
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 122
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 11
                spacing: 7
                Text { text: "OVERVIEW"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0
                    Repeater {
                        model: [
                            {icon: "▯", label: "MODEL", value: root.display(backend.deviceModel)},
                            {icon: "◇", label: "PRODUCT NAME", value: root.display(backend.deviceProductName)},
                            {icon: "▦", label: "PLATFORM", value: root.display(backend.devicePlatform)},
                            {icon: "↕", label: "CONNECTION MODE", value: root.display(backend.deviceInterface)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 8
                                Image { source: root.iconForGlyph(modelData.icon); Layout.preferredWidth: 27; Layout.preferredHeight: 27; fillMode: Image.PreserveAspectFit }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                    Text { text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 11
                spacing: 7
                Text { text: "IDENTITY"; color: "#ac79ff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0
                    Repeater {
                        model: [
                            {icon: "▤", label: "SERIAL NUMBER", value: root.display(backend.deviceSerial)},
                            {icon: "▥", label: "IMEI 1", value: root.display(backend.deviceDetails["IMEI"])},
                            {icon: "▥", label: "IMEI 2", value: root.display(backend.deviceDetails["IMEI 2"])},
                            {icon: "▥", label: "MEID", value: root.display(backend.deviceDetails["MEID"])}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 9; spacing: 8
                                Image { source: root.iconForGlyph(modelData.icon); Layout.preferredWidth: 27; Layout.preferredHeight: 27; fillMode: Image.PreserveAspectFit }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                    Text { text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 11
                spacing: 7
                Text { text: "SOFTWARE"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 0
                    Repeater {
                        model: [
                            {icon: "▤", label: "BUILD NUMBER", value: root.display(backend.deviceBuild)},
                            {icon: "◴", label: "EMUI VERSION", value: root.display(backend.deviceEmuiVersion)},
                            {icon: "◉", label: "ANDROID VERSION", value: root.display(backend.deviceAndroidVersion)},
                            {icon: "◇", label: "SECURITY PATCH", value: root.display(backend.deviceSecurityPatch)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 9; spacing: 8
                                Image { source: root.iconForGlyph(modelData.icon); Layout.preferredWidth: 27; Layout.preferredHeight: 27; fillMode: Image.PreserveAspectFit }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                    Text { text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 160
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 11
                spacing: 7
                Text { text: "BOARD"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 65
                    spacing: 0
                    Repeater {
                        model: [
                            {label: "BOARD ID", value: root.display(backend.deviceBoardId)},
                            {label: "CHIPSET", value: root.display(backend.devicePlatform)},
                            {label: "BOOTLOADER STATE", value: root.display(backend.deviceBootloader)},
                            {label: "FRP STATE", value: root.display(backend.deviceFrpState)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 8; spacing: 3
                                Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                Text { text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#091524"
                    border.width: 1
                    border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 9
                        Image { source: root.iconForGlyph("◎"); Layout.preferredWidth: 27; Layout.preferredHeight: 27; fillMode: Image.PreserveAspectFit }
                        Text { text: "VENDOR / COUNTRY"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { Layout.fillWidth: true; text: root.display(backend.deviceVendorCountry); color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                text: "READ DEVICE"
                onClicked: backend.runAction("read_device")
            }
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                enabled: root.reportText.length > 0
                text: "FULL DETAILS"
                onClicked: detailDialog.open()
            }
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                enabled: root.reportText.length > 0
                text: "COPY REPORT"
                onClicked: backend.copyDeviceReport()
                background: Rectangle { radius: 7; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                enabled: root.reportText.length > 0
                text: "SAVE REPORT"
                onClicked: saveReportDialog.open()
                background: Rectangle { radius: 7; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
    }
}

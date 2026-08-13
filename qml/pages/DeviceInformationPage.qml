import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root

    function display(value) {
        return value && value.length ? value : "—"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        Text {
            text: "DEVICE INFORMATION"
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
                    Text {
                        Layout.fillWidth: true
                        text: "Search Huawei / Honor model..."
                        color: "#8798ad"
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                    }
                    Text { text: "⌄"; color: Theme.text; font.pixelSize: 17 }
                }
            }

            Text {
                text: "SELECT DEVICE BY"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 11
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
                        width: parent.width / 2
                        height: parent.height
                        radius: 6
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0; color: "#5a33ad" }
                            GradientStop { position: 1; color: "#10598f" }
                        }
                        Text { anchors.centerIn: parent; text: "MODEL"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    Rectangle {
                        width: parent.width / 2
                        height: parent.height
                        color: "transparent"
                        Text { anchors.centerIn: parent; text: "CHIPSET"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        Text {
            text: "Switch to Chipset to browse Kirin platform families"
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 11
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
                            {icon: "◇", label: "PRODUCT NAME", value: "—"},
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
                                Text { text: modelData.icon; color: "#9fc4ff"; font.pixelSize: 21; font.family: Theme.fontFamily }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
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
                            {icon: "▤", label: "SERIAL NUMBER", value: "—"},
                            {icon: "▥", label: "IMEI 1", value: "—"},
                            {icon: "▥", label: "IMEI 2", value: "—"},
                            {icon: "▥", label: "MEID", value: "—"}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 9; spacing: 8
                                Text { text: modelData.icon; color: "#9fc4ff"; font.pixelSize: 18; font.family: Theme.fontFamily }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
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
                            {icon: "▤", label: "BUILD NUMBER", value: "—"},
                            {icon: "◴", label: "EMUI VERSION", value: "—"},
                            {icon: "◉", label: "ANDROID VERSION", value: "—"},
                            {icon: "◇", label: "SECURITY PATCH", value: root.display(backend.deviceSecurity)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 9; spacing: 8
                                Text { text: modelData.icon; color: "#9fc4ff"; font.pixelSize: 18; font.family: Theme.fontFamily }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
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
                            {label: "BOARD ID", value: "—"},
                            {label: "CHIPSET", value: root.display(backend.devicePlatform)},
                            {label: "BOOTLOADER STATE", value: "—"},
                            {label: "FRP STATE", value: root.display(backend.deviceSecurity)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: "#091524"
                            border.width: 1
                            border.color: "#304862"
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 8; spacing: 3
                                Text { text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
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
                        Text { text: "◎"; color: "#9fc4ff"; font.pixelSize: 18; font.family: Theme.fontFamily }
                        Text { text: "VENDOR / COUNTRY"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { Layout.fillWidth: true; text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
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
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                enabled: false
                text: "COPY REPORT"
                background: Rectangle { radius: 7; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                enabled: false
                text: "SAVE REPORT"
                background: Rectangle { radius: 7; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
    }
}

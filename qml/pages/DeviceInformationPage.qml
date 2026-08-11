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
        anchors.margins: 18
        spacing: 12

        Text {
            text: "DEVICE INFORMATION"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 22
            font.weight: Font.Medium
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
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
                    Text {
                        Layout.fillWidth: true
                        text: "Search Huawei / Honor model..."
                        color: "#8798ad"
                        font.family: Theme.fontFamily
                        font.pixelSize: 13
                    }
                    Text { text: "⌄"; color: Theme.text; font.pixelSize: 18 }
                }
            }
            Text { text: "SELECT DEVICE BY"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
            Rectangle {
                Layout.preferredWidth: 240
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

        Text {
            text: "Switch to Chipset to browse Kirin platform families"
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 116
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "OVERVIEW"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                    Repeater {
                        model: [
                            {label: "MODEL", value: root.display(backend.deviceModel)},
                            {label: "PRODUCT NAME", value: root.display(backend.deviceModel)},
                            {label: "PLATFORM", value: root.display(backend.devicePlatform)},
                            {label: "CONNECTION MODE", value: root.display(backend.deviceInterface)}
                        ]
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 5
                            color: "#091524"; border.width: 1; border.color: "#304862"
                            Column { anchors.centerIn: parent; spacing: 6
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; elide: Text.ElideRight; width: Math.max(110, parent.parent.width - 18); horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 116
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "IDENTITY"; color: "#ac79ff"; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                    Repeater {
                        model: [
                            {label: "SERIAL NUMBER", value: backend.connected ? "Detected / evidence journal" : "—"},
                            {label: "IMEI 1", value: "—"},
                            {label: "IMEI 2", value: "—"},
                            {label: "MEID", value: "—"}
                        ]
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 5
                            color: "#091524"; border.width: 1; border.color: "#304862"
                            Column { anchors.centerIn: parent; spacing: 6
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 116
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "SOFTWARE / SECURITY"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                    Repeater {
                        model: [
                            {label: "BUILD NUMBER", value: "—"},
                            {label: "EMUI VERSION", value: "—"},
                            {label: "SECURITY", value: root.display(backend.deviceSecurity)},
                            {label: "SESSION", value: backend.connected ? "ACTIVE" : "—"}
                        ]
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; radius: 5
                            color: "#091524"; border.width: 1; border.color: "#304862"
                            Column { anchors.centerIn: parent; spacing: 6
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            }
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.62
            RowLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 14
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                    Text { text: "BOARD"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Text { text: "Chipset / board identity is populated only from verified Xray evidence."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                GlowButton {
                    Layout.preferredWidth: 180; Layout.preferredHeight: 44
                    text: "READ DEVICE"
                    onClicked: backend.runAction("read_device")
                }
            }
        }
    }
}

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Text {
            text: "BACKUP & RESTORE"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 22
            font.weight: Font.Medium
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "SELECT DEVICE BY"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
            Rectangle {
                Layout.preferredWidth: 260; Layout.preferredHeight: 35; radius: 6
                color: "#0b1727"; border.width: 1; border.color: "#3b5270"
                Row {
                    anchors.fill: parent
                    Rectangle {
                        width: parent.width / 2; height: parent.height; radius: 6
                        gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#5a33ad" }; GradientStop { position: 1; color: "#10598f" } }
                        Text { anchors.centerIn: parent; text: "MODEL"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    Rectangle { width: parent.width / 2; height: parent.height; color: "transparent"; Text { anchors.centerIn: parent; text: "CHIPSET"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 } }
                }
            }
            Item { Layout.fillWidth: true }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 44; radius: 7
            color: "#081322"; border.width: 1; border.color: "#3c5676"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
                Text { text: "⌕"; color: "#9cb7d7"; font.pixelSize: 23 }
                Text { Layout.fillWidth: true; text: "Search Huawei / Honor model..."; color: "#8798ad"; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Text { text: "⌄"; color: Theme.text; font.pixelSize: 18 }
            }
        }
        Text { text: "Switch to Chipset to browse Kirin platform families"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            GlassPanel {
                Layout.fillWidth: true; Layout.fillHeight: true; panelOpacity: 0.64
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 9
                    Text { text: "CREATE BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                    Text { text: "Select data to backup:"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    Repeater {
                        model: [
                            {title: "Full OEMINFO", sub: "Read full OEM information from device."},
                            {title: "Security Data", sub: "Backup security-related data."},
                            {title: "Calibration Data", sub: "Backup calibration and sensor data."},
                            {title: "NV Data", sub: "Backup NV items and configuration."},
                            {title: "User-selected Partitions", sub: "Choose specific approved partitions."}
                        ]
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 53; radius: 6
                            color: "#091524"; border.width: 1; border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                CheckBox { enabled: backend.connected }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Text { text: modelData.title; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                                    Text { text: modelData.sub; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Text { text: backend.connected ? "Backup operations remain lease-guarded until the certified adapter is present." : "Connect and read the target device first."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    GlowButton { Layout.fillWidth: true; Layout.preferredHeight: 46; text: "CREATE BACKUP"; onClicked: backend.runAction("backup_restore") }
                }
            }

            GlassPanel {
                Layout.fillWidth: true; Layout.fillHeight: true; panelOpacity: 0.64
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Text { text: "RESTORE BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                    Text { text: "Select a verified backup set to restore:"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 160; radius: 7
                        color: "#071320"; border.width: 1; border.color: "#285078"
                        border.style: Qt.DashLine
                        Column {
                            anchors.centerIn: parent; spacing: 9
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⇧"; color: "#84aaff"; font.pixelSize: 35 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No backup selected"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Restore requires a matching device identity and verified evidence."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true; columns: 2; rowSpacing: 8; columnSpacing: 12
                        Text { text: "Model"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        Text { text: "Platform"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        Text { text: "Integrity"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
                    }
                    Text { text: "⚠  Device match and evidence verification are required before restore."; color: "#c984ff"; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    GlowButton { Layout.fillWidth: true; Layout.preferredHeight: 46; text: "RESTORE BACKUP"; onClicked: backend.runAction("backup_restore") }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true; Layout.preferredHeight: 105; panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                Text { text: "RECENT BACKUPS"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                Text { Layout.fillWidth: true; text: "No verified backups are recorded in this UI session."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
            }
        }
    }
}

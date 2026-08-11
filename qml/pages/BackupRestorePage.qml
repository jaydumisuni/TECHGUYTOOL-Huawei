import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        Text {
            text: "BACKUP & RESTORE"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 21
            font.weight: Font.Medium
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Item { Layout.fillWidth: true }
            Text { text: "SELECT DEVICE BY"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
            Rectangle {
                Layout.preferredWidth: 290
                Layout.preferredHeight: 36
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
            Item { Layout.fillWidth: true }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            radius: 7
            color: "#081322"
            border.width: 1
            border.color: "#3c5676"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                Text { text: "⌕"; color: "#9cb7d7"; font.pixelSize: 22 }
                Text { Layout.fillWidth: true; text: "Search Huawei / Honor model..."; color: "#8798ad"; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Text { text: "⌄"; color: Theme.text; font.pixelSize: 17 }
            }
        }
        Text { text: "Switch to Chipset to browse Kirin platform families"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 430
            spacing: 12

            GlassPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                panelOpacity: 0.64
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 7
                    Text { text: "CREATE BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                    Text { text: "Select data to backup:"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                    Repeater {
                        model: [
                            {icon: "▤", title: "Full OEMINFO", sub: "Read full OEM information from device."},
                            {icon: "◇", title: "Security Data", sub: "Backup security related data."},
                            {icon: "◎", title: "Calibration Data", sub: "Backup calibration and sensor data."},
                            {icon: "▥", title: "NV Data", sub: "Backup NV items and configuration."},
                            {icon: "▦", title: "User-selected Partitions", sub: "Choose specific partitions to backup."}
                        ]
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 5
                            color: "#091524"; border.width: 1; border.color: "#304862"
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8; spacing: 8
                                CheckBox { enabled: backend.connected }
                                Text { text: modelData.icon; color: "#79a8ff"; font.family: Theme.fontFamily; font.pixelSize: 18 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 1
                                    Text { text: modelData.title; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
                                    Text { text: modelData.sub; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                    Text { text: "Destination:"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 34; radius: 5; color: "#081322"; border.width: 1; border.color: "#304862"
                            Text { anchors.left: parent.left; anchors.leftMargin: 9; anchors.verticalCenter: parent.verticalCenter; text: "%LOCALAPPDATA%\\THETECHGUY\\Huawei\\Backups"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; elide: Text.ElideMiddle; width: parent.width - 18 }
                        }
                        Button {
                            Layout.preferredWidth: 66; Layout.preferredHeight: 34; enabled: false; text: "Browse"
                            background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                            contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                    CheckBox { text: "Verify backup after reading"; enabled: backend.connected; font.family: Theme.fontFamily; font.pixelSize: 10 }
                    GlowButton { Layout.fillWidth: true; Layout.preferredHeight: 42; text: "CREATE BACKUP"; onClicked: backend.runAction("backup_restore") }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                panelOpacity: 0.64
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Text { text: "RESTORE BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
                    Text { text: "Select a backup file to restore:"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 112; radius: 6
                        color: "#071320"; border.width: 1; border.color: "#285078"
                        Column {
                            anchors.centerIn: parent; spacing: 5
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⇧"; color: "#84aaff"; font.pixelSize: 28 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Drag & drop backup file here"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10 }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "or"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9 }
                            Button {
                                anchors.horizontalCenter: parent.horizontalCenter; width: 150; height: 32; enabled: false; text: "SELECT BACKUP FILE"
                                background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            }
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true; columns: 2; rowSpacing: 6; columnSpacing: 10
                        Text { text: "Model"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "Platform"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "Created"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "Integrity"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10 }
                    }
                    Text { text: "⚠  Device match required before restore."; color: "#c984ff"; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    Button {
                        Layout.fillWidth: true; Layout.preferredHeight: 42; enabled: false; text: "RESTORE BACKUP"
                        background: Rectangle { radius: 6; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                        contentItem: Text { text: parent.text; color: "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 6
                Text { text: "RECENT BACKUPS"; color: "#63b7ff"; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 30; color: "#0a1726"; border.width: 1; border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 8; anchors.rightMargin: 8
                        Text { text: "FILE NAME"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.fillWidth: true }
                        Text { text: "MODEL"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.preferredWidth: 95 }
                        Text { text: "PLATFORM"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.preferredWidth: 90 }
                        Text { text: "CREATED"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.preferredWidth: 120 }
                        Text { text: "SIZE"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.preferredWidth: 70 }
                        Text { text: "INTEGRITY"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9; Layout.preferredWidth: 75 }
                    }
                }
                Text { Layout.fillWidth: true; text: "No verified backups are recorded in this UI session."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter }
            }
        }
    }
}

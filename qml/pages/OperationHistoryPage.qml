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
        spacing: 8
        DeviceSearchHeader {
            pageTitle: "OPERATION HISTORY"
            placeholder: "Search Huawei / Honor model..."
            hint: "Switch to Chipset to browse Kirin platform families"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 36; radius: 5
                color: "#081322"; border.width: 1; border.color: "#304862"
                Text { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: "⌕  Search operations..."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
            }
            ComboBox { Layout.preferredWidth: 118; Layout.preferredHeight: 36; model: ["All Operations"] }
            ComboBox { Layout.preferredWidth: 105; Layout.preferredHeight: 36; model: ["All Results"] }
            ComboBox { Layout.preferredWidth: 105; Layout.preferredHeight: 36; model: ["All Dates"] }
            Button {
                Layout.preferredWidth: 82; Layout.preferredHeight: 36; enabled: false; text: "EXPORT"
                background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.preferredWidth: 100; Layout.preferredHeight: 36; enabled: false; text: "CLEAR HISTORY"
                background: Rectangle { radius: 5; color: "#23122f"; border.width: 1; border.color: "#6f3887" }
                contentItem: Text { text: parent.text; color: "#a66dc5"; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 292
            panelOpacity: 0.64
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 0
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 34
                    color: "#0a1726"; border.width: 1; border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9
                        Text { text: "TIME"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 92 }
                        Text { text: "DEVICE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 165 }
                        Text { text: "OPERATION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: "RESULT"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 85 }
                        Text { text: "DURATION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 85 }
                        Text { text: "BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 100 }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Column {
                        anchors.centerIn: parent
                        spacing: 7
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "No persisted operation rows are loaded in this UI session."; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Live evidence remains available in the operation log and Huawei audit journal."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "SELECTED OPERATION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                    Item { Layout.fillWidth: true }
                    Button {
                        Layout.preferredWidth: 95; Layout.preferredHeight: 30; enabled: false; text: "OPEN LOG"
                        background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                        contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 14
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 2
                        rowSpacing: 6
                        columnSpacing: 10
                        Text { text: "Session ID"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Time"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Device"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: backend.connected ? backend.deviceModel : "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Operation"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Result"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    Rectangle {
                        Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#2e4661"
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 6
                        GridLayout {
                            Layout.fillWidth: true; columns: 2; rowSpacing: 5; columnSpacing: 8
                            Text { text: "Interface"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: backend.connected ? backend.deviceInterface : "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Platform"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: backend.connected ? backend.devicePlatform : "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Engine Response"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "—"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea {
                                text: backend.logText.length ? backend.logText : "No operation evidence recorded in this session."
                                readOnly: true
                                wrapMode: TextEdit.Wrap
                                color: "#9fb4c8"
                                selectionColor: "#245782"
                                font.family: "Consolas"
                                font.pixelSize: 11
                                background: Rectangle { color: "#06111e"; radius: 5; border.width: 1; border.color: "#243c55" }
                            }
                        }
                    }
                }
            }
        }
    }
}

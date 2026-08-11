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
            text: "OPERATION HISTORY"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 22
            font.weight: Font.Medium
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "SELECT DEVICE BY"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
            Rectangle {
                Layout.preferredWidth: 275; Layout.preferredHeight: 35; radius: 6
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
            Layout.fillWidth: true; spacing: 9
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 38; radius: 6; color: "#081322"; border.width: 1; border.color: "#304862"
                Text { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "⌕  Search operations..."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
            }
            ComboBox { Layout.preferredWidth: 125; Layout.preferredHeight: 38; model: ["All Operations"] }
            ComboBox { Layout.preferredWidth: 112; Layout.preferredHeight: 38; model: ["All Results"] }
            GlowButton { Layout.preferredWidth: 105; Layout.preferredHeight: 38; text: "REFRESH"; onClicked: backend.runAction("read_device") }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.64
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 8
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 36; color: "#0a1726"; border.width: 1; border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                        Text { text: "TIME"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 90 }
                        Text { text: "DEVICE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 145 }
                        Text { text: "OPERATION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.fillWidth: true }
                        Text { text: "RESULT"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 10; Layout.preferredWidth: 85 }
                    }
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

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 145
            panelOpacity: 0.62
            RowLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 18
                ColumnLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 6
                    Text { text: "SELECTED OPERATION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.DemiBold }
                    Text { text: "Session evidence is append-only and hash-verified by the Xray / Gateway evidence layer."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Text { text: backend.connected ? "Current device: " + backend.deviceModel + " via " + backend.deviceInterface : "Current device: —"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11 }
                }
                Rectangle {
                    Layout.preferredWidth: 240; Layout.fillHeight: true; radius: 7
                    color: "#06111e"; border.width: 1; border.color: "#243c55"
                    Text { anchors.centerIn: parent; width: parent.width - 24; text: "Detailed historical envelopes remain in the application evidence journal; this panel mirrors the live session without inventing records."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                }
            }
        }
    }
}

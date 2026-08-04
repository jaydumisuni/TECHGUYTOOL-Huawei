import QtQuick 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

GlassPanel {
    id: root
    property string title: "PAGE"
    property string message: "This module is connected to the common engine interface."
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 16
        Text { text: root.title; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 28; font.weight: Font.Medium; Layout.alignment: Qt.AlignHCenter }
        Text { text: root.message; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; Layout.preferredWidth: 520 }
        Text { text: backend.healthSummary; color: Theme.cyan; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }
    }
}

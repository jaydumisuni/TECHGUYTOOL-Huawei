import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Dialog {
    id: root
    width: 455
    height: 340
    modal: true
    focus: true
    anchors.centerIn: parent
    padding: 0
    closePolicy: Popup.CloseOnEscape
    background: GlassPanel { panelOpacity: 0.98; borderColor: "#536d88" }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.preferredWidth: 25 }
            Text { text: "ABOUT"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 17; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
            Button { flat: true; text: "×"; font.pixelSize: 23; onClicked: root.close() }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Image { source: "../../assets/brand/techguy_logo.svg"; fillMode: Image.PreserveAspectFit; Layout.preferredWidth: 120; Layout.preferredHeight: 120 }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "TECHGUY TOOL — HUAWEI"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Medium }
                Text { text: "Service & Recovery Edition"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Text { text: "v0.1.0"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 15 }
                Item { Layout.preferredHeight: 5 }
                Text { text: "Publisher"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                Text { text: "THETECHGUY DIGITAL SOLUTIONS"; color: Theme.purple; font.family: Theme.fontFamily; font.pixelSize: 13; letterSpacing: 0.6 }
                Text { text: "UI Version 1.0"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                Text { text: "Engine adapters managed separately"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
            }
        }
        GlowButton { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 215; text: "CLOSE"; onClicked: root.close() }
    }
}

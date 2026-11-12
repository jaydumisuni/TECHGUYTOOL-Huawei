import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Dialog {
    id: root
    objectName: "aboutDialog"
    width: 465
    height: 350
    modal: true
    focus: true
    x: parent ? Math.round((parent.width - width) / 2) + (-38) : 0
    y: parent ? Math.round((parent.height - height) / 2) + (-6) : 0
    padding: 0
    closePolicy: Popup.CloseOnEscape
    background: GlassPanel { panelOpacity: 0.98; borderColor: "#536d88" }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        anchors.topMargin: 10
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
            Image { source: "../../assets/brand/techguy_header.png"; fillMode: Image.PreserveAspectFit; Layout.preferredWidth: 120; Layout.preferredHeight: 120; Layout.alignment: Qt.AlignTop }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 8
                Text { text: "TECHGUY TOOL — HUAWEI"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 20; font.weight: Font.Medium }
                Text { text: "Service & Recovery Edition"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
                Text { text: "v0.1.0"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 15 }
                Item { Layout.preferredHeight: 5 }
                Text { text: "Publisher"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                Text { text: "THETECHGUY DIGITAL SOLUTIONS"; color: Theme.purple; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 0.6 }
                Text { text: "UI Version 1.0"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                Text { text: "Engine adapters managed separately"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
            }
        }
        GlowButton { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 215; text: "CLOSE"; onClicked: root.close() }
    }
}

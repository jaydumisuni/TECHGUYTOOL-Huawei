import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Popup {
    id: root
    objectName: "settingsMenu"
    property var ownerWindow
    signal fixDriversRequested()
    signal registerRequested()
    signal testpointRequested()
    signal aboutRequested()
    width: 380
    height: 312
    padding: 10
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    background: GlassPanel {
        panelOpacity: 0.97
        borderColor: "#557797"
    }
    contentItem: ColumnLayout {
        spacing: 7
        Text {
            text: "SETTINGS"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 16
            font.letterSpacing: 0.8
            Layout.leftMargin: 5
        }
        Repeater {
            model: [
                {label: "Fix Drivers", detail: "Repair Huawei USB and Fastboot drivers", glyph: "⚒", action: "drivers"},
                {label: "Register Device", detail: "Register this computer or service device", glyph: "▣", action: "register"},
                {label: "Testpoint / Pinout Library", detail: "Exact-model, owner-approved service references", glyph: "⌖", action: "testpoint"},
                {label: "About", detail: "Version, licence and product information", glyph: "ⓘ", action: "about"}
            ]
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 61
                hoverEnabled: true
                background: Rectangle {
                    radius: 7
                    color: parent.hovered ? "#142b42" : "#0c1b2c"
                    border.width: 1
                    border.color: parent.hovered ? Theme.cyan : "#3c5872"
                }
                contentItem: RowLayout {
                    spacing: 14
                    Text {
                        text: modelData.glyph
                        color: "#77a5ff"
                        font.family: "Segoe UI Symbol"
                        font.pixelSize: 28
                        Layout.preferredWidth: 40
                        horizontalAlignment: Text.AlignHCenter
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        Text {
                            text: modelData.label
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 16
                        }
                        Text {
                            text: modelData.detail
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                        }
                    }
                }
                onClicked: {
                    root.close()
                    if (modelData.action === "drivers") root.fixDriversRequested()
                    else if (modelData.action === "register") root.registerRequested()
                    else if (modelData.action === "testpoint") root.testpointRequested()
                    else root.aboutRequested()
                }
            }
        }
    }
}

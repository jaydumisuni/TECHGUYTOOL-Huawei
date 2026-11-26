import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Popup {
    id: root
    objectName: "auditLogsDialog"
    width: 760
    height: 570
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    modal: true
    focus: true
    padding: 15
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // The operation backend supplies audit data; the UI must never invent
    // persisted files or claim export succeeded without an adapter result.
    property int selectedTab: 0
    property string sessionLog: backend.logText
    property string auditLog: typeof backend.auditLogText === "string" ? backend.auditLogText : ""
    property string logsFolderPath: typeof backend.logsFolderPath === "string" ?
                                    backend.logsFolderPath : ""
    property string notice: ""
    signal openFolderRequested()

    function openAudit() {
        selectedTab = 0
        notice = ""
        open()
    }

    background: GlassPanel { panelOpacity: 0.98; borderColor: "#557da3" }

    contentItem: ColumnLayout {
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "LOGS / AUDIT"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 19
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            Button {
                text: "×"; flat: true; font.pixelSize: 24
                onClicked: root.close()
                contentItem: Text {
                    text: parent.text
                    color: Theme.text
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
        Text {
            text: "Each action has a dated TXT report. The current session output remains separate."
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: [{title:"SESSION LOG",value:0},{title:"AUDIT JOURNAL",value:1}]
                Button {
                    Layout.preferredWidth: 158
                    Layout.preferredHeight: 35
                    text: modelData.title
                    background: Rectangle {
                        radius: 6
                        color: root.selectedTab === modelData.value ? "#213f5c" : "#0a1726"
                        border.width: 1
                        border.color: root.selectedTab === modelData.value ? Theme.cyan : "#36556c"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: Theme.text
                        font.pixelSize: 12
                        font.family: Theme.fontFamily
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: root.selectedTab = modelData.value
                }
            }
            Item { Layout.fillWidth: true }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#06111e"
            radius: 8
            border.width: 1
            border.color: "#36536e"
            ScrollView {
                objectName: "auditLogScroll"
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                TextArea {
                    objectName: "auditLogText"
                    text: root.selectedTab === 0 ?
                          (root.sessionLog.length ? root.sessionLog : "—") :
                          (root.auditLog.length ? root.auditLog :
                          (root.logsFolderPath.length ?
                           "Saved action reports are stored at:\n" + root.logsFolderPath +
                           "\n\nUse OPEN LOG FOLDER to inspect individual TXT reports." :
                           "Backend log folder unavailable."))
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.NoWrap
                    color: "#b6c9d9"
                    selectionColor: "#275b84"
                    font.family: "Consolas"
                    font.pixelSize: 12
                    background: Rectangle { color: "transparent" }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.notice.length > 0
            text: root.notice
            wrapMode: Text.Wrap
            color: "#e4bb78"
            font.family: Theme.fontFamily
            font.pixelSize: 11
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            Text {
                Layout.fillWidth: true
                text: root.selectedTab === 0 ? "Live session log" :
                      (root.logsFolderPath.length ? root.logsFolderPath : "Saved TXT reports unavailable")
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: 11
            }
            Button {
                objectName: "openAuditFolderButton"
                text: "OPEN LOG FOLDER"
                enabled: typeof backend.openLogsFolder === "function"
                Layout.preferredWidth: 150
                Layout.preferredHeight: 36
                onClicked: root.openFolderRequested()
            }
            Button {
                text: "CLOSE"
                Layout.preferredWidth: 88
                Layout.preferredHeight: 36
                onClicked: root.close()
            }
        }
    }
}

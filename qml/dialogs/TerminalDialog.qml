import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Window {
    id: root
    objectName: "terminalDialog"
    title: "TECHGUY — Terminal"
    color: "#05080e"
    flags: Qt.Window
    width: 370
    height: 180
    minimumWidth: 370
    minimumHeight: 180
    // Expanded terminal must remain smaller than the parent tool window.
    // User-driven resizing is also bounded by the main-window and screen limits.
    property int compactWidth: 370
    property int compactHeight: 180
    property int expandedWidth: 650
    property int expandedHeight: 390
    property int mainWindowWidthLimit: 730
    property int mainWindowHeightLimit: 435
    maximumWidth: Math.max(minimumWidth,
        Math.min(700, mainWindowWidthLimit, Screen.desktopAvailableWidth - 36))
    maximumHeight: Math.max(minimumHeight,
        Math.min(430, mainWindowHeightLimit, Screen.desktopAvailableHeight - 36))
    property bool expanded: false
    signal commandSubmitted(string command)
    property int historyIndex: -1
    property var commandHistory: []
    property bool followBottom: true
    property bool submittedAtLeastOnce: false
    // The 2026-11-11 live-service backend exposes terminalOutput as the
    // authoritative terminal transcript. Do not load a historical console
    // banner before any command: the owner requires an initial single dash.
    property string authoritativeOutput: typeof backend.terminalOutput === "string" ?
                                         backend.terminalOutput : ""
    property bool confirmationPending: backend.terminalConfirmationPending === true
    property string pendingCommand: typeof backend.terminalPendingCommand === "string" ?
                                    backend.terminalPendingCommand : ""
    property string pendingWarning: typeof backend.terminalPendingWarning === "string" ?
                                    backend.terminalPendingWarning : ""

    onAuthoritativeOutputChanged: {
        if (submittedAtLeastOnce && authoritativeOutput.length)
            replaceTranscript(authoritativeOutput)
    }
    function replaceTranscript(value) {
        var incoming = String(value === undefined || value === null ? "" : value)
        if (!incoming.length || incoming === transcript.text)
            return
        var shouldFollow = followBottom
        transcript.text = incoming
        if (shouldFollow)
            Qt.callLater(function() { outputScroll.ScrollBar.vertical.position =
                Math.max(0, 1 - outputScroll.ScrollBar.vertical.size) })
    }

    function appendResponse(value) {
        var line = String(value === undefined || value === null ? "" : value)
        if (line.length === 0)
            return
        var previous = transcript.text
        transcript.text = previous === "-" ? line : previous + "\n" + line
        if (followBottom) Qt.callLater(function() { outputScroll.ScrollBar.vertical.position =
            Math.max(0, 1 - outputScroll.ScrollBar.vertical.size) })
    }

    function submitCommand(value) {
        var command = String(value).trim()
        if (command.length === 0) return
        var previous = transcript.text
        transcript.text = previous === "-" ? "> " + command : previous + "\n> " + command
        submittedAtLeastOnce = true
        commandHistory.push(command)
        historyIndex = commandHistory.length
        commandInput.clear()
        followBottom = true
        Qt.callLater(function() { outputScroll.ScrollBar.vertical.position =
            Math.max(0, 1 - outputScroll.ScrollBar.vertical.size) })
        commandSubmitted(command)
    }

    function centerInWorkArea() {
        // Screen.availableGeometry is not exposed by QQuickScreenInfo in Qt 6.
        // Use the attached workarea dimensions and include XFCE's top panel.
        // This keeps the terminal centered independently of the main window.
        var workX = Screen.virtualX
        var topInset = Qt.platform.os === "linux" ?
                       Math.max(0, Screen.height - Screen.desktopAvailableHeight) : 0
        var workY = Screen.virtualY + topInset
        x = Math.round(workX + (Screen.desktopAvailableWidth - width) / 2)
        y = Math.round(workY + (Screen.desktopAvailableHeight - height) / 2)
    }

    function toggleExpanded() {
        // Do not maximize the terminal or its parent tool.
        showNormal()
        if (expanded) {
            width = compactWidth
            height = compactHeight
            expanded = false
        } else {
            width = Math.min(expandedWidth, maximumWidth)
            height = Math.min(expandedHeight, maximumHeight)
            expanded = true
        }
        Qt.callLater(centerInWorkArea)
    }
    onWidthChanged: { if (visible) Qt.callLater(centerInWorkArea) }
    onHeightChanged: { if (visible) Qt.callLater(centerInWorkArea) }

    Item {
        anchors.fill: parent

        RowLayout {
            id: toolbar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 7
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            height: 27
            spacing: 6

            Text {
                text: "TERMINAL"
                color: "#a2c4eb"
                font.family: "Consolas"
                font.pixelSize: 11
            }
            Item { Layout.fillWidth: true }
            Button {
                objectName: "terminalExpandButton"
                text: root.expanded ? "COMPACT" : "EXPAND"
                Layout.preferredWidth: 77
                Layout.preferredHeight: 25
                background: Rectangle {
                    radius: 4
                    color: parent.hovered ? "#18334d" : "#101d2c"
                    border.width: 1
                    border.color: "#477394"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#d4e5f6"
                    font.pixelSize: 10
                    font.family: "Consolas"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: root.toggleExpanded()
            }
        }

        RowLayout {
            id: inputRow
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottomMargin: 8
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            height: 29
            spacing: 7
            Text {
                text: ">"
                color: "#e5e5e5"
                font.family: "Consolas"
                font.pixelSize: 13
            }
            TextField {
                id: commandInput
                objectName: "terminalCommandInput"
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#f0f3f7"
                font.family: "Consolas"
                font.pixelSize: 12
                placeholderText: ""
                background: Rectangle {
                    color: "#050505"
                    border.width: 0
                }
                onAccepted: root.submitCommand(text)
                Keys.onUpPressed: {
                    if (root.commandHistory.length === 0) return
                    root.historyIndex = Math.max(0, root.historyIndex - 1)
                    commandInput.text = root.commandHistory[root.historyIndex]
                }
                Keys.onDownPressed: {
                    if (root.commandHistory.length === 0) return
                    root.historyIndex = Math.min(root.commandHistory.length, root.historyIndex + 1)
                    commandInput.text = root.historyIndex === root.commandHistory.length ? "" : root.commandHistory[root.historyIndex]
                }
            }
        }

        Rectangle {
            id: outputPanel
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: toolbar.bottom
            anchors.bottom: inputRow.top
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 5
            anchors.bottomMargin: 5
            radius: 4
            color: "#050505"
            border.width: 1
            border.color: "#27384e"

            ScrollView {
                id: outputScroll
                objectName: "terminalOutputScroll"
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                ScrollBar.vertical: ScrollBar {
                    id: terminalVerticalBar
                    objectName: "terminalVerticalScrollBar"
                    policy: ScrollBar.AsNeeded
                    onPositionChanged: {
                        root.followBottom = position >= Math.max(0, 1 - size - 0.03)
                    }
                }
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded

                TextArea {
                    id: transcript
                    objectName: "terminalTranscript"
                    readOnly: true
                    text: "-"
                    color: "#e5e5e5"
                    selectionColor: "#315a88"
                    font.family: "Consolas"
                    font.pixelSize: 12
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: true
                    background: Rectangle { color: "transparent" }
                }
            }
        }
    }

    // Device-state-changing commands from the real backend require an
    // explicit confirmation. Its pending command/warning are backend truth.
    Rectangle {
        id: commandConfirmation
        objectName: "terminalConfirmationPanel"
        anchors.fill: parent
        z: 100
        color: "#f207111f"
        border.width: 1
        border.color: "#ad8150"
        visible: root.confirmationPending

        MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 6
            Text {
                text: "CONFIRM DEVICE COMMAND"
                color: "#ffe0a4"
                font.family: "Consolas"
                font.weight: Font.DemiBold
                font.pixelSize: 12
                Layout.fillWidth: true
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                Column {
                    width: commandConfirmation.width - 32
                    spacing: 5
                    Text {
                        text: root.pendingCommand
                        width: parent.width
                        wrapMode: Text.WrapAnywhere
                        color: "#f1f6ff"
                        font.family: "Consolas"
                        font.pixelSize: 11
                    }
                    Text {
                        text: root.pendingWarning
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: "#e4b878"
                        font.family: "Consolas"
                        font.pixelSize: 11
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Button {
                    objectName: "terminalCancelCommand"
                    text: "CANCEL"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 27
                    onClicked: {
                        if (typeof backend.cancelTerminalCommand === "function")
                            backend.cancelTerminalCommand()
                    }
                }
                Button {
                    objectName: "terminalConfirmCommand"
                    text: "CONFIRM COMMAND"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 27
                    enabled: typeof backend.confirmTerminalCommand === "function"
                    onClicked: {
                        if (typeof backend.confirmTerminalCommand === "function")
                            backend.confirmTerminalCommand()
                    }
                }
            }
        }
    }

    onVisibleChanged: {
        if (visible) {
            // Every fresh open starts as a compact, centered terminal.
            if (!expanded) {
                width = compactWidth
                height = compactHeight
            }
            Qt.callLater(centerInWorkArea)
            commandInput.forceActiveFocus()
        }
    }
}

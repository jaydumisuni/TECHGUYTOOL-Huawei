import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "components"
import "pages"
import "dialogs"

ApplicationWindow {
    id: app
    // Normal startup uses the approved reference's window footprint, centered.
    // Maximizing expands into the OS work area; restoring returns to normal size.
    readonly property int compactWidth: 1586
    readonly property int compactHeight: 992
    // Compact by default. 75% of the usable display, capped at a
    // 1152x721 normal window on larger desktops; keeps generous margins
    // around the app instead of reproducing the near-full-screen PNG size.
    // Intentionally compact normal window; reference layout remains scalable.
    // Maximize is available when the operator needs larger controls.
    readonly property real startupScale: Math.min(840 / compactWidth,
        (Screen.desktopAvailableWidth - 64) / compactWidth,
        (Screen.desktopAvailableHeight - 64) / compactHeight)
    readonly property real uiScale: Math.min(width / compactWidth, height / compactHeight)
    width: Math.round(compactWidth * startupScale)
    height: Math.round(compactHeight * startupScale)
    minimumWidth: 800
    minimumHeight: 500
    x: Screen.virtualX + Math.round((Screen.desktopAvailableWidth - width) / 2)
    // KRATOS/XFCE reserves its top panel. Windows taskbars usually reserve
    // the bottom, so their top origin remains zero. The PySide preview
    // additionally positions from QScreen.availableGeometry authoritatively.
    y: Screen.virtualY +
       Math.round((Qt.platform.os === "linux" ?
                   Screen.height - Screen.desktopAvailableHeight : 0) +
                  (Screen.desktopAvailableHeight - height) / 2)
    visible: true
    color: "transparent"
    title: "TECHGUY TOOL — HUAWEI"
    flags: Qt.Window | Qt.FramelessWindowHint
    palette.window: Theme.background
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.button: "#0c1929"
    palette.base: "#081322"
    palette.highlight: Theme.blue
    palette.highlightedText: Theme.text

    property int pageIndex: 0
    property string pageTitle: "Service Center"

    Component.onCompleted: {
        var actions = [
            "read_device", "open_terminal", "fix_drivers", "register_device",
            "frp_repair", "bootloader", "huawei_id", "verlist", "pair",
            "full_oeminfo", "flash_firmware", "board_repair", "backup_restore"
        ]
        for (var i = 0; i < actions.length; ++i)
            backend.registerUiAction(actions[i])
    }

    // Reference-coordinate canvas: real clickable controls remain live QML.
    // On smaller monitors the complete 1586×992 layout is scaled uniformly,
    // never cropped, rearranged, or replaced with a screenshot.
    Item {
        id: designCanvas
        x: Math.round((app.width - width * app.uiScale) / 2)
        y: Math.round((app.height - height * app.uiScale) / 2)
        width: app.compactWidth
        height: app.compactHeight
        scale: app.uiScale
        transformOrigin: Item.TopLeft

    Rectangle {
        anchors.fill: parent
        radius: app.visibility === Window.Maximized ? 0 : 15
        color: Theme.background
        border.width: 1
        border.color: "#51bdf5"
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.00; color: "#07101c" }
                GradientStop { position: 0.33; color: "#090c1b" }
                GradientStop { position: 0.70; color: "#071427" }
                GradientStop { position: 1.00; color: "#06111d" }
            }
        }

        Canvas {
            anchors.fill: parent
            opacity: 0.84
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var g1 = ctx.createRadialGradient(width * 0.55, height * 0.06, 20, width * 0.55, height * 0.06, width * 0.38)
                g1.addColorStop(0, "rgba(172,58,255,0.05)")
                g1.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = g1; ctx.fillRect(0, 0, width, height)
                var g2 = ctx.createRadialGradient(width * 0.98, height * 0.35, 5, width * 0.98, height * 0.35, width * 0.31)
                g2.addColorStop(0, "rgba(0,177,255,0.34)")
                g2.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = g2; ctx.fillRect(0, 0, width, height)
                ctx.strokeStyle = "rgba(165,70,255,0.26)"
                ctx.lineWidth = 28
                ctx.beginPath(); ctx.moveTo(width * 0.67, -40); ctx.bezierCurveTo(width * 0.77, height * 0.20, width * 0.69, height * 0.55, width * 0.83, height + 30); ctx.stroke()
            }
        }

        Canvas {
            anchors.fill: parent
            opacity: 0.82
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var bottomGlow = ctx.createRadialGradient(width * 0.58, height * 0.94, 10, width * 0.58, height * 0.94, width * 0.34)
                bottomGlow.addColorStop(0, "rgba(0,139,255,0.28)")
                bottomGlow.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = bottomGlow; ctx.fillRect(0, 0, width, height)
                ctx.strokeStyle = "rgba(202,62,255,0.26)"
                ctx.lineWidth = 7
                ctx.beginPath(); ctx.moveTo(width * 0.74, -70); ctx.bezierCurveTo(width * 0.80, height * 0.24, width * 0.73, height * 0.56, width * 0.87, height + 70); ctx.stroke()
                ctx.strokeStyle = "rgba(75,168,255,0.23)"
                ctx.lineWidth = 10
                ctx.beginPath(); ctx.moveTo(width * 0.50, height + 40); ctx.bezierCurveTo(width * 0.58, height * 0.72, width * 0.61, height * 0.42, width * 0.66, -50); ctx.stroke()
            }
        }

        // Static reference-derived branding plate only (no interactive pixels).
        // Layout placeholders below remain to preserve all header control positions.
        Image {
            id: headerBrandPlate
            x: 0; y: 0
            width: 650; height: 95
            source: "../assets/brand/header_brand_plate.png"
            fillMode: Image.Stretch
            smooth: true
            z: 5
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 7
            spacing: 0

            Item {
                id: header
                Layout.fillWidth: true
                Layout.preferredHeight: 95
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: app.startSystemMove()
                    onDoubleClicked: app.visibility === Window.Maximized ? app.showNormal() : app.showMaximized()
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 25
                    anchors.rightMargin: 18
                    spacing: 12
                    Image {
                        source: "../assets/brand/techguy_header.png"
                        opacity: 0.0
                        fillMode: Image.PreserveAspectFit
                        Layout.preferredWidth: 105
                        Layout.preferredHeight: 86
                    }
                    ColumnLayout {
                        Layout.preferredWidth: 570
                        opacity: 0.0
                        spacing: 4
                        Text { text: "TECHGUY TOOL — HUAWEI"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 26; font.weight: Font.DemiBold; font.letterSpacing: 0.8 }
                        Text { text: "SERVICE & RECOVERY EDITION"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13; font.letterSpacing: 2.2 }
                    }
                    Item { Layout.fillWidth: true }
                    RowLayout {
                        spacing: 10
                        Rectangle { width: 13; height: 13; radius: 7; color: Theme.purple; border.width: 2; border.color: "#8ab7ff" }
                        Text { text: backend.connected ? "Device connected" : "Waiting for device"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 15 }
                    }
                    ComboBox {
                        Layout.preferredWidth: 250
                        Layout.preferredHeight: 42
                        model: ["Auto Detect", "ADB", "Fastboot", "Upgrade Mode", "Rescue"]
                    }
                    Button {
                        id: settingsButton
                        objectName: "settingsButton"
                        Layout.preferredWidth: 48; Layout.preferredHeight: 45
                        text: "⚙"
                        font.family: "Segoe UI Symbol"; font.pixelSize: 24
                        background: Rectangle { radius: 8; color: settingsButton.hovered ? "#14243a" : "#0b1726"; border.width: 1; border.color: "#49647f" }
                        contentItem: Image { source: Qt.resolvedUrl("../assets/ui-icons/settings.svg"); fillMode: Image.PreserveAspectFit; sourceSize.width: 28; sourceSize.height: 28; smooth: true }
                        onClicked: settingsMenu.open()
                    }
                    Button {
                        id: terminalButton
                        Layout.preferredWidth: 48; Layout.preferredHeight: 45
                        text: ">_"
                        font.family: "Consolas"; font.pixelSize: 17
                        background: Rectangle { radius: 8; color: terminalButton.hovered ? "#14243a" : "#0b1726"; border.width: 1; border.color: "#49647f" }
                        contentItem: Text { text: terminalButton.text; color: Theme.text; font: terminalButton.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: terminalDialog.show()
                    }
                    Rectangle { width: 1; height: 42; color: "#526071" }
                    Button { flat: true; text: "—"; font.pixelSize: 21; onClicked: app.showMinimized(); contentItem: Text { text: parent.text; color: Theme.text; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter } }
                    Button { flat: true; text: app.visibility === Window.Maximized ? "❐" : "□"; font.pixelSize: 21; onClicked: app.visibility === Window.Maximized ? app.showNormal() : app.showMaximized(); contentItem: Text { text: parent.text; color: Theme.text; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter } }
                    Button { flat: true; text: "×"; font.pixelSize: 26; onClicked: app.close(); contentItem: Text { text: parent.text; color: Theme.text; font: parent.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter } }
                }
            }

            RowLayout {
                id: body
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                GlassPanel {
                    id: sidebar
                    Layout.preferredWidth: 310
                    Layout.fillHeight: true
                    panelColor: "#030912"
                    panelOpacity: 0.91
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 4
                        NavItem { Layout.fillWidth: true; text: "Service Center"; glyph: "▦"; iconName: "service-center"; selected: app.pageIndex === 0; onSelectedClicked: { app.pageIndex = 0; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Device Information"; glyph: "▯"; iconName: "device-information"; selected: app.pageIndex === 1; onSelectedClicked: { app.pageIndex = 1; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Firmware Flash"; glyph: "▣"; iconName: "firmware-flash"; selected: app.pageIndex === 2; onSelectedClicked: { app.pageIndex = 2; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Partition Manager"; glyph: "◉"; iconName: "partition-manager"; selected: app.pageIndex === 3; onSelectedClicked: { app.pageIndex = 3; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Backup & Restore"; glyph: "☁"; iconName: "backup-restore"; selected: app.pageIndex === 4; onSelectedClicked: { app.pageIndex = 4; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Operation History"; glyph: "◴"; iconName: "operation-history"; selected: app.pageIndex === 5; onSelectedClicked: { app.pageIndex = 5; app.pageTitle = text } }
                        Item { Layout.fillHeight: true }
                        Image {
                            // Decorative ghost/background plate extracted from the approved
                            // comparison art, not a screenshot of interactive controls.
                            source: "../assets/brand/sidebar_mascot_plate.png"
                            opacity: 1.0
                            fillMode: Image.Stretch
                            Layout.fillWidth: true
                            Layout.preferredHeight: 410
                        }
                    }
                }

                Loader {
                    id: pageLoader
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourceComponent: app.pageIndex === 0 ? serviceComponent : app.pageIndex === 1 ? deviceInformationComponent : app.pageIndex === 2 ? firmwareComponent : app.pageIndex === 3 ? partitionManagerComponent : app.pageIndex === 4 ? backupRestoreComponent : operationHistoryComponent
                }

                GlassPanel {
                    id: livePanel
                    Layout.preferredWidth: 450
                    Layout.fillHeight: true
                    panelOpacity: 0.78
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 13
                        spacing: 10
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 7
                            Text {
                                text: "LIVE OPERATION LOG"
                                color: "#72a7ff"
                                font.family: Theme.fontFamily
                                font.pixelSize: 17
                                font.letterSpacing: 0.7
                                Layout.fillWidth: true
                            }
                            Button {
                                id: logsButton
                                objectName: "logsButton"
                                text: "LOGS"
                                Layout.preferredWidth: 75
                                Layout.preferredHeight: 29
                                background: Rectangle {
                                    radius: 5
                                    color: logsButton.hovered ? "#1b3e60" : "#0b2035"
                                    border.width: 1
                                    border.color: logsButton.hovered ? Theme.cyan : "#4d7394"
                                }
                                contentItem: Text {
                                    text: logsButton.text
                                    color: "#d8ebfb"
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    font.weight: Font.Medium
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                onClicked: auditLogsDialog.openAudit()
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 164
                            columns: 2
                            rowSpacing: 8
                            columnSpacing: 8
                            StatusCard { Layout.fillWidth: true; title: "Connection"; value: backend.connected ? "Connected" : "Not Connected"; glyph: "♧"; iconName: "power-plug" }
                            StatusCard { Layout.fillWidth: true; title: "Interface"; value: backend.deviceInterface; glyph: "▯"; iconName: "usb-interface" }
                            StatusCard { Layout.fillWidth: true; title: "Platform"; value: backend.devicePlatform; glyph: "▣"; iconName: "firmware-flash" }
                            StatusCard { Layout.fillWidth: true; title: "Security"; value: backend.deviceSecurity; glyph: "◇"; iconName: "security" }
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 8
                            color: "#06111e"
                            border.width: 1
                            border.color: "#2e4b68"
                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 4
                                SemanticLog {
                                    rawText: backend.logText
                                }
                            }
                        }
                        ProgressBar {
                            id: operationProgress
                            Layout.fillWidth: true
                            Layout.preferredHeight: 14
                            value: backend.progress / 100.0
                            background: Rectangle {
                                implicitHeight: 14
                                radius: 5
                                color: "#071727"
                                border.width: 1
                                border.color: "#446583"
                            }
                            contentItem: Item {
                                Rectangle {
                                    width: operationProgress.visualPosition * parent.width
                                    height: parent.height
                                    radius: 5
                                    visible: width > 0
                                    gradient: Gradient {
                                        orientation: Gradient.Horizontal
                                        GradientStop { position: 0; color: "#a13bdc" }
                                        GradientStop { position: 1; color: "#2eabeb" }
                                    }
                                }
                            }
                        }
                        Text { Layout.fillWidth: true; text: backend.progress + "%"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 61
                radius: 8
                panelOpacity: 0.72
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 25
                    anchors.rightMargin: 25
                    spacing: 14
                    Text { text: "ⓘ"; color: "#d5dce4"; font.family: "Segoe UI Symbol"; font.pixelSize: 21 }
                    Text { text: "TECHGUY TOOL Huawei v0.1.0"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 13 }
                    Item { Layout.fillWidth: true }
                    Text { text: "◷"; color: Theme.text; font.pixelSize: 21 }
                    Text { text: Qt.formatTime(new Date(), "hh:mm:ss AP"); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    Rectangle { width: 1; height: 25; color: "#435469" }
                    Text { text: "▣"; color: Theme.text; font.pixelSize: 18 }
                    Text {
                        text: typeof backend.hostSystemLabel === "string" && backend.hostSystemLabel.length ?
                              backend.hostSystemLabel :
                              (Qt.platform.os === "windows" ? "Windows" :
                               Qt.platform.os === "linux" ? "Linux" : Qt.platform.os)
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                    Rectangle { width: 1; height: 25; color: "#435469" }
                    Text { text: "♢"; color: Theme.text; font.pixelSize: 20 }
                    Text { text: backend.registered ? "Registered" : "Administrator"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                }
            }
        }
    }

    } // designCanvas

    Component { id: serviceComponent; ServiceCenterPage {} }
    Component { id: deviceInformationComponent; DeviceInformationPage {} }
    Component { id: firmwareComponent; FirmwareFlashPage {} }
    Component { id: partitionManagerComponent; PartitionManagerPage {} }
    Component { id: backupRestoreComponent; BackupRestorePage {} }
    Component { id: operationHistoryComponent; OperationHistoryPage {} }

    SettingsMenu {
        id: settingsMenu
        parent: Overlay.overlay
        x: designCanvas.x + (app.compactWidth - width - 93) * app.uiScale
        y: designCanvas.y + 94 * app.uiScale
        scale: app.uiScale
        onFixDriversRequested: driverDialog.open()
        onRegisterRequested: registerDialog.open()
        onTestpointRequested: testpointDialog.openManual()
        onAboutRequested: aboutDialog.open()
    }
    RegisterDialog { id: registerDialog; parent: Overlay.overlay; scale: app.uiScale }
    DriverDialog { id: driverDialog; parent: Overlay.overlay; scale: app.uiScale }
    AboutDialog { id: aboutDialog; parent: Overlay.overlay; scale: app.uiScale }
    TestpointDialog { id: testpointDialog; parent: Overlay.overlay; scale: app.uiScale }
    AuditLogsDialog {
        id: auditLogsDialog
        parent: Overlay.overlay
        scale: app.uiScale
        onOpenFolderRequested: {
            if (typeof backend.openLogsFolder === "function")
                backend.openLogsFolder()
        }
    }
    TerminalDialog {
        id: terminalDialog
        mainWindowWidthLimit: Math.max(370, app.width - 110)
        mainWindowHeightLimit: Math.max(180, app.height - 90)
        onCommandSubmitted: function(command) {
            // The backend owns validation, execution and audit custody.
            // Never imply execution when a command adapter is not present.
            if (typeof backend.submitTerminalLine === "function")
                backend.submitTerminalLine(command)
            else
                terminalDialog.appendResponse("Command backend unavailable — nothing executed.")
        }
    }
    Connections {
        target: backend
        ignoreUnknownSignals: true
        function onTerminalOutputChanged() {
            if (typeof backend.terminalOutput === "string")
                terminalDialog.replaceTranscript(backend.terminalOutput)
        }
        // Compatibility with a chunk-emitting backend: no fabricated output.
        function onTerminalOutputReady(output) {
            if (typeof backend.terminalOutput !== "string")
                terminalDialog.appendResponse(output)
        }
        // The tool can request the exact same popup during a service operation.
        function onTestpointRequired(modelId, operationLabel) {
            testpointDialog.openForOperation(modelId, operationLabel)
        }
        function onPinoutChanged() {
            testpointDialog.backendPinoutChanged()
        }
        function onPinoutBusyChanged() {
            testpointDialog.backendPinoutChanged()
        }
        function onPinoutSearchReady(resultsJson) {
            testpointDialog.applyPinoutSearchResults(resultsJson)
        }
        function onPinoutReferenceReady(referenceJson) {
            testpointDialog.applyPinoutReference(referenceJson)
        }
    }
}

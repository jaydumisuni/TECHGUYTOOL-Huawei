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
    width: 1586
    height: 992
    minimumWidth: 1280
    minimumHeight: 800
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
                GradientStop { position: 0.00; color: "#030914" }
                GradientStop { position: 0.33; color: "#050a16" }
                GradientStop { position: 0.70; color: "#04101f" }
                GradientStop { position: 1.00; color: "#03101c" }
            }
        }

        Canvas {
            anchors.fill: parent
            opacity: 0.52
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var g1 = ctx.createRadialGradient(width * 0.55, height * 0.06, 20, width * 0.55, height * 0.06, width * 0.38)
                g1.addColorStop(0, "rgba(172,58,255,0.14)")
                g1.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = g1; ctx.fillRect(0, 0, width, height)
                var g2 = ctx.createRadialGradient(width * 0.98, height * 0.35, 5, width * 0.98, height * 0.35, width * 0.31)
                g2.addColorStop(0, "rgba(0,177,255,0.16)")
                g2.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = g2; ctx.fillRect(0, 0, width, height)
                ctx.strokeStyle = "rgba(165,70,255,0.22)"
                ctx.lineWidth = 11
                ctx.beginPath(); ctx.moveTo(width * 0.67, -40); ctx.bezierCurveTo(width * 0.77, height * 0.20, width * 0.69, height * 0.55, width * 0.83, height + 30); ctx.stroke()
            }
        }

        Canvas {
            anchors.fill: parent
            opacity: 0.58
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var bottomGlow = ctx.createRadialGradient(width * 0.58, height * 0.94, 10, width * 0.58, height * 0.94, width * 0.34)
                bottomGlow.addColorStop(0, "rgba(0,139,255,0.14)")
                bottomGlow.addColorStop(1, "rgba(0,0,0,0)")
                ctx.fillStyle = bottomGlow; ctx.fillRect(0, 0, width, height)
                ctx.strokeStyle = "rgba(202,62,255,0.20)"
                ctx.lineWidth = 5
                ctx.beginPath(); ctx.moveTo(width * 0.74, -70); ctx.bezierCurveTo(width * 0.80, height * 0.24, width * 0.73, height * 0.56, width * 0.87, height + 70); ctx.stroke()
                ctx.strokeStyle = "rgba(75,168,255,0.16)"
                ctx.lineWidth = 6
                ctx.beginPath(); ctx.moveTo(width * 0.50, height + 40); ctx.bezierCurveTo(width * 0.58, height * 0.72, width * 0.61, height * 0.42, width * 0.66, -50); ctx.stroke()
            }
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
                        source: "../assets/brand/techguy_logo.svg"
                        fillMode: Image.PreserveAspectFit
                        Layout.preferredWidth: 105
                        Layout.preferredHeight: 86
                    }
                    ColumnLayout {
                        Layout.preferredWidth: 570
                        spacing: 4
                        Text { text: "TECHGUY TOOL — HUAWEI"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 28; font.weight: Font.DemiBold; font.letterSpacing: 0.8 }
                        Text { text: "SERVICE & RECOVERY EDITION"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 14; font.letterSpacing: 1.7 }
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
                        Layout.preferredWidth: 48; Layout.preferredHeight: 45
                        text: "⚙"
                        font.family: "Segoe UI Symbol"; font.pixelSize: 24
                        background: Rectangle { radius: 8; color: settingsButton.hovered ? "#14243a" : "#0b1726"; border.width: 1; border.color: "#49647f" }
                        contentItem: Text { text: settingsButton.text; color: Theme.text; font: settingsButton.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: settingsMenu.open()
                    }
                    Button {
                        id: terminalButton
                        Layout.preferredWidth: 48; Layout.preferredHeight: 45
                        text: ">_"
                        font.family: "Consolas"; font.pixelSize: 17
                        background: Rectangle { radius: 8; color: terminalButton.hovered ? "#14243a" : "#0b1726"; border.width: 1; border.color: "#49647f" }
                        contentItem: Text { text: terminalButton.text; color: Theme.text; font: terminalButton.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { backend.runAction("open_terminal"); terminalDialog.show() }
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
                    panelOpacity: 0.90
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 4
                        NavItem { Layout.fillWidth: true; text: "Service Center"; glyph: "▦"; selected: app.pageIndex === 0; onSelectedClicked: { app.pageIndex = 0; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Device Information"; glyph: "▯"; selected: app.pageIndex === 1; onSelectedClicked: { app.pageIndex = 1; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Firmware Flash"; glyph: "▣"; selected: app.pageIndex === 2; onSelectedClicked: { app.pageIndex = 2; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Partition Manager"; glyph: "◉"; selected: app.pageIndex === 3; onSelectedClicked: { app.pageIndex = 3; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Backup & Restore"; glyph: "☁"; selected: app.pageIndex === 4; onSelectedClicked: { app.pageIndex = 4; app.pageTitle = text } }
                        NavItem { Layout.fillWidth: true; text: "Operation History"; glyph: "◴"; selected: app.pageIndex === 5; onSelectedClicked: { app.pageIndex = 5; app.pageTitle = text } }
                        Item { Layout.fillHeight: true }
                        Image {
                            source: "../assets/brand/techguy_mascot.png"
                            fillMode: Image.PreserveAspectFit
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
                    panelOpacity: 0.90
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 13
                        spacing: 10
                        Text { text: "LIVE OPERATION LOG"; color: "#72a7ff"; font.family: Theme.fontFamily; font.pixelSize: 17; font.letterSpacing: 0.7 }
                        GridLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 164
                            columns: 2
                            rowSpacing: 8
                            columnSpacing: 8
                            StatusCard { Layout.fillWidth: true; title: "Connection"; value: backend.connected ? "Connected" : "Not Connected"; glyph: "♧" }
                            StatusCard { Layout.fillWidth: true; title: "Interface"; value: backend.deviceInterface; glyph: "▯" }
                            StatusCard { Layout.fillWidth: true; title: "Platform"; value: backend.devicePlatform; glyph: "▣" }
                            StatusCard { Layout.fillWidth: true; title: "Security"; value: backend.deviceSecurity; glyph: "◇" }
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
                                TextArea {
                                    text: backend.logText
                                    readOnly: true
                                    wrapMode: TextEdit.Wrap
                                    color: "#9fb4c8"
                                    selectionColor: "#245782"
                                    font.family: "Consolas"
                                    font.pixelSize: 12
                                    background: Rectangle { color: "transparent" }
                                }
                            }
                        }
                        ProgressBar { Layout.fillWidth: true; value: backend.progress / 100.0 }
                        Text { Layout.fillWidth: true; text: backend.progress + "%"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 61
                radius: 8
                panelOpacity: 0.84
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
                    Text { text: "Windows 11 Pro 23H2 (64-bit)"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    Rectangle { width: 1; height: 25; color: "#435469" }
                    Text { text: "♢"; color: Theme.text; font.pixelSize: 20 }
                    Text { text: backend.registered ? "Registered" : "Administrator"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                }
            }
        }
    }

    Component { id: serviceComponent; ServiceCenterPage {} }
    Component { id: deviceInformationComponent; DeviceInformationPage {} }
    Component { id: firmwareComponent; FirmwareFlashPage {} }
    Component { id: partitionManagerComponent; PartitionManagerPage {} }
    Component { id: backupRestoreComponent; BackupRestorePage {} }
    Component { id: operationHistoryComponent; OperationHistoryPage {} }

    SettingsMenu {
        id: settingsMenu
        parent: Overlay.overlay
        x: app.width - width - 105
        y: 70
        onFixDriversRequested: driverDialog.open()
        onRegisterRequested: registerDialog.open()
        onTestpointRequested: testpointDialog.open()
        onAboutRequested: aboutDialog.open()
    }
    RegisterDialog { id: registerDialog; parent: Overlay.overlay }
    DriverDialog { id: driverDialog; parent: Overlay.overlay }
    AboutDialog { id: aboutDialog; parent: Overlay.overlay }
    TestpointDialog { id: testpointDialog; parent: Overlay.overlay }
    TerminalDialog { id: terminalDialog }
}
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property string packageRole: "base"
    property var recovery: {
        try { return JSON.parse(backend.recoverySummaryJson) }
        catch (error) { return ({"blockers":["READINESS_UNAVAILABLE"],"packages":{}}) }
    }

    function authorityFor(role) {
        if (role === "base") return baseAuthority.text
        if (role === "cust") return custAuthority.text
        return preloadAuthority.text
    }

    function packageState(role) {
        return recovery.packages && recovery.packages[role] ? recovery.packages[role] : ({"selected":false,"display_name":"","sha256":""})
    }

    FileDialog {
        id: packageDialog
        title: "Select Huawei " + root.packageRole.toUpperCase() + " recovery package"
        nameFilters: ["Huawei recovery packages (*.zip *.app *.bin *.img)", "All files (*)"]
        onAccepted: backend.setRecoveryPackage(root.packageRole, selectedFile.toString(), root.authorityFor(root.packageRole))
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 9

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "NATIVE SYSTEM RECOVERY"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 22
                font.weight: Font.Medium
                Layout.fillWidth: true
            }
            Rectangle {
                radius: 7
                color: backend.recoveryCanStart ? "#123827" : "#281c26"
                border.width: 1
                border.color: backend.recoveryCanStart ? "#42b883" : "#84506a"
                implicitWidth: 176
                implicitHeight: 34
                Text {
                    anchors.centerIn: parent
                    text: backend.recoveryCanStart ? "RECOVERY READY" : "RECOVERY GUARDED"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                }
            }
        }

        Text {
            text: "Locked-device stock recovery using Huawei identity, Base + CUST + PRELOAD authority, and a governed native transport."
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#243c55" }
        SectionLabel { number: 1; text: "DEVICE / RECOVERY IDENTITY" }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 66
            spacing: 0
            Repeater {
                model: [
                    {label:"FAMILY", value: root.recovery.family || "—"},
                    {label:"BUILD", value: root.recovery.build || "—"},
                    {label:"MODEL / REGION", value: (root.recovery.model || "UNRESOLVED") + " / " + (root.recovery.region || "UNRESOLVED")},
                    {label:"LOCK STATE", value: root.recovery.lock_state || "—"}
                ]
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0a1525"
                    border.width: 1
                    border.color: "#314a66"
                    Column {
                        anchors.centerIn: parent
                        width: parent.width - 12
                        spacing: 5
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                        Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; elide: Text.ElideMiddle }
                    }
                }
            }
        }

        SectionLabel { number: 2; text: "RECOVERY PACKAGE AUTHORITY" }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                Text { text: "BASE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 70 }
                TextField { id: baseAuthority; Layout.fillWidth: true; placeholderText: "Official label, e.g. CLT-LGRP2-OVS 9.1.0.325"; color: Theme.text; font.family: Theme.fontFamily }
                Text { text: root.packageState("base").display_name || "Not selected"; color: root.packageState("base").selected ? Theme.text : Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 190; elide: Text.ElideMiddle }
                GlowButton { text: "BROWSE"; Layout.preferredWidth: 100; onClicked: { root.packageRole="base"; packageDialog.open() } }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "CUST"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 70 }
                TextField { id: custAuthority; Layout.fillWidth: true; placeholderText: "Official label, e.g. CLT-L29-CUST …(C432)"; color: Theme.text; font.family: Theme.fontFamily }
                Text { text: root.packageState("cust").display_name || "Not selected"; color: root.packageState("cust").selected ? Theme.text : Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 190; elide: Text.ElideMiddle }
                GlowButton { text: "BROWSE"; Layout.preferredWidth: 100; onClicked: { root.packageRole="cust"; packageDialog.open() } }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "PRELOAD"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 70 }
                TextField { id: preloadAuthority; Layout.fillWidth: true; placeholderText: "Official label, e.g. CLT-L29-PRELOAD …(C432R1)"; color: Theme.text; font.family: Theme.fontFamily }
                Text { text: root.packageState("preload").display_name || "Not selected"; color: root.packageState("preload").selected ? Theme.text : Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 190; elide: Text.ElideMiddle }
                GlowButton { text: "BROWSE"; Layout.preferredWidth: 100; onClicked: { root.packageRole="preload"; packageDialog.open() } }
            }
        }

        SectionLabel { number: 3; text: "RECOVERY AUTHORITY" }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 70
            spacing: 8
            Repeater {
                model: [
                    {label:"IDENTITY", value: root.recovery.identity_status || "NOT CHECKED"},
                    {label:"PACKAGES", value: root.recovery.package_ready ? "VERIFIED" : "NOT READY"},
                    {label:"ANTI-ROLLBACK", value: root.recovery.anti_rollback_state || "UNRESOLVED"},
                    {label:"TRANSPORT", value: root.recovery.transport_status || "UNCERTIFIED"},
                    {label:"HUAWEI AUTH", value: root.recovery.official_authorization_ready ? "READY" : "NOT READY"}
                ]
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 6
                    color: "#0a1525"
                    border.width: 1
                    border.color: "#314a66"
                    Column {
                        anchors.centerIn: parent
                        spacing: 5
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 9 }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.value; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; font.weight: Font.DemiBold }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 92
            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6
                Text { text: "BLOCKERS"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10 }
                Text {
                    width: parent.width
                    text: root.recovery.blockers && root.recovery.blockers.length ? root.recovery.blockers.join(" • ") : "All recovery authorities are green."
                    color: root.recovery.blockers && root.recovery.blockers.length ? "#f2b8c6" : "#8fd8b1"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: root.recovery.destructive_warning || "Native Huawei System Recovery may erase user data."
                    color: "#efc37a"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                text: "VERIFY RECOVERY PLAN"
                onClicked: backend.runAction("flash_firmware")
            }
            GlowButton {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                text: backend.recoveryCanStart ? "START RECOVERY" : "START RECOVERY — BLOCKED"
                enabled: backend.recoveryCanStart
                onClicked: backend.requestNativeRecoveryStart()
            }
        }
    }
}

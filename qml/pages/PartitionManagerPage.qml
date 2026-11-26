import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property var selectedPartition: ({})
    property string pendingPartition: ""
    FileDialog {
        id: partitionImage
        title: "Select matching raw partition image"
        nameFilters: ["Partition image (*.img *.bin)", "All files (*)"]
        onAccepted: backend.startPartition("write",root.pendingPartition,selectedFile.toString())
    }
    FileDialog {
        id: restoreManifest
        title: "Select verified partition backup receipt"
        nameFilters: ["Backup receipt (backup.json)"]
        onAccepted: backend.startPartition("restore","",selectedFile.toString())
    }
    FolderDialog {
        id: backupFolder
        title: "Select backup destination"
        onAccepted: backend.startPartition("backup",root.pendingPartition,selectedFolder.toString())
    }
    function shown(value) {
        return value === undefined || value === null || value === "" ? "Not reported" : String(value)
    }
    function partitionSize(row) {
        var n = Number(row.size_bytes || 0)
        if (n <= 0) return "Not reported"
        return n >= 1073741824 ? (n / 1073741824).toFixed(2) + " GiB" : (n / 1048576).toFixed(2) + " MiB"
    }
    Connections {
        target: backend
        function onDeviceChanged() { root.selectedPartition = ({}) }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8
        DeviceSearchHeader {
            pageTitle: "PARTITION MANAGER"
            placeholder: "Search Huawei / Honor model..."
            hint: "Switch to Chipset to browse Kirin platform families"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            GlowButton { text: "↻  REFRESH"; Layout.preferredWidth: 150; Layout.preferredHeight: 42; onClicked: backend.runAction("read_device") }
            GlowButton { text: "▤  READ"; Layout.preferredWidth: 150; Layout.preferredHeight: 42; enabled: !!root.selectedPartition.name && !backend.operationBusy; onClicked: { root.pendingPartition = root.selectedPartition.name; backupFolder.open() } }
            Button {
                text: "✎  WRITE"; enabled: !!root.selectedPartition.name && !backend.operationBusy; onClicked: { root.pendingPartition = root.selectedPartition.name; partitionImage.open() }
                 Layout.preferredWidth: 150; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: parent.enabled ? Theme.text : "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                text: "♲  ERASE"; enabled: !!root.selectedPartition.name && !backend.operationBusy; onClicked: backend.startPartition("erase",root.selectedPartition.name,""); Layout.preferredWidth: 150; Layout.preferredHeight: 42
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: parent.enabled ? Theme.text : "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Item { Layout.fillWidth: true }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 292
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 0
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    color: "#0a1726"
                    border.width: 1
                    border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                        Text { text: "□"; color: Theme.muted; font.pixelSize: 15; Layout.preferredWidth: 28 }
                        Text { text: "PARTITION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 185 }
                        Text { text: "LUN"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 65 }
                        Text { text: "START"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.fillWidth: true }
                        Text { text: "SIZE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 105 }
                        Text { text: "STATUS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; Layout.preferredWidth: 85 }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ListView {
                        id: partitionList
                        objectName: "livePartitionInventory"
                        anchors.fill: parent
                        clip: true
                        model: backend.devicePartitions
                        currentIndex: -1
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: partitionList.width
                            height: 32
                            color: partitionList.currentIndex === index ? "#234764" : index % 2 === 0 ? "#0a1829" : "#102033"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                Text { text: ""; Layout.preferredWidth: 28 }
                                Text { text: root.shown(modelData.name); color: Theme.text; font.pixelSize: 12; Layout.preferredWidth: 185; elide: Text.ElideRight }
                                Text { text: root.shown(modelData.lun); color: Theme.muted; font.pixelSize: 12; Layout.preferredWidth: 65; elide: Text.ElideRight }
                                Text { text: root.shown(modelData.start_offset_bytes); color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                                Text { text: root.partitionSize(modelData); color: Theme.text; font.pixelSize: 12; Layout.preferredWidth: 105 }
                                Text { text: modelData.read_only ? "Read-only" : "Observed"; color: Theme.muted; font.pixelSize: 12; Layout.preferredWidth: 85 }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: { partitionList.currentIndex = index; root.selectedPartition = modelData }
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                    Column {
                        anchors.centerIn: parent
                        visible: partitionList.count === 0
                        spacing: 8
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: backend.connected ? "No partition inventory reported in this mode." : "Connect and read a device to begin partition discovery."
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                        }
                    }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 165
            panelOpacity: 0.62
            RowLayout {
                anchors.fill: parent
                anchors.margins: 13
                spacing: 16

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 9
                    Text { text: "SELECTED PARTITION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Partition: " + root.shown(root.selectedPartition.name); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "LUN: " + root.shown(root.selectedPartition.lun); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Start: " + root.shown(root.selectedPartition.start_offset_bytes); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Text { text: "Size: " + root.partitionSize(root.selectedPartition); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "File System: " + root.shown(root.selectedPartition.filesystem); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Type: " + root.shown(root.selectedPartition.risk); color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        }
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.fillHeight: true
                    color: "#2e4661"
                }

                RowLayout {
                    Layout.preferredWidth: 245
                    Layout.fillHeight: true
                    spacing: 12
                    Item {
                        Layout.preferredWidth: 92
                        Layout.preferredHeight: 92
                        Rectangle {
                            anchors.centerIn: parent
                            width: 84; height: 84; radius: 42
                            color: "transparent"
                            border.width: 10
                            border.color: "#52667c"
                            Rectangle {
                                anchors.centerIn: parent
                                width: 58; height: 58; radius: 29
                                color: "#0b1727"
                                Text { anchors.centerIn: parent; text: "—\nUsed"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Text { text: "■  Used      —"; color: "#b06cff"; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "■  Free       —"; color: "#4ba9ff"; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "■  Total      —"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Button {
                Layout.fillWidth: true; Layout.preferredHeight: 46; enabled: !!root.selectedPartition.name && !backend.operationBusy; text: "⇧  BACKUP PARTITION"; onClicked: { root.pendingPartition = root.selectedPartition.name; backupFolder.open() }
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: parent.enabled ? Theme.text : "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.fillWidth: true; Layout.preferredHeight: 46; enabled: backend.connected && !backend.operationBusy; text: "⇩  RESTORE PARTITION"; onClicked: restoreManifest.open()
                background: Rectangle { radius: 7; color: "#0a1422"; border.width: 1; border.color: "#2a3d56" }
                contentItem: Text { text: parent.text; color: parent.enabled ? Theme.text : "#526277"; font.family: Theme.fontFamily; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }
    }
}

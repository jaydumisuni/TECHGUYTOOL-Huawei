import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."
import "../components"

GlassPanel {
    id: root
    property var rows: []
    property var selected: ({})
    property string selectedLog: ""
    function refresh() { rows = backend.operationHistory() }
    readonly property var filtered: rows.filter(function(row) {
        var query = searchField.text.toLowerCase()
        return (!query || JSON.stringify(row).toLowerCase().indexOf(query) >= 0)
            && (operationFilter.currentIndex === 0 || row.operation === operationFilter.currentText)
            && (resultFilter.currentIndex === 0 || row.result === resultFilter.currentText)
            && (dateFilter.currentIndex === 0 || row.date === dateFilter.currentText)
    })
    Component.onCompleted: refresh()
    Connections { target: backend; function onActionLogSaved() { root.refresh() } }
    FileDialog {
        id: exportDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["History JSON (*.json)"]
        defaultSuffix: "json"
        onAccepted: {
            if (!backend.exportOperationHistory(selectedFile.toString(),root.filtered))
                root.selectedLog = "Export failed. Choose a new destination file."
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 8
        DeviceSearchHeader {
            pageTitle: "OPERATION HISTORY"
            placeholder: "Search Huawei / Honor model..."
            hint: "Switch to Chipset to browse Kirin platform families"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            TextField {
                id: searchField
                Layout.fillWidth: true; Layout.preferredHeight: 36
                placeholderText: "Search operations..."
            }
            ComboBox { id: operationFilter; Layout.preferredWidth: 118; Layout.preferredHeight: 36; model: ["All Operations"].concat(Array.from(new Set(root.rows.map(function(r){return r.operation}))).sort()) }
            ComboBox { id: resultFilter; Layout.preferredWidth: 105; Layout.preferredHeight: 36; model: ["All Results"].concat(Array.from(new Set(root.rows.map(function(r){return r.result}))).sort()) }
            ComboBox { id: dateFilter; Layout.preferredWidth: 105; Layout.preferredHeight: 36; model: ["All Dates"].concat(Array.from(new Set(root.rows.map(function(r){return r.date}))).sort().reverse()) }
            Button {
                Layout.preferredWidth: 82; Layout.preferredHeight: 36; enabled: root.filtered.length > 0; text: "EXPORT"; onClicked: exportDialog.open()
                background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                Layout.preferredWidth: 100; Layout.preferredHeight: 36; text: "RESET FILTER"; onClicked: { searchField.text = ""; operationFilter.currentIndex = 0; resultFilter.currentIndex = 0; dateFilter.currentIndex = 0; root.selected = ({}); root.selectedLog = "" }
                background: Rectangle { radius: 5; color: "#23122f"; border.width: 1; border.color: "#6f3887" }
                contentItem: Text { text: parent.text; color: "#a66dc5"; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 292
            panelOpacity: 0.64
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 0
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 34
                    color: "#0a1726"; border.width: 1; border.color: "#304862"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9
                        Text { text: "TIME"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 92 }
                        Text { text: "DEVICE"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 165 }
                        Text { text: "OPERATION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: "RESULT"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 85 }
                        Text { text: "DURATION"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 85 }
                        Text { text: "BACKUP"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 11; Layout.preferredWidth: 100 }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ListView {
                        id: historyList
                        objectName: "operationHistoryList"
                        anchors.fill: parent; clip: true; model: root.filtered
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: historyList.width; height: 32
                            color: root.selected.path === modelData.path ? "#234764" : index % 2 ? "#102033" : "#0a1829"
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 8
                                Text { text: (modelData.time || "").slice(11,19); color: Theme.text; Layout.preferredWidth: 92; font.pixelSize: 11 }
                                Text { text: modelData.model || "Not recorded"; color: Theme.text; Layout.preferredWidth: 165; font.pixelSize: 11; elide: Text.ElideRight }
                                Text { text: modelData.operation; color: Theme.text; Layout.fillWidth: true; font.pixelSize: 11; elide: Text.ElideRight }
                                Text { text: modelData.result; color: Theme.text; Layout.preferredWidth: 85; font.pixelSize: 11; elide: Text.ElideRight }
                                Text { text: modelData.elapsed || "?"; color: Theme.muted; Layout.preferredWidth: 85; font.pixelSize: 11 }
                                Text { text: "See report"; color: Theme.muted; Layout.preferredWidth: 100; font.pixelSize: 11 }
                            }
                            MouseArea { anchors.fill: parent; onClicked: { root.selected = modelData; root.selectedLog = backend.readOperationLog(modelData.path) } }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                    Text { anchors.centerIn: parent; visible: historyList.count === 0; text: "No matching operation reports."; color: Theme.muted }
                }
            }
        }

        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.62
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "SELECTED OPERATION DETAILS"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12; font.weight: Font.DemiBold }
                    Item { Layout.fillWidth: true }
                    Button {
                        Layout.preferredWidth: 95; Layout.preferredHeight: 30; enabled: !!root.selected.path; text: "OPEN LOG"; onClicked: backend.openOperationLog(root.selected.path)
                        background: Rectangle { radius: 5; color: "#0a1626"; border.width: 1; border.color: "#315272" }
                        contentItem: Text { text: parent.text; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 14
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        columns: 2
                        rowSpacing: 6
                        columnSpacing: 10
                        Text { text: "Session ID"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: root.selected.run || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Time"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: root.selected.time || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Device"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: root.selected.model || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Operation"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: root.selected.operation || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: "Result"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        Text { text: root.selected.result || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                    }
                    Rectangle {
                        Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#2e4661"
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 6
                        GridLayout {
                            Layout.fillWidth: true; columns: 2; rowSpacing: 5; columnSpacing: 8
                            Text { text: "Interface"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: root.selected.interface || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Platform"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: root.selected.platform || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: "Engine Response"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 12 }
                            Text { text: root.selected.message || "?"; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea {
                                text: root.selectedLog || "Select an operation to view its report."
                                readOnly: true
                                wrapMode: TextEdit.Wrap
                                color: "#9fb4c8"
                                selectionColor: "#245782"
                                font.family: "Consolas"
                                font.pixelSize: 11
                                background: Rectangle { color: "#06111e"; radius: 5; border.width: 1; border.color: "#243c55" }
                            }
                        }
                    }
                }
            }
        }
    }
}

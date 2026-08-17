import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."
import "../components"

Popup {
    id: root
    objectName: "testpointDialog"
    width: 760
    height: 650
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 14

    property var allModels: []
    property var filteredModels: []
    property var selectedModel: null
    property var selectedRecord: ({})
    property string expectedInterface: "Select an exact model"
    property bool hasReference: selectedRecord && selectedRecord.reference !== undefined && selectedRecord.reference !== ""

    function loadAuthority() {
        var profiles = JSON.parse(backend.deviceProfilesJson)
        allModels = profiles.models || []
        refreshFilter()
    }

    function refreshFilter() {
        var query = searchField.text.trim().toLowerCase()
        var next = []
        for (var i = 0; i < allModels.length; ++i) {
            var item = allModels[i]
            var haystack = (item.model + " " + item.name + " " + item.platform).toLowerCase()
            if (query === "" || haystack.indexOf(query) !== -1)
                next.push(item)
        }
        filteredModels = next
        if (selectedModel !== null) {
            var stillVisible = false
            for (var j = 0; j < next.length; ++j)
                if (next[j].model === selectedModel.model) stillVisible = true
            if (!stillVisible) clearSelection()
        }
    }

    function clearSelection() {
        selectedModel = null
        selectedRecord = ({})
        expectedInterface = "Select an exact model"
    }

    function selectModel(item) {
        selectedModel = item
        expectedInterface = backend.expectedServiceInterface(item.model)
        selectedRecord = JSON.parse(backend.testpointRecordJson(item.model))
    }

    onOpened: {
        searchField.text = ""
        clearSelection()
        loadAuthority()
        searchField.forceActiveFocus()
    }

    background: GlassPanel {
        panelOpacity: 0.98
        borderColor: "#577da3"
    }

    contentItem: ColumnLayout {
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "TESTPOINT / PINOUT LIBRARY"
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: 19
                font.weight: Font.DemiBold
                font.letterSpacing: 0.8
                Layout.fillWidth: true
            }
            Button {
                text: "×"
                flat: true
                font.pixelSize: 24
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
            text: "Exact-model references only. The tool never substitutes a similar Huawei/Honor model or downloads a pinout automatically."
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        TextField {
            id: searchField
            objectName: "testpointSearchField"
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            placeholderText: "Search exact model, product name or chipset..."
            color: Theme.text
            font.family: Theme.fontFamily
            onTextChanged: root.refreshFilter()
            background: Rectangle {
                radius: 7
                color: "#081522"
                border.width: 1
                border.color: searchField.activeFocus ? Theme.cyan : "#405876"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            GlassPanel {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                panelOpacity: 0.70
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Text {
                        text: "EXACT MODEL"
                        color: "#72a7ff"
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        font.letterSpacing: 0.8
                    }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        Column {
                            width: parent.width
                            spacing: 6
                            Repeater {
                                model: root.filteredModels
                                Button {
                                    width: parent ? parent.width : 280
                                    height: 58
                                    hoverEnabled: true
                                    background: Rectangle {
                                        radius: 7
                                        color: root.selectedModel && root.selectedModel.model === modelData.model ? "#173455" : parent.hovered ? "#11283d" : "#0a1928"
                                        border.width: 1
                                        border.color: root.selectedModel && root.selectedModel.model === modelData.model ? Theme.cyan : "#365571"
                                    }
                                    contentItem: Column {
                                        leftPadding: 10
                                        spacing: 2
                                        Text { text: modelData.model + " — " + modelData.name; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 13 }
                                        Text { text: modelData.platform; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11 }
                                    }
                                    onClicked: root.selectModel(modelData)
                                }
                            }
                        }
                    }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                panelOpacity: 0.70
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Text {
                        text: root.selectedModel ? root.selectedModel.model + " — " + root.selectedModel.name : "NO MODEL SELECTED"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 17
                        font.weight: Font.Medium
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Text {
                        text: root.selectedModel ? "Platform: " + root.selectedModel.platform : "Choose an exact model from the verified local profile list."
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 74
                        radius: 7
                        color: "#071522"
                        border.width: 1
                        border.color: "#345b7c"
                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 5
                            Text { text: "EXPECTED SERVICE INTERFACE"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; font.letterSpacing: 0.8 }
                            Text { text: root.expectedInterface; color: Theme.cyan; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.Medium }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: "#06111e"
                        border.width: 1
                        border.color: root.hasReference ? Theme.green : "#6d5262"

                        Image {
                            anchors.fill: parent
                            anchors.margins: 10
                            source: root.hasReference ? root.selectedRecord.reference : ""
                            fillMode: Image.PreserveAspectFit
                            visible: root.hasReference
                        }

                        Column {
                            anchors.centerIn: parent
                            width: parent.width - 36
                            spacing: 8
                            visible: !root.hasReference
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "NO APPROVED TESTPOINT REFERENCE"
                                color: "#ef9aa7"
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                width: parent.width
                                text: root.selectedModel ? "No owner-approved Testpoint image/reference is installed for this exact model. The tool will not substitute another model." : "Select an exact model to check the owner-approved local Testpoint catalogue."
                                color: Theme.muted
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 86
                        radius: 7
                        color: "#09192a"
                        border.width: 1
                        border.color: "#3d5d7a"
                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4
                            Text { text: "OPERATION RESUME STATE"; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 10; font.letterSpacing: 0.8 }
                            Text { text: backend.selectedOperationLabel; color: Theme.purple; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.Medium }
                            Text { text: "After the governor verifies the required service entry, the original repair may resume from its retained stage. This popup grants no write authority."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.Wrap; width: parent.width }
                        }
                    }
                }
            }
        }
    }
}

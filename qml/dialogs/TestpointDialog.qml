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
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 14

    property var allModels: []
    property var filteredModels: []
    property var selectedModel: null
    property var selectedRecord: ({})
    property string expectedInterface: "Select an exact model"
    // Network I/O, exact-model validation and evidence-hash verification belong
    // to a future backend adapter, not to QML. Reference images must be handed
    // to the UI through a local file or Qt image-provider URI.
    property string lookupStatus: ""
    property string pendingExactModel: ""
    property string operationContext: ""
    property string pinoutBrand: "Huawei"
    property string pinoutType: "test-point"
    property string lastPinoutSearch: ""
    property string lastPinoutImage: ""
    property string renderedReference: {
        var source = String(selectedRecord && selectedRecord.reference ? selectedRecord.reference : "")
        return /^(file:\/\/|qrc:|image:\/\/)/.test(source) ? source : ""
    }
    property bool hasReference: renderedReference.length > 0
    property string referenceText: {
        if (!selectedRecord || selectedRecord.owner_approved !== true) return ""
        var text = selectedRecord.instructions || selectedRecord.text || selectedRecord.notes || ""
        return Array.isArray(text) ? text.join("\n") : String(text)
    }
    property bool hasTextReference: referenceText.trim().length > 0

    function openManual() {
        pendingExactModel = ""
        operationContext = ""
        open()
    }

    function openForOperation(modelId, operationLabel) {
        pendingExactModel = String(modelId || "").trim()
        operationContext = String(operationLabel || "")
        open()
    }

    function applyPinoutSearchResults(payload) {
        try {
            var decoded = JSON.parse(String(payload || "{}"))
            if (!decoded) throw Error("Empty response")
            var items = []
            if (Array.isArray(decoded.results)) {
                for (var i=0;i<decoded.results.length;i++) {
                    var rec=decoded.results[i]
                    // Present browse-only matches but never auto-load them.
                    items.push({
                        model:String(rec.model || ""),
                        name:String(rec.brand || "") + (rec.exact ? " • EXACT" : " • BROWSE ONLY"),
                        platform:String(rec.type || "test-point"),
                        record_id:String(rec.id || ""),
                        images:Array.isArray(rec.images) ? rec.images : [],
                        exact:rec.exact === true
                    })
                }
                lookupStatus=String(decoded.exact_count || 0) +
                    " exact match(es), " + items.length + " result(s)."
            } else if (Array.isArray(decoded.models)) {
                items=decoded.models
                lookupStatus=items.length + " model(s) returned."
            } else {
                lookupStatus="No model results returned by pinout backend."
                return
            }
            allModels=items
            refreshFilter()
        } catch (error) {
            lookupStatus="Pinout search results were invalid."
        }
    }

    function applyPinoutReference(payload) {
        try {
            var decoded=JSON.parse(String(payload || "{}"))
            if (!decoded || !selectedModel) {
                lookupStatus="No exact-model reference is selected."
                return
            }
            if (selectedModel.record_id) {
                if (selectedModel.exact !== true ||
                    String(decoded.record_id || "") !== selectedModel.record_id ||
                    String(decoded.model || "") !== selectedModel.model ||
                    !/^[a-f0-9]{64}$/.test(String(decoded.sha256 || "")) ||
                    !/^file:\/\//.test(String(decoded.local_url || ""))) {
                    lookupStatus="Remote image is not verified for this exact model."
                    return
                }
                selectedRecord={
                    owner_approved:true,
                    reference:String(decoded.local_url),
                    evidence_sha256:String(decoded.sha256),
                    source_url:String(decoded.source_url || "")
                }
            } else {
                if (decoded.model !== selectedModel.model ||
                    decoded.owner_approved !== true) {
                    lookupStatus="Reference has not been approved for this exact model."
                    return
                }
                selectedRecord=decoded
            }
            lookupStatus=hasReference || hasTextReference ?
                         "Exact-model reference ready." :
                         "No verified image or instructions returned."
        } catch (error) {
            lookupStatus="Pinout image response could not be read."
        }
    }

    function backendPinoutChanged() {
        if (!visible) return
        if (typeof backend.pinoutStatus === "string")
            lookupStatus=backend.pinoutStatus
        var results=typeof backend.pinoutResultsJson === "string" ?
                    backend.pinoutResultsJson : ""
        if (results && results !== lastPinoutSearch) {
            lastPinoutSearch=results
            applyPinoutSearchResults(results)
        }
        var image=typeof backend.pinoutImageJson === "string" ?
                  backend.pinoutImageJson : ""
        if (image && image !== "{}" && image !== lastPinoutImage) {
            lastPinoutImage=image
            applyPinoutReference(image)
        }
    }

    function requestOnlineSearch() {
        var query=searchField.text.trim()
        if (!query.length) {
            lookupStatus="Enter an exact model or part number."
            return
        }
        if (typeof backend.searchPinouts === "function") {
            lastPinoutSearch=typeof backend.pinoutResultsJson === "string" ?
                             backend.pinoutResultsJson : ""
            lastPinoutImage=""
            lookupStatus="Searching the trusted pinout library..."
            if (backend.searchPinouts(pinoutBrand,query,pinoutType) !== true)
                lookupStatus=typeof backend.pinoutStatus === "string" ?
                             backend.pinoutStatus : "Pinout search not accepted."
        } else if (typeof backend.searchPinoutModels === "function") {
            lookupStatus="Searching the connected pinout library..."
            backend.searchPinoutModels(query)
        } else {
            lookupStatus="Online pinout backend not connected; local model search only."
        }
    }

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
        selectedModel=item
        if (item.record_id) {
            selectedRecord=({})
            expectedInterface="Exact-model reference only"
            if (item.exact !== true) {
                lookupStatus="Browse-only match. Exact device model required before image loading."
                return
            }
            if (!item.images.length || !item.images[0].id) {
                lookupStatus="No validated image is listed for this model."
                return
            }
            if (typeof backend.loadPinoutImage === "function") {
                lookupStatus="Fetching verified exact-model pinout image..."
                lastPinoutImage=typeof backend.pinoutImageJson === "string" ?
                                backend.pinoutImageJson : ""
                backend.loadPinoutImage(item.record_id,String(item.images[0].id))
            } else {
                lookupStatus="Pinout image backend is unavailable."
            }
            return
        }
        expectedInterface=backend.expectedServiceInterface(item.model)
        selectedRecord=JSON.parse(backend.testpointRecordJson(item.model))
        if (selectedRecord && selectedRecord.expected_interface)
            expectedInterface=String(selectedRecord.expected_interface)
        lookupStatus=hasReference || hasTextReference ?
                     "Verified local reference." :
                     "No approved local reference; search the trusted library."
    }

    onOpened: {
        lookupStatus = ""
        searchField.text = pendingExactModel
        clearSelection()
        loadAuthority()
        if (pendingExactModel.length) {
            for (var i = 0; i < filteredModels.length; ++i) {
                if (filteredModels[i].model === pendingExactModel) {
                    selectModel(filteredModels[i])
                    break
                }
            }
            if (selectedModel === null)
                requestOnlineSearch()
        }
        searchField.forceActiveFocus()
        pendingExactModel = ""
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
            text: root.operationContext.length ?
                "Required for: " + root.operationContext + ". Use only an exact-model, verified reference." :
                "Exact-model pinout images and service instructions. Local references or verified backend results only."
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: 12
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            TextField {
                id: searchField
                objectName: "testpointSearchField"
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                placeholderText: "Search exact model, product name or chipset..."
                color: Theme.text
                font.family: Theme.fontFamily
                onTextChanged: root.refreshFilter()
                onAccepted: root.requestOnlineSearch()
                background: Rectangle {
                    radius: 7
                    color: "#081522"
                    border.width: 1
                    border.color: searchField.activeFocus ? Theme.cyan : "#405876"
                }
            }
            ComboBox {
                objectName: "pinoutBrandSelector"
                model: ["Huawei", "Honor"]
                Layout.preferredWidth: 94
                Layout.preferredHeight: 44
                onActivated: function(index) {
                    root.pinoutBrand=index === 1 ? "Honor" : "Huawei"
                }
            }
            ComboBox {
                objectName: "pinoutTypeSelector"
                model: ["TESTPOINT", "ISP PINOUT"]
                Layout.preferredWidth: 123
                Layout.preferredHeight: 44
                onActivated: function(index) {
                    root.pinoutType=index === 1 ? "isp-pinout" : "test-point"
                }
            }
            Button {
                objectName: "searchPinoutButton"
                text: "SEARCH LIBRARY"
                Layout.preferredHeight: 44
                Layout.preferredWidth: 155
                onClicked: root.requestOnlineSearch()
                ToolTip.visible: hovered
                ToolTip.text: "Backend search; no direct network requests in this UI"
            }
        }
        Text {
            Layout.fillWidth: true
            visible: root.lookupStatus.length > 0
            text: root.lookupStatus
            color: Theme.cyan
            font.family: Theme.fontFamily
            font.pixelSize: 11
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            GlassPanel {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                panelOpacity: 0.82
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
                panelOpacity: 0.82
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

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 7
                            visible: root.hasReference || root.hasTextReference
                            Image {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: root.hasTextReference ? 95 : 180
                                visible: root.hasReference
                                source: root.renderedReference
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.hasReference ? 92 : 250
                                Layout.fillHeight: !root.hasReference
                                visible: root.hasTextReference
                                clip: true
                                TextArea {
                                    objectName: "pinoutInstructionsText"
                                    text: root.referenceText
                                    textFormat: TextEdit.PlainText
                                    wrapMode: TextEdit.Wrap
                                    readOnly: true
                                    selectByMouse: true
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 12
                                    background: Rectangle { color: "transparent" }
                                }
                            }
                        }

                        Column {
                            anchors.centerIn: parent
                            width: parent.width - 36
                            spacing: 8
                            visible: !root.hasReference && !root.hasTextReference
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
                                text: root.selectedModel ? "No exact-model reference has been provided by the backend. A similar-model pinout will never be substituted." : "Search for an exact model, or open this dialog from a requested operation."
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
                            Text { text: root.operationContext.length ? root.operationContext : backend.selectedOperationLabel; color: Theme.purple; font.family: Theme.fontFamily; font.pixelSize: 13; font.weight: Font.Medium }
                            Text { text: "After the governor verifies the required service entry, the original repair may resume from its retained stage. This popup grants no write authority."; color: Theme.muted; font.family: Theme.fontFamily; font.pixelSize: 11; wrapMode: Text.Wrap; width: parent.width }
                        }
                    }
                }
            }
        }
    }
}

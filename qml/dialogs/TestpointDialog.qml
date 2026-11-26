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
    closePolicy: operationContext.length ? Popup.NoAutoClose : Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 14

    property var allModels: []
    property var filteredModels: []
    property var selectedModel: null
    property var selectedRecord: ({})
    property string expectedInterface: "Select an exact model"
    // Images come from the live verified catalogue via the backend, not QML
    // network requests. Browsing an image never authorizes a device operation.
    property string lookupStatus: ""
    property string pendingExactModel: ""
    // Kept only as an internal call compatibility value; not shown in the library UI.
    property string operationContext: ""
    property int selectedImageIndex: 0
    readonly property int imageCount: selectedModel && selectedModel.images ?
                                     selectedModel.images.length : 0
    signal imageEnlargeRequested(string imageUrl, string modelName)
    property string pinoutBrand: "Huawei"
    property string pinoutType: "test-point"
    property string lastPinoutSearch: ""
    property string lastPinoutImage: ""
    property bool showingOnlineResults: false
    property string onlineQuery: ""
    property string renderedReference: {
        var source = String(selectedRecord && selectedRecord.reference ? selectedRecord.reference : "")
        return /^(file:\/\/|qrc:|image:\/\/)/.test(source) ? source : ""
    }
    property bool hasReference: renderedReference.length > 0
    readonly property bool previewReady: hasReference && pinoutPreview.status === Image.Ready
    readonly property bool previewFailed: hasReference && pinoutPreview.status === Image.Error
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
        if (operationContext.length) return
        try {
            var decoded = JSON.parse(String(payload || "{}"))
            if (!decoded) throw Error("Empty response")
            var items = []
            if (Array.isArray(decoded.results)) {
                for (var i=0;i<decoded.results.length;i++) {
                    var rec=decoded.results[i]
                    // Browse entries are valid images to *view*, not device
                    // identity assertions or permissions to run a repair.
                    items.push({
                        model:String(rec.model || ""),
                        name:String(rec.brand || "") + (rec.exact ? " - EXACT MATCH" : " - VIEW IMAGE"),
                        platform:String(rec.type || "test-point"),
                        record_id:String(rec.id || ""),
                        images:Array.isArray(rec.images) ? rec.images : [],
                        exact:rec.exact === true
                    })
                }
                lookupStatus=decoded.browse_gallery === true ?
                    ("Browse " + decoded.result_count + " available image records. Click a model to view.") :
                    (String(decoded.exact_count || 0) + " exact match(es), " + items.length + " result(s).")
            } else if (Array.isArray(decoded.models)) {
                items=decoded.models
                lookupStatus=items.length + " model(s) returned."
            } else {
                lookupStatus="No model results returned by pinout backend."
                return
            }
            showingOnlineResults=Array.isArray(decoded.results)
            onlineQuery=String(decoded.query || searchField.text).trim()
            allModels=items
            refreshFilter()
            if (decoded.browse_gallery === true && items.length > 0 &&
                searchField.text.trim() === "" && operationContext.length === 0) {
                // Show a clearly labeled *gallery preview* immediately.
                // It is not a match to any connected device.
                selectModel(items[0])
            } else if (showingOnlineResults && decoded.auto_select_allowed === true &&
                Number(decoded.exact_count) === 1) {
                for (var j=0; j<items.length; j++) {
                    if (items[j].exact === true) {
                        selectModel(items[j])
                        break
                    }
                }
            }
        } catch (error) {
            lookupStatus="Pinout search results were invalid."
        }
    }

    function applyPinoutReference(payload) {
        if (operationContext.length) return
        try {
            var decoded=JSON.parse(String(payload || "{}"))
            if (!decoded || !selectedModel) {
                lookupStatus="No exact-model reference is selected."
                return
            }
            if (selectedModel.record_id) {
                // A browse result may be viewed as an image; this does not
                // approve a device operation. Validate the actual catalogue
                // record, selected image ID, model identity and file digest.
                if (String(decoded.record_id || "") !== selectedModel.record_id ||
                    String(decoded.image_id || "") !== String(selectedModel.images[selectedImageIndex].id) ||
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
        if (!visible || operationContext.length) return
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

    function browseLibrary() {
        if (typeof backend.browsePinouts !== "function") {
            lookupStatus="Pinout catalogue browser is unavailable."
            return
        }
        lastPinoutSearch=typeof backend.pinoutResultsJson === "string" ?
                         backend.pinoutResultsJson : ""
        lastPinoutImage=""
        if (backend.browsePinouts(pinoutBrand,pinoutType) !== true)
            lookupStatus=typeof backend.pinoutStatus === "string" ?
                         backend.pinoutStatus : "Cannot open pinout catalogue."
        else
            lookupStatus="Loading verified image catalogue..."
    }

    function requestOnlineSearch() {
        var query=searchField.text.trim()
        if (!query.length) {
            browseLibrary()
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
        showingOnlineResults = false
        onlineQuery = ""
        allModels = profiles.models || []
        refreshFilter()
    }

    function normalizeSearch(value) {
        return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()
    }

    function refreshFilter() {
        var query = normalizeSearch(searchField.text)
        var next = []
        if (showingOnlineResults) {
            // Backend already applied exact-model and alias matching.
            // Never discard its trusted matches merely due to hyphen/space
            // differences (e.g. VOG-AL00 versus VOG AL00).
            if (query === normalizeSearch(onlineQuery))
                next = allModels.slice()
        } else {
            for (var i = 0; i < allModels.length; ++i) {
                var item = allModels[i]
                var haystack = normalizeSearch(item.model + " " + item.name + " " + item.platform)
                if (query === "" || haystack.indexOf(query) !== -1)
                    next.push(item)
            }
        }
        filteredModels = next
        if (selectedModel !== null) {
            var stillVisible = false
            for (var j = 0; j < next.length; ++j)
                if (next[j].record_id === selectedModel.record_id &&
                    next[j].model === selectedModel.model) stillVisible = true
            if (!stillVisible) clearSelection()
        }
    }

    function clearSelection() {
        selectedModel = null
        selectedRecord = ({})
        expectedInterface = "Select an exact model"
        selectedImageIndex=0
    }

    function loadSelectedImage(index) {
        if (!selectedModel || !selectedModel.record_id ||
            index < 0 || index >= imageCount) return
        var image = selectedModel.images[index]
        if (!image || !image.id) {
            lookupStatus="This image has no validated reference ID."
            return
        }
        if (typeof backend.loadPinoutImage !== "function") {
            lookupStatus="Pinout image backend is unavailable."
            return
        }
        if (backend.pinoutBusy === true) {
            lookupStatus="Please wait for the current image to load."
            return
        }
        selectedImageIndex=index
        selectedRecord=({})
        lookupStatus="Loading image " + (index + 1) + " of " + imageCount + "..."
        // A second selection of the very same image yields the same JSON.
        // Reset deduplication before the backend emits its next reply;
        // otherwise an identical cached response leaves the preview blank.
        lastPinoutImage=""
        if (backend.loadPinoutImage(selectedModel.record_id,String(image.id)) !== true)
            lookupStatus=typeof backend.pinoutStatus === "string" ?
                         backend.pinoutStatus : "Pinout image request unavailable."
    }

    function selectModel(item) {
        selectedModel=item
        selectedImageIndex=0
        if (item.record_id) {
            selectedRecord=({})
            expectedInterface="Exact-model reference only"
            // Manually viewing a catalogue image is permitted for browse
            // results; no device operation consumes this selection.
            loadSelectedImage(0)
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
        if (operationContext.length) {
            // The automatic repair path uses only the existing approved local
            // reference. A manual gallery search does not authorize a repair.
            var exact = allModels.filter(function(row) {return row.model === pendingExactModel})
            if (exact.length === 1) selectModel(exact[0])
            else lookupStatus = "No exact local model reference available."
            lookupStatus += " Waiting for the selected device interface."
        } else
            browseLibrary() // Manual gallery opens with real image records.
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
                onClicked: { if (root.operationContext.length) backend.cancelServiceEntry(); root.close() }
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
            text: "Browse available Huawei or Honor test-point and ISP images. Search to narrow models; click an image to enlarge."
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
                placeholderText: "Browse images or search a model..."
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
                enabled: !backend.pinoutBusy
                Layout.preferredWidth: 94
                Layout.preferredHeight: 44
                onActivated: function(index) {
                    root.pinoutBrand=index === 1 ? "Honor" : "Huawei"
                    root.clearSelection()
                    root.requestOnlineSearch()
                }
            }
            ComboBox {
                objectName: "pinoutTypeSelector"
                model: ["TESTPOINT", "ISP PINOUT"]
                enabled: !backend.pinoutBusy
                Layout.preferredWidth: 123
                Layout.preferredHeight: 44
                onActivated: function(index) {
                    root.pinoutType=index === 1 ? "isp-pinout" : "test-point"
                    root.clearSelection()
                    root.requestOnlineSearch()
                }
            }
            Button {
                objectName: "searchPinoutButton"
                text: searchField.text.trim().length ? "SEARCH" : "BROWSE IMAGES"
                enabled: !backend.pinoutBusy
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
                    ListView {
                        id: pinoutModelList
                        objectName: "pinoutModelList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.filteredModels
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        delegate: Button {
                            width: ListView.view ? ListView.view.width - 12 : 260
                            height: 58
                            enabled: !backend.pinoutBusy
                            hoverEnabled: true
                            background: Rectangle {
                                radius: 7
                                color: root.selectedModel && root.selectedModel.record_id === modelData.record_id ? "#173455" : parent.hovered ? "#11283d" : "#0a1928"
                                border.width: 1
                                border.color: root.selectedModel && root.selectedModel.record_id === modelData.record_id ? Theme.cyan : "#365571"
                            }
                            contentItem: Column {
                                leftPadding: 10
                                spacing: 2
                                Text {
                                    text: modelData.model + " - " + modelData.name
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                    width: parent.width - 16
                                }
                                Text {
                                    text: modelData.platform
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                }
                            }
                            onClicked: root.selectModel(modelData)
                        }
                    }
                    Text {
                        objectName: "pinoutModelCount"
                        text: root.filteredModels.length + " models in this list"
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        Layout.fillWidth: true
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
                                id: pinoutPreview
                                objectName: "pinoutPreviewImage"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: root.hasTextReference ? 95 : 180
                                visible: root.hasReference
                                source: root.renderedReference
                                fillMode: Image.PreserveAspectFit
                                smooth: true
                                asynchronous: true
                                cache: true
                                onStatusChanged: {
                                    if (status === Image.Error)
                                        root.lookupStatus = "Pinout image could not be displayed. Retry the selection."
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: root.hasReference
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.imageEnlargeRequested(root.renderedReference,
                                                      root.selectedModel ? root.selectedModel.model : "Pinout")
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                visible: root.hasReference
                                Button {
                                    objectName: "pinoutEnlargeButton"
                                    text: "ENLARGE / ZOOM"
                                    enabled: root.hasReference
                                    Layout.preferredWidth: 165
                                    onClicked: root.imageEnlargeRequested(root.renderedReference,
                                              root.selectedModel ? root.selectedModel.model : "Pinout")
                                }
                                Item { Layout.fillWidth: true }
                                Button {
                                    objectName: "pinoutPreviousImage"
                                    text: "PREV"
                                    visible: root.imageCount > 1
                                    enabled: root.selectedImageIndex > 0
                                    onClicked: root.loadSelectedImage(root.selectedImageIndex - 1)
                                }
                                Text {
                                    visible: root.imageCount > 1
                                    text: (root.selectedImageIndex + 1) + " / " + root.imageCount
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 11
                                }
                                Button {
                                    objectName: "pinoutNextImage"
                                    text: "NEXT"
                                    visible: root.imageCount > 1
                                    enabled: root.selectedImageIndex < root.imageCount - 1
                                    onClicked: root.loadSelectedImage(root.selectedImageIndex + 1)
                                }
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
                                text: "NO PINOUT IMAGE SELECTED"
                                color: "#ef9aa7"
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                width: parent.width
                                text: root.selectedModel ? "Image unavailable for the selected catalogue entry." : "Choose an image from the library on the left."
                                color: Theme.muted
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }

                }
            }
        }
    }
}

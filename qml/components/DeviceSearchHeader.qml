import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root
    objectName: "sharedDeviceSearchHeader"

    property string pageTitle: ""
    property string placeholder: "Search Huawei / Honor model..."
    property string hint: "Search exact Huawei models or enter an unlisted target."
    property bool interactiveTarget: true
    property string selectedBy: "MODEL"
    property string queryText: ""
    property string selectionError: ""
    property var profileData: JSON.parse(backend.deviceProfilesJson)
    property var filteredResults: findOptions(selectedBy, queryText)

    Layout.fillWidth: true
    spacing: 7

    function chipsetRows() {
        var entries = []
        var seen = ({})
        var groups = profileData.platform_families || []
        for (var i = 0; i < groups.length; i++) {
            var label = String(groups[i].name || "")
            var match = /^Kirin\s+(\d{3,4})(?:\/(\d{3,4}))?$/i.exec(label)
            if (match) {
                var suffixes = match[2] ? [match[1], match[2]] : [match[1]]
                for (var j = 0; j < suffixes.length; j++) {
                    var name = "kirin" + suffixes[j]
                    if (!seen[name]) {
                        entries.push({value: name, label: "Kirin " + suffixes[j],
                                      detail: "Exact Fastboot product: " + name, guide: false})
                        seen[name] = true
                    }
                }
            } else {
                entries.push({value: "", label: label,
                              detail: "Category only — enter the exact chipset identifier",
                              guide: true})
            }
        }
        var loaders = profileData.loader_families || []
        for (var n = 0; n < loaders.length; n++) {
            var cpu = String(loaders[n].cpu || "")
            var numeric = /^hisi(\d{3,4})$/.exec(cpu)
            var value = numeric && cpu !== "hisi620" && cpu !== "hisi710" ? "kirin" + numeric[1] : cpu
            if (!seen[value]) {
                entries.push({value: value, label: value === cpu ? cpu + " (exact loader)" : "Kirin " + numeric[1],
                              detail: "Reference loader family: " + cpu + " (" + loaders[n].container_count + " containers)",
                              guide: false})
                seen[value] = true
            }
        }
        return entries
    }

    function findOptions(mode, search) {
        var needle = String(search || "").trim().toLowerCase()
        var options = []
        if (mode === "MODEL") {
            var models = profileData.models || []
            for (var i = 0; i < models.length; i++) {
                var entry = models[i]
                var model = String(entry.model || "").toUpperCase()
                var name = String(entry.name || "")
                var platform = String(entry.platform || "")
                if (!needle || (model + " " + name + " " + platform).toLowerCase().indexOf(needle) >= 0)
                    options.push({value: model, label: model + "  |  " + name,
                                  detail: platform, guide: false})
            }
            var exact = String(search || "").trim().toUpperCase()
            var format = /^[A-Z0-9][A-Z0-9_.-]{2,63}$/
            if (format.test(exact) && exact.indexOf("-") >= 0) {
                var exists = models.some(function(m) {
                    return String(m.model || "").toUpperCase() === exact
                })
                if (!exists)
                    options.push({value: exact, label: "Use exact model " + exact,
                                  detail: "Manual model — chipset must be verified separately",
                                  guide: false})
            }
        } else {
            var chips = chipsetRows()
            for (var k = 0; k < chips.length; k++) {
                var item = chips[k]
                if (!needle || (item.value + " " + item.label + " " + item.detail).toLowerCase().indexOf(needle) >= 0)
                    options.push(item)
            }
            var manual = String(search || "").trim().toLowerCase().replace(/\s+/g, "")
            if (/^[a-z0-9][a-z0-9_.-]{2,63}$/.test(manual) &&
                    manual !== "qualcommhuawei" && manual !== "mediatekhuawei" &&
                    !chips.some(function(m) { return m.value === manual }))
                options.push({value: manual, label: "Use exact chipset " + manual,
                              detail: "Matched to connected Fastboot product during preflight",
                              guide: false})
        }
        return options
    }

    function selectMode(mode) {
        if (!interactiveTarget || backend.operationBusy)
            return
        selectedBy = mode
        selectionError = ""
        searchInput.text = ""
        queryText = ""
        showSuggestions()
        searchInput.forceActiveFocus()
    }

    function showSuggestions() {
        if (!interactiveTarget)
            return
        var overlay = Overlay.overlay
        if (!overlay)
            return
        var point = searchFrame.mapToItem(overlay, 0, searchFrame.height + 3)
        var right = searchFrame.mapToItem(overlay, searchFrame.width, searchFrame.height + 3)
        var paintedWidth = Math.max(200, right.x - point.x)
        suggestionPopup.x = Math.max(0, Math.min(point.x, overlay.width - paintedWidth))
        suggestionPopup.y = point.y
        suggestionPopup.width = paintedWidth
        suggestionPopup.height = Math.min(248, Math.max(58, filteredResults.length * 46 + 8))
        suggestionPopup.open()
    }

    function selectOption(item) {
        if (backend.operationBusy)
            return
        selectionError = ""
        if (item.guide) {
            selectedBy = "CHIPSET"
            searchInput.text = ""
            queryText = ""
            suggestionPopup.close()
            searchInput.forceActiveFocus()
            return
        }
        if (selectedBy === "MODEL")
            backend.selectDeviceProfile(item.value)
        else
            backend.setFirmwareChipset(item.value)
        searchInput.text = item.value
        queryText = item.value
        suggestionPopup.close()
    }

    function commitEntry() {
        var raw = String(searchInput.text || "").trim()
        if (!raw) {
            suggestionPopup.close()
            return
        }
        var items = findOptions(selectedBy, raw)
        var exact = selectedBy === "MODEL" ? raw.toUpperCase() : raw.toLowerCase().replace(/\s+/g, "")
        var resolved = items.find(function(item) {
            return !item.guide && item.value.toLowerCase() === exact.toLowerCase()
        })
        if (resolved) {
            selectOption(resolved)
        } else {
            // A partial name like "P30" is not a validated device model.
            selectionError = "Choose a matching result or enter an exact model / chipset."
            showSuggestions()
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        Text {
            visible: root.pageTitle.length > 0
            text: root.pageTitle
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 22
            font.weight: Font.Medium
            Layout.fillWidth: true
        }
        Text {
            text: "SELECT DEVICE BY"
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: 12
        }
        Rectangle {
            Layout.preferredWidth: 200
            Layout.preferredHeight: 34
            radius: 6
            color: "#0b1727"
            border.width: 1
            border.color: "#3b5270"

            Row {
                anchors.fill: parent
                Rectangle {
                    objectName: "deviceSelectorModel"
                    width: parent.width / 2
                    height: parent.height
                    radius: 6
                    color: root.selectedBy === "MODEL" ? "#4435a7" : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "MODEL"
                        color: root.selectedBy === "MODEL" ? Theme.text : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: root.interactiveTarget && !backend.operationBusy
                        onClicked: root.selectMode("MODEL")
                    }
                }
                Rectangle {
                    objectName: "deviceSelectorChipset"
                    width: parent.width / 2
                    height: parent.height
                    radius: 6
                    color: root.selectedBy === "CHIPSET" ? "#155b92" : "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "CHIPSET"
                        color: root.selectedBy === "CHIPSET" ? Theme.text : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                    MouseArea {
                        anchors.fill: parent
                        enabled: root.interactiveTarget && !backend.operationBusy
                        onClicked: root.selectMode("CHIPSET")
                    }
                }
            }
        }
    }

    Rectangle {
        id: searchFrame
        objectName: "deviceSearchFrame"
        Layout.fillWidth: true
        Layout.preferredHeight: 45
        radius: 7
        color: "#081322"
        border.width: 1
        border.color: searchInput.activeFocus ? "#438cc7" : "#3c5676"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 10
            spacing: 8
            Image {
                source: Qt.resolvedUrl("../../assets/ui-icons/search.svg")
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                fillMode: Image.PreserveAspectFit
            }
            TextField {
                id: searchInput
                objectName: "deviceTargetSearchInput"
                Layout.fillWidth: true
                font.family: Theme.fontFamily
                font.pixelSize: 13
                color: Theme.text
                selectByMouse: true
                enabled: root.interactiveTarget && !backend.operationBusy
                background: Item {}
                placeholderText: root.selectedBy === "MODEL"
                    ? "Search model code/name (or type exact model)"
                    : "Search Kirin / type exact chipset"
                onTextEdited: {
                    root.selectionError = ""
                    root.queryText = text
                    root.showSuggestions()
                }
                onPressed: root.showSuggestions()
                onAccepted: root.commitEntry()
            }
            Text {
                visible: !root.interactiveTarget
                text: root.placeholder
                color: Theme.muted
                Layout.fillWidth: true
                font.family: Theme.fontFamily
                font.pixelSize: 13
            }
            Rectangle {
                objectName: "deviceSearchShowOptions"
                Layout.preferredWidth: 25
                Layout.preferredHeight: 28
                color: "transparent"
                Text {
                    anchors.centerIn: parent
                    text: "\u2304"
                    font.pixelSize: 22
                    color: Theme.text
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: root.interactiveTarget && !backend.operationBusy
                    onClicked: root.showSuggestions()
                }
            }
        }
    }

    Text {
        id: statusLabel
        objectName: "deviceTargetSelectionStatus"
        Layout.fillWidth: true
        text: root.selectionError.length ? root.selectionError :
            root.interactiveTarget
            ? "Target model: " + (backend.firmwareModel || "not selected")
              + "  |  Chipset: " + (backend.firmwareChipset || "detect / select")
            : root.hint
        color: Theme.muted
        font.family: Theme.fontFamily
        font.pixelSize: 11
        elide: Text.ElideRight
    }

    Text {
        objectName: "deviceSelectedServiceLoader"
        Layout.fillWidth: true
        visible: root.interactiveTarget
        text: backend.selectedServiceLoaderLabel
        color: "#85b7ea"
        font.family: Theme.fontFamily
        font.pixelSize: 11
        elide: Text.ElideRight
    }

    ComboBox {
        objectName: "deviceLoaderVariant"
        Layout.fillWidth: true
        Layout.preferredHeight: 30
        visible: root.interactiveTarget && backend.loaderVariantOptions.length > 0
        enabled: !backend.operationBusy
        model: ["Select exact loader variant"].concat(backend.loaderVariantOptions)
        currentIndex: Math.max(0, backend.loaderVariantOptions.indexOf(backend.loaderVariant) + 1)
        onActivated: backend.setLoaderVariant(index === 0 ? "" : backend.loaderVariantOptions[index - 1])
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#243c55"
    }

    Popup {
        id: suggestionPopup
        objectName: "deviceTargetSuggestions"
        parent: Overlay.overlay
        padding: 3
        modal: false
        focus: false
        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
        background: Rectangle {
            radius: 6
            color: "#0b192a"
            border.width: 1
            border.color: "#3b699a"
        }
        contentItem: ListView {
            id: suggestionsList
            objectName: "deviceTargetSuggestionList"
            clip: true
            model: root.filteredResults
            spacing: 1
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Rectangle {
                objectName: "deviceTargetSuggestionRow"
                property var option: modelData
                width: suggestionsList.width
                height: 44
                radius: 4
                color: choiceMouse.containsMouse ? "#1d3c63" : "transparent"
                opacity: option.guide ? 0.78 : 1.0
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    spacing: 3
                    Text {
                        text: option.label
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        width: parent.width
                    }
                    Text {
                        text: option.detail
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        width: parent.width
                    }
                }
                MouseArea {
                    id: choiceMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.selectOption(parent.option)
                }
            }
            Text {
                anchors.centerIn: parent
                visible: root.filteredResults.length === 0
                text: "No catalogue match. Enter the exact model / chipset."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: 12
            }
        }
    }
}

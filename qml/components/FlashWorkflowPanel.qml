import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import ".."

ColumnLayout {
    id: root
    objectName: "flashWorkflowPanel"
    Layout.fillWidth: true
    Layout.fillHeight: true
    spacing: 9

    // This is a configuration editor, NOT a flashing executor.
    // The existing Huawei backend supports only file existence/size preflight.
    property int workflowIndex: 0
    property string pendingRole: ""
    property var packages: ({})
    property var multiFiles: []
    property var partitionSelection: ({})
    property string lastPreflight: ""
    property bool rebootAfter: false
    property bool fastbootToUpgrade: false
    readonly property var workflowNames: [
        "APP firmware · Upgrade / Fastboot",
        "Multiple APP files · Upgrade",
        "APP firmware · Fastboot",
        "Board firmware · XML / Fastboot"
    ]
    readonly property var partitionNames: [
        "SHA256RSA", "CRC", "BASE_VERLIST", "BASE_VER",
        "PACKAGE_TYPE", "HISIUFS_GPT", "XLOADER", "FASTBOOT",
        "DTS", "DTO", "VECTOR", "FW_LPM3",
        "HHEE", "VBMETA", "TEE0S", "RECOVERY",
        "RECOVERY_RAMDISK", "ERECOVERY", "ERECOVERY_RAMDISK",
        "MODEM", "VENDOR", "SYSTEM", "CUST", "PRELOAD"
    ]
    readonly property var sourceRoles: {
        if (workflowIndex === 0)
            return [{role:"upgrade", label:"UPDATE.APP"},
                    {role:"cust", label:"CUST.APP"}]
        if (workflowIndex === 1)
            return [{role:"multi", label:"ADD APP FILES"}]
        if (workflowIndex === 2)
            return [{role:"base", label:"BASE.APP"},
                    {role:"cust", label:"CUST.APP"},
                    {role:"preload", label:"PRELOAD.APP"}]
        return [{role:"xml", label:"BOARD XML"}]
    }
    readonly property int selectedCount: {
        var total=0
        for (var k in partitionSelection)
            if (partitionSelection[k] === true) total++
        return total
    }
    readonly property bool sourceReady: {
        if (workflowIndex === 1) return multiFiles.length > 0
        if (workflowIndex === 2)
            return !!packages.base || !!packages.cust || !!packages.preload
        if (workflowIndex === 3) return !!packages.xml
        return !!packages.upgrade
    }
    signal backRequested()

    function basename(value) {
        var stringValue=String(value || "")
        if (!stringValue.length) return "Not selected"
        return decodeURIComponent(stringValue.split("/").pop())
    }
    function packagePath(role) {
        if (role === "multi") {
            return multiFiles.length ? basename(multiFiles[multiFiles.length-1]) :
                   "No APP files selected"
        }
        return basename(packages[role])
    }
    function requestSource(role) {
        pendingRole=role
        filePicker.nameFilters = role === "xml" ?
            ["Huawei board XML (*.xml)", "All files (*)"] :
            ["Huawei APP firmware (*.app)", "All files (*)"]
        filePicker.fileMode = role === "multi" ?
            FileDialog.OpenFiles : FileDialog.OpenFile
        filePicker.open()
    }
    function storeFile(role, url) {
        var path=String(url || "")
        if (!path.length) return
        if (role === "multi") {
            var list=multiFiles.slice()
            if (list.indexOf(path) === -1) list.push(path)
            multiFiles=list
        } else {
            var entries={}
            for (var key in packages) entries[key]=packages[key]
            entries[role]=path
            packages=entries
        }
        lastPreflight=""
    }
    function clearSelection() {
        partitionSelection={}
        if (workflowIndex === 1) {
            multiFiles=[]
        } else {
            var remaining={}
            for (var role in packages) {
                if (workflowIndex === 0 && (role === "upgrade" || role === "cust"))
                    continue
                if (workflowIndex === 2 &&
                    (role === "base" || role === "cust" || role === "preload"))
                    continue
                if (workflowIndex === 3 && role === "xml")
                    continue
                remaining[role]=packages[role]
            }
            packages=remaining
        }
        lastPreflight=""
    }
    function flipPartitions() {
        var updated={}
        for (var i=0;i<partitionNames.length;i++) {
            var name=partitionNames[i]
            updated[name]=partitionSelection[name] !== true
        }
        partitionSelection=updated
    }
    function togglePartition(name, enabled) {
        var updated={}
        for (var k in partitionSelection) updated[k]=partitionSelection[k]
        updated[name]=enabled
        partitionSelection=updated
    }
    function firstSource() {
        if (workflowIndex === 0) return String(packages.upgrade || "")
        if (workflowIndex === 1) return multiFiles.length ?
                                       String(multiFiles[0]) : ""
        if (workflowIndex === 2) return String(packages.base ||
                                                packages.cust ||
                                                packages.preload || "")
        return String(packages.xml || "")
    }
    function preflightPrimaryFile() {
        var source=firstSource()
        if (!source.length) {
            lastPreflight="No package selected."
            return
        }
        if (typeof backend.setFirmwarePath !== "function" ||
            typeof backend.runAction !== "function") {
            lastPreflight="Package preflight backend is not connected."
            return
        }
        backend.setFirmwarePath(source)
        var response=backend.runAction("flash_firmware")
        lastPreflight=response === undefined || response === null ?
                      "Preflight requested. Consult the live operation log." :
                      String(response)
    }

    FileDialog {
        id: filePicker
        title: root.pendingRole === "xml" ?
               "Select Huawei board XML" : "Select Huawei APP firmware"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Huawei APP firmware (*.app)", "All files (*)"]
        onAccepted: {
            if (root.pendingRole === "multi") {
                for (var i=0;i<selectedFiles.length;i++)
                    root.storeFile("multi",selectedFiles[i].toString())
            } else {
                root.storeFile(root.pendingRole,selectedFile.toString())
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        Text {
            text: "FLASH WORKFLOW"
            font.family: Theme.fontFamily
            font.weight: Font.DemiBold
            font.pixelSize: 15
            color: Theme.text
        }
        ComboBox {
            id: workflowPicker
            objectName: "flashWorkflowModePicker"
            Layout.fillWidth: true
            Layout.preferredHeight: 38
            model: root.workflowNames
            currentIndex: root.workflowIndex
            onActivated: function(index) {
                root.workflowIndex=index
                root.lastPreflight=""
                if (typeof backend.setFirmwareMode === "function") {
                    var mode=index === 3 ? "Board Firmware" :
                             index === 2 ? "Full Flash" : "Upgrade"
                    backend.setFirmwareMode(mode)
                }
            }
        }
        Button {
            objectName: "flashWorkflowBack"
            text: "OVERVIEW"
            Layout.preferredWidth: 100
            Layout.preferredHeight: 38
            onClicked: root.backRequested()
        }
    }
    Text {
        Layout.fillWidth: true
        text: "Choose the exact source and mode. The selected package must be verified by the backend before any write."
        font.family: Theme.fontFamily
        font.pixelSize: 12
        color: Theme.muted
        wrapMode: Text.WordWrap
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: 12

        GlassPanel {
            Layout.preferredWidth: 282
            Layout.fillHeight: true
            panelOpacity: 0.66
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Text {
                    text: root.workflowIndex === 3 ? "XML SOURCE" : "APP SOURCES"
                    color: Theme.cyan
                    font.family: Theme.fontFamily
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                }
                Repeater {
                    model: root.sourceRoles
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 5
                        Button {
                            objectName: "flashSource_" + modelData.role
                            text: modelData.label
                            Layout.preferredWidth: 126
                            Layout.preferredHeight: 32
                            onClicked: root.requestSource(modelData.role)
                        }
                        Text {
                            Layout.fillWidth: true
                            font.family: Theme.fontFamily
                            font.pixelSize: 11
                            color: Theme.muted
                            elide: Text.ElideMiddle
                            text: root.packagePath(modelData.role)
                        }
                    }
                }
                Text {
                    visible: root.workflowIndex === 1
                    text: root.multiFiles.length + " distinct APP file(s) selected"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.cyan
                }
                ScrollView {
                    visible: root.workflowIndex === 1
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    Column {
                        width: 245
                        spacing: 3
                        Repeater {
                            model: root.multiFiles
                            Text {
                                width: 235
                                text: root.basename(modelData)
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                color: Theme.text
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true; visible: root.workflowIndex !== 1 }
                Text {
                    Layout.fillWidth: true
                    text: root.workflowIndex === 0 ?
                          "Upgrade mode uses UPDATE.APP and optional CUST.APP." :
                          root.workflowIndex === 1 ?
                          "Add several APP files for an Upgrade Mode job." :
                          root.workflowIndex === 2 ?
                          "Fastboot mode accepts BASE, CUST and PRELOAD APP sources." :
                          "Board flashing requires a model-matched XML manifest."
                    color: Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
            }
        }
        GlassPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            panelOpacity: 0.66
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6
                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: root.workflowIndex === 1 ?
                              "APP FILE QUEUE" : "PARTITION TEMPLATE"
                        color: Theme.cyan
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                    }
                    Button {
                        objectName: "flashInvertSelection"
                        visible: root.workflowIndex >= 2
                        text: "INVERT"
                        Layout.preferredWidth: 77
                        Layout.preferredHeight: 28
                        onClicked: root.flipPartitions()
                    }
                    Button {
                        objectName: "flashClearSelection"
                        text: "CLEAR"
                        Layout.preferredWidth: 66
                        Layout.preferredHeight: 28
                        onClicked: root.clearSelection()
                    }
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: root.workflowIndex >= 2 ?
                          "Reference names only — no APP/XML partition inventory has been parsed." :
                          "The backend must verify the exact package and device before execution."
                    color: Theme.amber
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.workflowIndex >= 2
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    GridLayout {
                        width: 415
                        columns: 3
                        rowSpacing: 0
                        columnSpacing: 1
                        Repeater {
                            model: root.partitionNames
                            CheckBox {
                                objectName: "flashPartition_" + modelData
                                text: modelData
                                font.family: Theme.fontFamily
                                font.pixelSize: 10
                                Layout.preferredWidth: 136
                                Layout.preferredHeight: 29
                                checked: root.partitionSelection[modelData] === true
                                onToggled: root.togglePartition(modelData,checked)
                            }
                        }
                    }
                }
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.workflowIndex < 2
                    Column {
                        anchors.centerIn: parent
                        width: parent.width - 20
                        spacing: 8
                        Text {
                            width: parent.width
                            text: root.workflowIndex === 1 ?
                                  "Files can be added repeatedly and cleared before submission." :
                                  "UPDATE.APP package layout is not yet available from the backend."
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
                Text {
                    visible: root.workflowIndex >= 2
                    text: root.selectedCount + " reference partition(s) selected"
                    font.family: Theme.fontFamily
                    font.pixelSize: 11
                    color: Theme.muted
                }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        CheckBox {
            objectName: "flashRebootAfter"
            text: "Reboot on finish"
            checked: root.rebootAfter
            onToggled: root.rebootAfter=checked
            font.family: Theme.fontFamily
            font.pixelSize: 11
        }
        CheckBox {
            objectName: "flashFastbootToUpgrade"
            visible: root.workflowIndex === 0
            text: "Fastboot to upgrade"
            checked: root.fastbootToUpgrade
            onToggled: root.fastbootToUpgrade=checked
            font.family: Theme.fontFamily
            font.pixelSize: 11
        }
        Item { Layout.fillWidth: true }
        Text {
            text: "PLAN ONLY — NO DEVICE WRITES"
            font.family: Theme.fontFamily
            font.pixelSize: 11
            color: Theme.amber
        }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        Button {
            id: verifyButton
            objectName: "flashPreflightButton"
            text: "CHECK PRIMARY FILE"
            Layout.preferredWidth: 210
            Layout.preferredHeight: 40
            enabled: root.sourceReady
            onClicked: root.preflightPrimaryFile()
        }
        GlowButton {
            id: startButton
            objectName: "flashExecuteButton"
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            text: "START FLASH — BACKEND NOT CONNECTED"
            enabled: false
            // Execution is deliberately absent until a dedicated plan API
            // verifies full package inventory and authorizes every write.
        }
    }
    Text {
        Layout.fillWidth: true
        visible: root.lastPreflight.length > 0
        text: root.lastPreflight
        font.family: Theme.fontFamily
        font.pixelSize: 11
        color: Theme.cyan
        wrapMode: Text.WordWrap
    }
}

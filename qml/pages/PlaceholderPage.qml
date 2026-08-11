import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    property string title: "PAGE"
    // Kept only for Main.qml compatibility; no placeholder copy is rendered.
    property string message: ""

    Loader {
        anchors.fill: parent
        sourceComponent: root.title === "DEVICE INFORMATION" ? deviceInformationComponent
                         : root.title === "PARTITION MANAGER" ? partitionManagerComponent
                         : root.title === "BACKUP & RESTORE" ? backupRestoreComponent
                         : operationHistoryComponent
    }

    Component { id: deviceInformationComponent; DeviceInformationPage {} }
    Component { id: partitionManagerComponent; PartitionManagerPage {} }
    Component { id: backupRestoreComponent; BackupRestorePage {} }
    Component { id: operationHistoryComponent; OperationHistoryPage {} }
}

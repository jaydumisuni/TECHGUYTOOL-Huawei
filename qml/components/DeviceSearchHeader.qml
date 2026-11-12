import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root
    objectName: "sharedDeviceSearchHeader"
    property string pageTitle: ""
    property string placeholder: "Search Model..."
    property string hint: "Switch to Chipset to browse platform families"
    Layout.fillWidth: true
    spacing: 8

    RowLayout {
        Layout.fillWidth: true
        Text {
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
            width: 200; height: 34; radius: 6
            color: "#0b1727"; border.width: 1; border.color: "#3b5270"
            Row {
                anchors.fill: parent
                Rectangle {
                    width: 100; height: 34; radius: 6
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "#5a33ad" }
                        GradientStop { position: 1; color: "#10598f" }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "MODEL"
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                }
                Rectangle {
                    width: 100; height: 34; color: "transparent"
                    Text {
                        anchors.centerIn: parent
                        text: "CHIPSET"
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 45
        radius: 7
        color: "#081322"
        border.width: 1
        border.color: "#3c5676"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            Image {
                source: Qt.resolvedUrl("../../assets/ui-icons/search.svg")
                Layout.preferredWidth: 23
                Layout.preferredHeight: 23
                fillMode: Image.PreserveAspectFit
            }
            Text {
                text: root.placeholder
                color: "#8798ad"
                font.family: Theme.fontFamily
                font.pixelSize: 14
                Layout.fillWidth: true
            }
            Text { text: "⌄"; color: Theme.text; font.pixelSize: 18 }
        }
    }
    Text {
        text: root.hint
        color: Theme.muted
        font.family: Theme.fontFamily
        font.pixelSize: 12
    }
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#243c55"
    }
}

import QtQuick 2.15
import ".."

Row {
    id: root
    property int number: 1
    property string text: "SECTION"
    spacing: 10
    Rectangle {
        width: 20; height: 20; radius: 10
        color: "#203b5a"
        Text { anchors.centerIn: parent; text: root.number; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 12 }
    }
    Text { text: root.text; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: 14; font.weight: Font.Medium; letterSpacing: 0.7; anchors.verticalCenter: parent.verticalCenter }
}

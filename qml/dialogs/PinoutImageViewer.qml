import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Window {
    id: root
    objectName: "pinoutImageViewer"
    title: imageTitle.length ? "PINOUT IMAGE - " + imageTitle : "PINOUT IMAGE"
    visible: false
    color: Theme.background
    flags: Qt.Window
    width: Math.max(450, Math.min(1160, Screen.desktopAvailableWidth - 60))
    height: Math.max(380, Math.min(820, Screen.desktopAvailableHeight - 70))
    minimumWidth: 450
    minimumHeight: 380
    x: Screen.virtualX + Math.round((Screen.desktopAvailableWidth - width) / 2)
    y: Screen.virtualY + Math.round((Screen.desktopAvailableHeight - height) / 2)

    property string imageSource: ""
    property string imageTitle: ""
    property real zoomFactor: 1.0
    property real panX: 0
    property real panY: 0
    readonly property bool imageReady: pinoutImage.status === Image.Ready
    readonly property real naturalWidth: Math.max(1, pinoutImage.implicitWidth)
    readonly property real naturalHeight: Math.max(1, pinoutImage.implicitHeight)
    readonly property real fitScale: Math.min(viewport.width / naturalWidth,
                                             viewport.height / naturalHeight)
    readonly property real imageScale: fitScale * zoomFactor

    function openImage(sourceUrl, name) {
        if (!/^(file:\/\/|qrc:|image:\/\/)/.test(String(sourceUrl || "")))
            return
        imageSource = String(sourceUrl)
        imageTitle = String(name || "Pinout")
        fitImage()
        show()
        requestActivate()
    }
    function fitImage() {
        zoomFactor = 1
        panX = 0
        panY = 0
    }
    function zoomBy(factor) {
        zoomFactor = Math.max(0.25, Math.min(16, zoomFactor * factor))
        constrainPan()
    }
    function actualPixels() {
        zoomFactor = Math.max(0.25, Math.min(16, 1 / Math.max(0.001, fitScale)))
        constrainPan()
    }
    function constrainPan() {
        var excessX = Math.max(0, (pinoutImage.width - viewport.width) / 2)
        var excessY = Math.max(0, (pinoutImage.height - viewport.height) / 2)
        panX = Math.max(-excessX, Math.min(excessX, panX))
        panY = Math.max(-excessY, Math.min(excessY, panY))
    }

    Rectangle {
        anchors.fill: parent
        color: "#07121f"
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 9
            Text {
                text: root.imageTitle
                font.family: Theme.fontFamily
                font.pixelSize: 17
                font.weight: Font.DemiBold
                color: Theme.text
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Button {
                objectName: "pinoutViewerZoomOut"
                text: "-"
                Layout.preferredWidth: 40
                onClicked: root.zoomBy(1 / 1.25)
            }
            Text {
                text: Math.round(root.imageScale * 100) + "%"
                color: Theme.cyan
                font.family: Theme.fontFamily
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
                Layout.preferredWidth: 60
            }
            Button {
                objectName: "pinoutViewerZoomIn"
                text: "+"
                Layout.preferredWidth: 40
                onClicked: root.zoomBy(1.25)
            }
            Button {
                objectName: "pinoutViewerActualPixels"
                text: "100%"
                Layout.preferredWidth: 65
                onClicked: root.actualPixels()
            }
            Button {
                objectName: "pinoutViewerFit"
                text: "FIT"
                Layout.preferredWidth: 60
                onClicked: root.fitImage()
            }
            Button {
                objectName: "pinoutViewerMaximize"
                text: root.visibility === Window.Maximized ? "RESTORE" : "MAXIMIZE"
                Layout.preferredWidth: 90
                onClicked: root.visibility === Window.Maximized ?
                           root.showNormal() : root.showMaximized()
            }
            Button {
                objectName: "pinoutViewerClose"
                text: "CLOSE"
                Layout.preferredWidth: 70
                onClicked: root.close()
            }
        }

        Rectangle {
            id: viewport
            objectName: "pinoutImageViewport"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            radius: 8
            color: "#05101a"
            border.color: "#36546d"
            border.width: 1

            Image {
                id: pinoutImage
                objectName: "pinoutZoomImage"
                source: root.imageSource
                asynchronous: true
                cache: true
                smooth: true
                mipmap: true
                fillMode: Image.Stretch
                width: Math.max(1, root.naturalWidth * root.imageScale)
                height: Math.max(1, root.naturalHeight * root.imageScale)
                x: (viewport.width - width) / 2 + root.panX
                y: (viewport.height - height) / 2 + root.panY
                onStatusChanged: if (status === Image.Ready) root.fitImage()
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: root.imageScale > root.fitScale ? Qt.OpenHandCursor : Qt.ArrowCursor
                property real startX: 0
                property real startY: 0
                onPressed: function(mouse) {
                    startX = mouse.x
                    startY = mouse.y
                }
                onPositionChanged: function(mouse) {
                    if ((mouse.buttons & Qt.LeftButton) === 0) return
                    root.panX += mouse.x - startX
                    root.panY += mouse.y - startY
                    startX = mouse.x
                    startY = mouse.y
                    root.constrainPan()
                }
                onWheel: function(wheel) {
                    root.zoomBy(wheel.angleDelta.y > 0 ? 1.2 : 1 / 1.2)
                    wheel.accepted = true
                }
            }
            Text {
                anchors.centerIn: parent
                visible: pinoutImage.status === Image.Loading
                text: "Loading verified pinout image..."
                color: Theme.muted
                font.family: Theme.fontFamily
            }
            Text {
                anchors.centerIn: parent
                visible: pinoutImage.status === Image.Error
                text: "Image could not be displayed."
                color: "#ef9aa7"
                font.family: Theme.fontFamily
            }
        }
        Text {
            Layout.fillWidth: true
            text: "Mouse wheel to zoom  |  Drag to pan  |  FIT resets the view"
            font.family: Theme.fontFamily
            color: Theme.muted
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
        }
    }
}

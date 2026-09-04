import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

TextArea {
    id: root
    property string rawText: ""

    function escaped(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
    }

    function formatLine(value) {
        var line = escaped(value)
        line = line.replace(/^(\[[0-9]{2}:[0-9]{2}:[0-9]{2}\])/, '<font color="#16c7ef">$1</font>')
        line = line.replace(/\[(INFO|READY|USB|DEVICE)\]/g, '<font color="#55bfff">[$1]</font>')
        line = line.replace(/\[(WARN|GUARD)\]/g, '<font color="#ffc66d">[$1]</font>')
        line = line.replace(/\[(ERROR|FAIL|FAILED)\]/g, '<font color="#ff6477">[$1]</font>')
        line = line.replace(/\b(OK|PASS|READY)\b/g, '<font color="#4fe06a">$1</font>')
        line = line.replace(/(latest version|connected|installed)/gi, '<font color="#4fe06a">$1</font>')
        return line
    }

    function formatted(value) {
        var lines = String(value || "").split("\n")
        var result = []
        for (var i = 0; i < lines.length; ++i)
            result.push(formatLine(lines[i]))
        return result.join("<br>")
    }

    text: formatted(rawText)
    textFormat: TextEdit.RichText
    readOnly: true
    wrapMode: TextEdit.Wrap
    color: "#aab8c7"
    selectionColor: "#245782"
    selectedTextColor: Theme.text
    font.family: "Consolas"
    font.pixelSize: 12
    background: Rectangle { color: "transparent" }
}

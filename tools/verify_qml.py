from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML_ROOT = ROOT / "qml"


@dataclass(frozen=True)
class Finding:
    path: Path
    message: str


def strip_strings_and_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if quote:
            if char == "\\":
                out.extend("  ")
                i += 2
                continue
            if char == quote:
                quote = None
            out.append(" ")
            i += 1
            continue
        if char in {'"', "'"}:
            quote = char
            out.append(" ")
            i += 1
            continue
        if char == "/" and nxt == "/":
            while i < len(text) and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if char == "/" and nxt == "*":
            out.extend("  ")
            i += 2
            while i + 1 < len(text) and text[i : i + 2] != "*/":
                out.append("\n" if text[i] == "\n" else " ")
                i += 1
            out.extend("  ")
            i += 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def balance_findings(path: Path, text: str) -> list[Finding]:
    clean = strip_strings_and_comments(text)
    pairs = {"}": "{", "]": "[", ")": "("}
    stack: list[tuple[str, int]] = []
    findings: list[Finding] = []
    line = 1
    for char in clean:
        if char == "\n":
            line += 1
        elif char in "{[(":
            stack.append((char, line))
        elif char in "}])":
            if not stack or stack[-1][0] != pairs[char]:
                findings.append(Finding(path, f"unmatched {char!r} at line {line}"))
            else:
                stack.pop()
    for char, opened in stack:
        findings.append(Finding(path, f"unclosed {char!r} opened at line {opened}"))
    return findings


def verify() -> list[Finding]:
    findings: list[Finding] = []
    qml_files = sorted(QML_ROOT.rglob("*.qml"))
    if not qml_files:
        return [Finding(QML_ROOT, "no QML files found")]

    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    for path in qml_files:
        text = path.read_text(encoding="utf-8")
        findings.extend(balance_findings(path, text))
        if "import QtQuick" not in text:
            findings.append(Finding(path, "missing QtQuick import"))
        relative = path.relative_to(ROOT).as_posix()
        if f'alias="{relative}"' not in qrc:
            findings.append(Finding(path, "missing from resources.qrc"))
        if re.search(r"(?:source|icon\.source):\s*[\"'](?:[A-Za-z]:\\|/home/|/mnt/)", text):
            findings.append(Finding(path, "contains an absolute asset path"))
        if re.search(r"\bRow\s*\{[^{}]{0,500}\b(?:leftPadding|rightPadding|topPadding|bottomPadding)\s*:", text, re.S):
            findings.append(Finding(path, "Row positioner uses unsupported padding property"))
        for source in re.findall(r'\bsource:\s*"([^":]+\.(?:png|ico|jpg|jpeg|svg))"', text, re.I):
            resolved = (path.parent / source).resolve()
            if not resolved.is_file():
                findings.append(Finding(path, f"missing image source: {source}"))

    main = QML_ROOT / "Main.qml"
    if main not in qml_files:
        findings.append(Finding(main, "main QML entry point is missing"))
    else:
        text = main.read_text(encoding="utf-8")
        for required in ("SettingsMenu", "RegisterDialog", "DriverDialog", "AboutDialog", "TerminalDialog"):
            if required not in text:
                findings.append(Finding(main, f"missing required popup: {required}"))
    return findings


def main() -> int:
    findings = verify()
    if findings:
        for finding in findings:
            print(f"FAIL {finding.path.relative_to(ROOT)}: {finding.message}")
        return 1
    print(f"PASS QML contract: {len(list(QML_ROOT.rglob('*.qml')))} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

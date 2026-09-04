from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    relative
    for folder in (ROOT / "qml", ROOT / "assets")
    for relative in sorted(
        path.relative_to(ROOT).as_posix()
        for path in folder.rglob("*")
        if path.is_file()
    )
]
content = ["<RCC>", '  <qresource prefix="/">']
content.extend(f'    <file alias="{path}">{path}</file>' for path in FILES)
content.extend(["  </qresource>", "</RCC>", ""])
(ROOT / "resources.qrc").write_text("\n".join(content), encoding="utf-8")
print(f"resources.qrc: {len(FILES)} files")

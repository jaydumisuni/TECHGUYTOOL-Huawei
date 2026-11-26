from __future__ import annotations

"""Built-in filesystem navigation for Huawei's ADB/Fastboot terminal.

No host shell is started and no arbitrary program is executed. The returned
working directory belongs to the terminal session, never to os.chdir().
"""

from pathlib import Path
import os
import re

MAX_DIRECTORY_LIST = 120


def _path_argument(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValueError("Enter a directory path.")
    if value.startswith('"') or value.endswith('"'):
        if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
            raise ValueError('Use matching double quotes around paths with spaces.')
        value = value[1:-1]
    if not value or any(char in value for char in "\r\n\x00"):
        raise ValueError("Invalid directory path.")
    return value


def resolve_directory(current: Path, argument: str) -> Path:
    value = _path_argument(argument)
    if value == "~":
        value = str(Path.home())
    elif value.startswith("~/") or value.startswith("~\\"):
        value = str(Path.home() / value[2:])
    value = os.path.expandvars(value)
    if os.name == "nt":
        if re.fullmatch(r"[A-Za-z]:", value):
            value += "\\"
        elif re.match(r"^[A-Za-z]:[^\\/]", value):
            raise ValueError("Use a full drive path, for example D:\\firmware.")
    requested = Path(value)
    if not requested.is_absolute():
        requested = current / requested
    try:
        resolved = requested.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"Directory does not exist: {value}") from exc
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {value}")
    return resolved


def try_directory_command(line: str, current: Path) -> tuple[Path, str] | None:
    """Return new cwd and display response; None means ADB/Fastboot command."""
    text = line.strip()
    if not text:
        return None
    if any(c in text for c in "\r\n\x00"):
        raise ValueError("Only one terminal command is accepted per line.")
    word, _, remainder = text.partition(" ")
    cmd = word.casefold()
    if cmd in ("cd..", "cd."):
        cmd, remainder = "cd", ".." if cmd == "cd.." else "."
    elif os.name == "nt" and re.fullmatch(r"[A-Za-z]:", word):
        cmd, remainder = "cd", word
    if cmd not in ("cd", "pwd", "dir", "ls"):
        return None

    if cmd == "pwd":
        if remainder.strip():
            raise ValueError("pwd does not accept arguments.")
        return current, str(current)

    if cmd == "cd":
        target = remainder.strip()
        if target.casefold() == "/d":
            raise ValueError("Use cd /d followed by a directory.")
        if target[:3].casefold() == "/d ":
            target = target[3:].strip()
        if not target:
            return current, str(current)
        next_dir = resolve_directory(current, target)
        return next_dir, str(next_dir)

    target = resolve_directory(current, remainder) if remainder.strip() else current
    try:
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
    except (OSError, PermissionError) as exc:
        raise ValueError(f"Cannot list directory: {target}") from exc
    lines = [str(target)]
    for entry in entries[:MAX_DIRECTORY_LIST]:
        try:
            label = "<DIR>" if entry.is_dir() else f"{entry.stat().st_size:>10}"
        except OSError:
            label = "       ???"
        lines.append(f"{label}  {entry.name}")
    if len(entries) > MAX_DIRECTORY_LIST:
        lines.append(f"... {len(entries) - MAX_DIRECTORY_LIST} more entries (first {MAX_DIRECTORY_LIST} shown).")
    elif len(entries) == 0:
        lines.append("(empty)")
    return current, "\n".join(lines)

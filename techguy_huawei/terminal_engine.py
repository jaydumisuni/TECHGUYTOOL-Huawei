from __future__ import annotations

"""ADB/Fastboot console transport. Never execute host shell commands.

Read operations run immediately. State-changing commands require an exact
one-shot approval from the UI backend, bound to the command and live device.
No firmware, mode transition, wipe or reboot is initiated automatically.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import re
import shlex

from .action_health import ActionState
from .device_engine import DeviceEngine, EngineResult
from .evidence import EvidenceJournal


MAX_COMMAND_LENGTH = 8192
SERIAL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
HOST_ONLY_ADB = frozenset(
    {"devices", "version", "--version", "help", "start-server", "kill-server"}
)
HOST_ONLY_FASTBOOT = frozenset({"devices", "version", "--version", "help", "--help"})


@dataclass(frozen=True)
class TerminalCommand:
    tool: str
    arguments: tuple[str, ...]
    requires_confirmation: bool
    fingerprint: str
    serial: str = ""

    @property
    def requires_device(self) -> bool:
        head = self.arguments[2:] if self.serial else self.arguments
        if not head:
            return False
        if self.tool == "adb":
            return head[0] not in HOST_ONLY_ADB
        return head[0] not in HOST_ONLY_FASTBOOT


def _read_only(tool: str, args: tuple[str, ...]) -> bool:
    args = args[2:] if len(args) >= 3 and args[0] == "-s" else args
    if tool == "fastboot":
        return (
            args in (
                ("devices",), ("devices", "-l"), ("--version",),
                ("version",), ("help",), ("--help",),
                ("oem", "get-bootinfo"), ("oem", "get-build-number"),
            )
            or (len(args) == 2 and args[0] == "getvar")
        )
    return (
        args in (
            ("devices",), ("devices", "-l"), ("version",), ("--version",),
            ("help",), ("get-state",), ("get-serialno",),
        )
        or (len(args) == 3 and args[:2] == ("shell", "getprop")
            and args[2].startswith("ro."))
        or args == ("shell", "getprop")
    )


def parse_console(line: str) -> TerminalCommand:
    if not line or len(line) > MAX_COMMAND_LENGTH or any(c in line for c in "\r\n\x00"):
        raise ValueError("Enter one ADB or Fastboot command on a single line.")
    try:
        # On Windows posix=False preserves backslashes in local flash paths.
        words = shlex.split(line, posix=os.name != "nt")
    except ValueError as exc:
        raise ValueError("Invalid command quoting.") from exc
    if os.name == "nt":
        words = [w[1:-1] if len(w) > 1 and w[0] == w[-1] == '"' else w for w in words]
    if len(words) < 2 or words[0].lower() not in {"adb", "adb.exe", "fastboot", "fastboot.exe"}:
        raise ValueError("Terminal commands must start with adb or fastboot.")
    tool = words[0].lower().removesuffix(".exe")
    args = tuple(words[1:])
    if not all(args) or any("\x00" in arg for arg in args):
        raise ValueError("Invalid empty command argument.")
    serial = ""
    if args and args[0] == "-s":
        if len(args) < 3 or not SERIAL_PATTERN.fullmatch(args[1]):
            raise ValueError("Use -s followed by one valid device serial and a command.")
        serial = args[1]
    digest = sha256(json.dumps([tool, *args], ensure_ascii=False).encode("utf-8")).hexdigest()
    return TerminalCommand(
        tool=tool,
        arguments=args,
        requires_confirmation=not _read_only(tool, args),
        fingerprint=digest,
        serial=serial,
    )


def terminal_context_fingerprint(command: TerminalCommand, working_directory: Path | None) -> str:
    """Bind a confirmed device command to the exact filesystem directory.

    Preserve the old fingerprint for callers without a directory context.
    """
    if working_directory is None:
        return command.fingerprint
    resolved = str(Path(working_directory).resolve())
    return sha256(json.dumps([command.fingerprint, resolved], ensure_ascii=False).encode("utf-8")).hexdigest()


def _target_for_write(
    engine: DeviceEngine,
    command: TerminalCommand,
    expected_serial: str,
) -> tuple[str | None, EngineResult | None]:
    binary = engine._tool(command.tool)
    if not binary:
        return None, EngineResult(
            False, f"{command.tool}.exe missing from runtime/platform-tools.",
            ActionState.MISSING_DEPENDENCY,
        )
    # The target is checked again immediately before the irreversible command.
    try:
        discovery, _ = engine._run(
            "huawei_terminal_target_check", [binary, "devices"],
            timeout=15,
        )
    except Exception as exc:
        return None, EngineResult(
            False, f"Device presence check failed: {type(exc).__name__}.",
            ActionState.FAILED,
        )
    if discovery.returncode:
        return None, EngineResult(
            False, "Device enumeration failed; write was not executed.", ActionState.GUARDED
        )
    if command.tool == "fastboot":
        present = {row.split()[0] for row in DeviceEngine._fastboot_rows(discovery.stdout)}
    else:
        present = {
            row.split()[0] for row in DeviceEngine._adb_rows(discovery.stdout)
            if len(row.split()) >= 2 and row.split()[1] == "device"
        }

    if command.serial:
        serial = command.serial
        if serial not in present:
            return None, EngineResult(
                False, "Requested target device is not connected; no write executed.",
                ActionState.GUARDED,
            )
    elif len(present) == 1:
        serial = next(iter(present))
    else:
        return None, EngineResult(
            False, "A write requires exactly one connected device or an explicit -s serial.",
            ActionState.GUARDED,
        )
    if expected_serial and serial != expected_serial:
        return None, EngineResult(
            False, "Target changed since the UI selected the device; write cancelled.",
            ActionState.GUARDED,
        )
    return serial, None


def execute_console(
    app_root: Path,
    evidence_journal: Path,
    line: str,
    *,
    approved: bool = False,
    command_fingerprint: str = "",
    expected_serial: str = "",
    working_directory: Path | None = None,
) -> EngineResult:
    try:
        command = parse_console(line)
    except ValueError as exc:
        return EngineResult(False, str(exc), ActionState.GUARDED)
    active_directory: Path | None = None
    if working_directory is not None:
        try:
            active_directory = Path(working_directory).resolve(strict=True)
            if not active_directory.is_dir():
                raise ValueError("Not a directory")
        except (OSError, RuntimeError, ValueError):
            return EngineResult(
                False, "Terminal working directory is no longer available; no command executed.",
                ActionState.GUARDED,
            )
    required_fingerprint = terminal_context_fingerprint(command, active_directory)
    if command.requires_confirmation and (
        not approved or command_fingerprint != required_fingerprint
    ):
        return EngineResult(
            False,
            "Explicit confirmation is required for this device-state or write command. "
            "No command has been executed.",
            ActionState.GUARDED,
            {
                "confirmation_required": True,
                "fingerprint": command.fingerprint,
                "tool": command.tool,
                "arguments": list(command.arguments),
            },
        )
    engine = DeviceEngine(app_root, EvidenceJournal(evidence_journal))
    # Only terminal invocations inherit this session directory. Other service
    # operations continue to use their own immutable project-root context.
    engine.terminal_working_directory = active_directory
    binary = engine._tool(command.tool)
    if not binary:
        return EngineResult(
            False, f"{command.tool}.exe missing from runtime/platform-tools.",
            ActionState.MISSING_DEPENDENCY,
        )
    args = list(command.arguments)
    if command.requires_confirmation and command.requires_device:
        serial, failure = _target_for_write(engine, command, expected_serial)
        if failure is not None:
            return failure
        if not command.serial:
            args = ["-s", serial, *args]

    try:
        # Write commands are not terminated by an artificial timeout mid-flash.
        # They run in the service worker and never in the Qt GUI thread.
        response, _ = engine._run(
            "huawei_terminal_write" if command.requires_confirmation else "huawei_terminal_read",
            [binary, *args],
            timeout=None if command.requires_confirmation else 45,
        )
    except Exception as exc:
        return EngineResult(
            False, f"{command.tool} execution failed: {type(exc).__name__}: {exc}",
            ActionState.FAILED,
        )
    output = (
        response.stdout + ("\n" if response.stdout and response.stderr else "")
        + response.stderr
    ).strip()
    if response.returncode:
        return EngineResult(
            False,
            f"{command.tool} exited with code {response.returncode}:\n{output[:12000]}",
            ActionState.FAILED,
        )
    return EngineResult(
        True,
        output[:12000] or "Command completed successfully; no output returned.",
        ActionState.READY,
        {
            "command_fingerprint": required_fingerprint,
            "working_directory": str(active_directory) if active_directory is not None else "",
            "read_only": not command.requires_confirmation,
        },
    )

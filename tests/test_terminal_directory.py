"""Source and process-level proof for stateful Huawei terminal directories."""
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace

import pytest

from techguy_huawei.action_health import ActionState
from techguy_huawei.device_engine import DeviceEngine
from techguy_huawei.evidence import EvidenceJournal
from techguy_huawei.terminal_directory import resolve_directory, try_directory_command
from techguy_huawei.terminal_engine import (
    execute_console, parse_console, terminal_context_fingerprint,
)


def test_cd_and_pwd_keep_session_cwd_without_changing_process(tmp_path, monkeypatch):
    import os
    first = tmp_path / "My Firmware" / "build A"
    first.mkdir(parents=True)
    (first / "system.img").write_bytes(b"fixture")
    before = Path.cwd()
    new, out = try_directory_command('cd "My Firmware\\build A"', tmp_path)
    assert new == first.resolve() and out == str(first)
    assert try_directory_command("pwd", new) == (new, str(new))
    new2, _ = try_directory_command("cd ..", new)
    assert new2 == first.parent
    assert try_directory_command("cd.", new2)[0] == new2
    assert try_directory_command("cd..", new)[0] == new.parent
    assert Path.cwd() == before


def test_ls_dir_and_directory_with_space(tmp_path):
    target = tmp_path / "firmware files"
    target.mkdir()
    (target / "system image.img").write_bytes(b"test-data")
    (target / "subfolder").mkdir()
    new, listing = try_directory_command('dir "firmware files"', tmp_path)
    assert new == tmp_path
    assert "system image.img" in listing
    assert "<DIR>  subfolder" in listing
    new, listing = try_directory_command("ls", target)
    assert "system image.img" in listing and new == target


def test_no_shell_or_nonexistent_directory(tmp_path):
    original = Path.cwd()
    assert try_directory_command("adb devices", tmp_path) is None
    assert try_directory_command("fastboot --version", tmp_path) is None
    for line in ("cd does-not-exist", "cd /d", 'cd "broken', "pwd extra", "dir nonexistent", "cd\nfastboot erase userdata"):
        with pytest.raises(ValueError):
            try_directory_command(line, tmp_path)
    assert Path.cwd() == original


def test_write_approval_cannot_be_replayed_from_other_directory(tmp_path, monkeypatch):
    a = tmp_path / "romA"
    b = tmp_path / "romB"
    a.mkdir()
    b.mkdir()
    line = "fastboot flash system system.img"
    command = parse_console(line)
    permit = terminal_context_fingerprint(command, a)
    assert permit != terminal_context_fingerprint(command, b)
    assert terminal_context_fingerprint(command, None) == command.fingerprint
    monkeypatch.setattr(DeviceEngine, "_run", lambda *_a, **_k: pytest.fail("No device process allowed"))
    result = execute_console(tmp_path, tmp_path / "journal.jsonl", line,
                             approved=True, command_fingerprint=permit,
                             working_directory=b)
    assert result.health_state is ActionState.GUARDED
    assert result.payload["confirmation_required"] is True


def test_missing_folder_cannot_dispatch_command(tmp_path, monkeypatch):
    nonexistent = tmp_path / "gone"
    monkeypatch.setattr(DeviceEngine, "_run", lambda *_a, **_k: pytest.fail("No device process allowed"))
    result = execute_console(tmp_path, tmp_path / "journal.jsonl", "fastboot devices",
                             working_directory=nonexistent)
    assert not result.ok
    assert result.health_state is ActionState.GUARDED
    assert "no command executed" in result.message.lower()


def test_actual_subprocess_receives_cwd_without_host_shell(tmp_path, monkeypatch):
    import techguy_huawei.device_engine as module
    journal = EvidenceJournal(tmp_path / "evidence.jsonl")
    engine = DeviceEngine(tmp_path, journal)
    engine.terminal_working_directory = tmp_path
    seen = []
    def fake_run(command, **kwargs):
        seen.append({"argv":command,"kwargs":kwargs})
        return CompletedProcess(command, 0, "Android Debug Bridge version 1.0.41", "")
    monkeypatch.setattr(module.subprocess,"run",fake_run)
    engine._run("huawei_terminal_read",["C:/Program Files/adb.exe","version"],timeout=45)
    assert seen[0]["kwargs"]["cwd"] == str(tmp_path)
    assert seen[0]["kwargs"]["shell"] is False
    assert seen[0]["kwargs"]["capture_output"] is True
    engine._run("read_device",["C:/Program Files/adb.exe","devices"],timeout=15)
    assert "cwd" not in seen[1]["kwargs"]


def test_terminal_backend_cd_and_confirmation_bind_to_current_folder(tmp_path, monkeypatch):
    from PySide6.QtCore import QCoreApplication
    from techguy_huawei.backend import Backend
    import techguy_huawei.backend as backend_module
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr(backend_module.AppPaths, "resolve",
        lambda: SimpleNamespace(evidence=tmp_path/"evidence",
                                logs=tmp_path/"logs",
                                registration=tmp_path/"reg.json"))
    monkeypatch.setattr(Backend,"_audit_runtime_wiring",lambda self: None)
    app_root = Path(__file__).resolve().parents[1]
    backend = Backend(app_root)
    backend._terminal_cwd = str(tmp_path.resolve())
    firmware = tmp_path / "rom with spaces"
    firmware.mkdir()
    (firmware / "system.img").write_bytes(b"test")
    backend.submitTerminalLine('cd "' + str(firmware) + '"')
    assert backend.terminalCurrentDirectory == str(firmware)
    backend.submitTerminalLine("pwd")
    assert str(firmware) in backend.terminalOutput
    backend.submitTerminalLine("dir")
    assert "system.img" in backend.terminalOutput
    backend.submitTerminalLine("fastboot flash system system.img")
    assert backend.terminalConfirmationPending is True
    assert backend._pending_terminal[4] == str(firmware)
    backend.submitTerminalLine("cd ..")
    assert not backend.terminalConfirmationPending
    assert backend.confirmTerminalCommand() is False
    assert backend.terminalCurrentDirectory == str(tmp_path)
    backend.submitTerminalLine("cd nonexistent")
    assert backend.terminalCurrentDirectory == str(tmp_path)
    backend.health_timer.stop()

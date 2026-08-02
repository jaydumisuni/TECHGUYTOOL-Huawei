from __future__ import annotations

from pathlib import Path

from techguy_huawei.action_health import ActionState
from techguy_huawei.device_engine import DeviceEngine
from techguy_huawei.evidence import EvidenceJournal


def engine(tmp_path: Path) -> DeviceEngine:
    return DeviceEngine(tmp_path, EvidenceJournal(tmp_path / "evidence.jsonl"))


def test_adb_parser_ignores_daemon_noise() -> None:
    output = """* daemon not running; starting now at tcp:5037\n* daemon started successfully\nList of devices attached\nABC123 device product:VOG-L29 model:VOG-L29\n"""
    assert DeviceEngine._adb_rows(output) == ["ABC123 device product:VOG-L29 model:VOG-L29"]


def test_fastboot_parser_accepts_only_real_rows() -> None:
    output = "ABC123\tfastboot\n< waiting for device >\nnoise\nXYZ fastbootd\n"
    assert DeviceEngine._fastboot_rows(output) == ["ABC123\tfastboot", "XYZ fastbootd"]


def test_guarded_operations_are_explicit(tmp_path: Path) -> None:
    result = engine(tmp_path).guarded("FRP Repair")
    assert result.ok is False
    assert result.health_state is ActionState.GUARDED
    assert "ownership" in result.message.lower()


def test_firmware_preflight_rejects_missing_and_empty(tmp_path: Path) -> None:
    subject = engine(tmp_path)
    missing = subject.package_preflight(str(tmp_path / "missing.zip"))
    assert missing.health_state is ActionState.GUARDED
    empty = tmp_path / "empty.zip"
    empty.write_bytes(b"")
    rejected = subject.package_preflight(str(empty))
    assert rejected.health_state is ActionState.FAILED


def test_firmware_preflight_accepts_nonempty_file(tmp_path: Path) -> None:
    package = tmp_path / "VOG-L29.zip"
    package.write_bytes(b"firmware-evidence")
    result = engine(tmp_path).package_preflight(str(package))
    assert result.ok is True
    assert result.payload == {"path": str(package), "size": len(b"firmware-evidence")}

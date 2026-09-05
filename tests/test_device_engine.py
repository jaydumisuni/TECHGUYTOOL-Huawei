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


def _storage_report():
    from techguy_huawei.usb_discovery import discover_huawei_usb

    return discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E\HUAWEI-FIXTURE",
                "class_name": "USB",
                "friendly_name": "USB Mass Storage Device",
                "device_desc": "USB Mass Storage Device",
                "bus_reported_desc": "HUAWEI",
                "manufacturer": "Compatible USB storage device",
                "hardware_ids": [r"USB\VID_12D1&PID_107E"],
                "compatible_ids": [r"USB\Class_08&SubClass_06&Prot_50"],
                "container_id": "huawei-container",
                "parent_instance_id": "root",
            }
        ]
    )


def _no_huawei_report():
    from techguy_huawei.usb_discovery import discover_huawei_usb

    return discover_huawei_usb([])


def test_probe_prefers_huawei_storage_identity_over_unrelated_redmi_adb(
    monkeypatch, tmp_path: Path
) -> None:
    import techguy_huawei.device_engine as device_engine

    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True, raising=False)
    monkeypatch.setattr(
        device_engine, "discover_windows_huawei_usb", lambda: _storage_report(), raising=False
    )

    def unexpected_run(*args, **kwargs):
        raise AssertionError("ADB/Fastboot must not run before storage-only Huawei identity is returned")

    monkeypatch.setattr(subject, "_run", unexpected_run)
    result = subject.probe()
    assert result.ok is True
    assert result.payload is not None
    assert result.payload["interface"] == "Huawei USB / Pre-service"
    assert result.payload["model"] == "Huawei device (identity pending)"
    assert result.payload["usb_discovery"]["state"] == "storage_only_pre_service"
    assert result.payload["usb_discovery"]["write_authority"] == "none"


def test_windows_generic_redmi_adb_is_not_accepted_as_huawei(
    monkeypatch, tmp_path: Path
) -> None:
    import subprocess
    import techguy_huawei.device_engine as device_engine

    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True, raising=False)
    monkeypatch.setattr(
        device_engine, "discover_windows_huawei_usb", lambda: _no_huawei_report(), raising=False
    )
    monkeypatch.setattr(subject, "_tool", lambda name: name)

    def fake_run(action_id, args, timeout=12):
        command = list(args)
        if command[0] == "adb" and command[1:] == ["devices", "-l"]:
            output = "List of devices attached\nREDMI123 device product:sky model:2312DRA50G\n"
        elif command[0] == "fastboot":
            output = ""
        elif command[:4] == ["adb", "-s", "REDMI123", "shell"] and command[-1] == "ro.product.manufacturer":
            output = "Xiaomi\n"
        else:
            output = ""
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr=""), command

    monkeypatch.setattr(subject, "_run", fake_run)
    result = subject.probe()
    assert result.ok is False
    assert result.health_state is ActionState.READY
    assert "No Huawei device" in result.message
    assert subject.snapshot.connected is False


def test_multiple_huawei_usb_devices_are_guarded(monkeypatch, tmp_path: Path) -> None:
    import techguy_huawei.device_engine as device_engine
    from techguy_huawei.usb_discovery import discover_huawei_usb

    multiple = discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E\A",
                "class_name": "USB",
                "friendly_name": "USB Mass Storage Device",
                "bus_reported_desc": "HUAWEI",
                "hardware_ids": [r"USB\VID_12D1&PID_107E"],
                "container_id": "container-a",
            },
            {
                "instance_id": r"USB\VID_12D1&PID_107E\B",
                "class_name": "USB",
                "friendly_name": "USB Mass Storage Device",
                "bus_reported_desc": "HUAWEI",
                "hardware_ids": [r"USB\VID_12D1&PID_107E"],
                "container_id": "container-b",
            },
        ]
    )
    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True, raising=False)
    monkeypatch.setattr(
        device_engine, "discover_windows_huawei_usb", lambda: multiple, raising=False
    )
    result = subject.probe()
    assert result.ok is False
    assert result.health_state is ActionState.GUARDED
    assert "Multiple Huawei" in result.message


def test_pnp_fastboot_does_not_bind_unrelated_fastboot_cli_serial(monkeypatch, tmp_path: Path) -> None:
    import techguy_huawei.device_engine as device_engine
    from techguy_huawei.usb_discovery import discover_huawei_usb

    huawei_fastboot = discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_3609\HUAWEIROOT",
                "class_name": "AndroidUsbDeviceClass",
                "friendly_name": "HUAWEI Android Bootloader Interface",
                "bus_reported_desc": "HUAWEI Fastboot",
                "hardware_ids": [r"USB\VID_12D1&PID_3609"],
                "container_id": "huawei-fastboot-container",
            }
        ]
    )
    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True, raising=False)
    monkeypatch.setattr(
        device_engine, "discover_windows_huawei_usb", lambda: huawei_fastboot, raising=False
    )

    def unexpected_run(*args, **kwargs):
        raise AssertionError("PnP-proven Huawei Fastboot must not consume an unbound CLI serial")

    monkeypatch.setattr(subject, "_run", unexpected_run)
    result = subject.probe()
    assert result.ok is True
    assert result.payload is not None
    assert result.payload["interface"] == "Fastboot"
    assert result.payload["serial"] == ""
    assert result.payload["usb_discovery"]["state"] == "normal_fastboot"
    assert result.payload["usb_discovery"]["write_authority"] == "none"


def _adb_usb_report():
    from techguy_huawei.usb_discovery import discover_huawei_usb

    return discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E&MI_01\6&ABC&0&0001",
                "class_name": "AndroidUsbDeviceClass",
                "friendly_name": "HUAWEI ADB Interface",
                "bus_reported_desc": "HUAWEI ADB",
                "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_01"],
                "container_id": "huawei-adb-container",
                "parent_instance_id": r"USB\VID_12D1&PID_107E\HUAWEIROOT",
            }
        ]
    )


def test_pnp_huawei_adb_without_verified_authorized_session_stays_guarded(monkeypatch, tmp_path: Path) -> None:
    import subprocess
    import techguy_huawei.device_engine as device_engine

    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True, raising=False)
    monkeypatch.setattr(device_engine, "discover_windows_huawei_usb", lambda: _adb_usb_report(), raising=False)
    monkeypatch.setattr(subject, "_tool", lambda name: name)

    def fake_run(action_id, args, timeout=12):
        command = list(args)
        if command[0] == "adb" and command[1:] == ["devices", "-l"]:
            output = "List of devices attached\nPRIVATE123 unauthorized\n"
        elif command[0] == "fastboot":
            output = ""
        else:
            raise AssertionError(f"unverified ADB row must not be queried: {command}")
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr=""), command

    monkeypatch.setattr(subject, "_run", fake_run)
    result = subject.probe()
    assert result.ok is False
    assert result.health_state is ActionState.GUARDED
    assert "Huawei ADB interface detected" in result.message
    assert "verified authorized Huawei ADB session" in result.message
    assert result.payload is not None
    assert result.payload["usb_discovery"]["state"] == "adb"
    assert "PRIVATE123" not in repr(result.payload)

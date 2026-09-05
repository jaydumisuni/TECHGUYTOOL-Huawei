from __future__ import annotations

import json
import subprocess

import pytest

from techguy_huawei.windows_usb_descriptor import (
    POWERSHELL_USB_DESCRIPTOR_SCRIPT,
    UsbDescriptorError,
    collect_windows_usb_descriptor,
)


def descriptor_payload(*, interfaces: list[dict[str, int]] | None = None) -> str:
    return json.dumps(
        {
            "vid": "12D1",
            "pid": "107E",
            "bcd_device": "0299",
            "manufacturer": "unknown",
            "product": "HUAWEI",
            "configuration_count": 1,
            "interfaces": interfaces
            if interfaces is not None
            else [
                {
                    "number": 0,
                    "alternate": 0,
                    "class_code": 0x08,
                    "subclass_code": 0x06,
                    "protocol_code": 0x50,
                }
            ],
        }
    )


def test_descriptor_reader_uses_fixed_powershell_argv_without_shell() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=descriptor_payload(), stderr="")

    descriptor = collect_windows_usb_descriptor(
        r"USB\VID_12D1&PID_107E\PRIVATE-SERIAL",
        runner=runner,
        powershell="powershell.exe",
    )

    assert descriptor.vid == "12D1"
    assert descriptor.pid == "107E"
    assert descriptor.bcd_device == "0299"
    assert descriptor.mass_storage_only is True
    assert descriptor.configuration_count == 1
    assert not hasattr(descriptor, "serial")
    assert calls[0][0][0] == "powershell.exe"
    assert calls[0][0][1:3] == ["-NoProfile", "-NonInteractive"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["check"] is False


def test_descriptor_reports_composite_configuration_as_not_charge_only() -> None:
    payload = descriptor_payload(
        interfaces=[
            {
                "number": 0,
                "alternate": 0,
                "class_code": 0x08,
                "subclass_code": 0x06,
                "protocol_code": 0x50,
            },
            {
                "number": 1,
                "alternate": 0,
                "class_code": 0xFF,
                "subclass_code": 0x42,
                "protocol_code": 0x01,
            },
        ]
    )

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=payload, stderr="")

    descriptor = collect_windows_usb_descriptor(
        r"USB\VID_12D1&PID_107E\PRIVATE-SERIAL",
        runner=runner,
        powershell="powershell.exe",
    )
    assert descriptor.mass_storage_only is False


def test_descriptor_reader_rejects_malformed_or_non_object_json() -> None:
    for output in ("not json", json.dumps([{"vid": "12D1"}])):
        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        with pytest.raises(UsbDescriptorError) as caught:
            collect_windows_usb_descriptor(
                r"USB\VID_12D1&PID_107E\PRIVATE-SERIAL",
                runner=runner,
                powershell="powershell.exe",
            )
        assert caught.value.code == "USB_DESCRIPTOR_INVALID"


def test_descriptor_reader_rejects_nonzero_powershell_exit() -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 5, stdout="", stderr="access denied")

    with pytest.raises(UsbDescriptorError) as caught:
        collect_windows_usb_descriptor(
            r"USB\VID_12D1&PID_107E\PRIVATE-SERIAL",
            runner=runner,
            powershell="powershell.exe",
        )
    assert caught.value.code == "USB_DESCRIPTOR_UNAVAILABLE"
    assert "access denied" in caught.value.message

def test_descriptor_script_requests_read_only_hub_access() -> None:
    assert "GENERIC_READ" in POWERSHELL_USB_DESCRIPTOR_SCRIPT
    assert "GENERIC_WRITE" not in POWERSHELL_USB_DESCRIPTOR_SCRIPT

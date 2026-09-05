from __future__ import annotations

import json
import subprocess

import pytest

from techguy_huawei.windows_usb import (
    UsbDiscoveryError,
    collect_windows_usb_observations,
    discover_windows_huawei_usb,
)


def fixture_payload() -> str:
    return json.dumps(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E\FIXTURE107E",
                "class_name": "USB",
                "friendly_name": "USB Mass Storage Device",
                "device_desc": "USB Mass Storage Device",
                "bus_reported_desc": "HUAWEI",
                "manufacturer": "Compatible USB storage device",
                "hardware_ids": [r"USB\VID_12D1&PID_107E"],
                "compatible_ids": [r"USB\Class_08&SubClass_06&Prot_50"],
                "container_id": "fixture-container",
                "parent_instance_id": r"USB\ROOT_HUB30\fixture",
            }
        ]
    )


def test_collector_uses_fixed_powershell_argv_without_shell() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=fixture_payload(), stderr="")

    report = discover_windows_huawei_usb(runner=runner, powershell="powershell.exe")
    assert report.state == "storage_only_pre_service"
    assert calls[0][0][0] == "powershell.exe"
    assert calls[0][0][1:3] == ["-NoProfile", "-NonInteractive"]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["check"] is False
    assert calls[0][1]["capture_output"] is True


def test_collector_normalizes_powerShell_json_to_observations() -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="\ufeff" + fixture_payload(), stderr="")

    observations = collect_windows_usb_observations(runner=runner, powershell="powershell.exe")
    assert len(observations) == 1
    assert observations[0].instance_id == r"USB\VID_12D1&PID_107E\FIXTURE107E"
    assert observations[0].hardware_ids == (r"USB\VID_12D1&PID_107E",)


def test_collector_rejects_nonzero_powershell_exit() -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="access denied")

    with pytest.raises(UsbDiscoveryError) as caught:
        collect_windows_usb_observations(runner=runner, powershell="powershell.exe")
    assert caught.value.code == "USB_DISCOVERY_UNAVAILABLE"
    assert "access denied" in caught.value.message


def test_collector_rejects_malformed_or_non_list_json() -> None:
    outputs = ["not json", json.dumps({"instance_id": "one-object"})]
    for output in outputs:
        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        with pytest.raises(UsbDiscoveryError) as caught:
            collect_windows_usb_observations(runner=runner, powershell="powershell.exe")
        assert caught.value.code == "USB_DISCOVERY_INVALID"

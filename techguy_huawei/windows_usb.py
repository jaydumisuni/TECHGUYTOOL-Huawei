from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Callable

from .usb_discovery import UsbDiscoveryReport, UsbObservation, discover_huawei_usb

POWERSHELL_DISCOVERY_SCRIPT = r'''
$get = {
    param($instanceId, $keyName)
    try {
        return (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName $keyName -ErrorAction Stop).Data
    } catch {
        return $null
    }
}
$devices = Get-PnpDevice -PresentOnly | Where-Object {
    $_.InstanceId -match 'VID_12D1' -or
    $_.FriendlyName -match 'Huawei|HUAWEI' -or
    $_.Class -eq 'WPD'
}
$items = @()
foreach ($device in $devices) {
    $hardwareIds = & $get $device.InstanceId 'DEVPKEY_Device_HardwareIds'
    $compatibleIds = & $get $device.InstanceId 'DEVPKEY_Device_CompatibleIds'
    $items += [ordered]@{
        instance_id = [string]$device.InstanceId
        class_name = [string]$device.Class
        friendly_name = [string]$device.FriendlyName
        device_desc = [string](& $get $device.InstanceId 'DEVPKEY_Device_DeviceDesc')
        bus_reported_desc = [string](& $get $device.InstanceId 'DEVPKEY_Device_BusReportedDeviceDesc')
        manufacturer = [string](& $get $device.InstanceId 'DEVPKEY_Device_Manufacturer')
        hardware_ids = @($hardwareIds)
        compatible_ids = @($compatibleIds)
        container_id = [string](& $get $device.InstanceId 'DEVPKEY_Device_ContainerId')
        parent_instance_id = [string](& $get $device.InstanceId 'DEVPKEY_Device_Parent')
    }
}
ConvertTo-Json -InputObject @($items) -Depth 5 -Compress
'''


class UsbDiscoveryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(code, message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def collect_windows_usb_observations(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    powershell: str | None = None,
) -> list[UsbObservation]:
    executable = powershell or shutil.which("powershell.exe") or shutil.which("powershell")
    if not executable:
        raise UsbDiscoveryError("USB_DISCOVERY_UNAVAILABLE", "PowerShell is unavailable")
    command = [
        executable,
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        POWERSHELL_DISCOVERY_SCRIPT,
    ]
    try:
        completed = runner(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UsbDiscoveryError("USB_DISCOVERY_UNAVAILABLE", str(exc)) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "PowerShell discovery failed").strip()
        raise UsbDiscoveryError("USB_DISCOVERY_UNAVAILABLE", detail)
    try:
        payload = json.loads((completed.stdout or "").lstrip("\ufeff").strip() or "[]")
    except json.JSONDecodeError as exc:
        raise UsbDiscoveryError("USB_DISCOVERY_INVALID", str(exc)) from exc
    if not isinstance(payload, list):
        raise UsbDiscoveryError("USB_DISCOVERY_INVALID", "collector JSON root must be an array")
    observations: list[UsbObservation] = []
    for item in payload:
        if not isinstance(item, dict):
            raise UsbDiscoveryError("USB_DISCOVERY_INVALID", "collector item must be an object")
        observations.append(UsbObservation.from_mapping(item))
    return observations


def discover_windows_huawei_usb(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    powershell: str | None = None,
) -> UsbDiscoveryReport:
    return discover_huawei_usb(
        collect_windows_usb_observations(runner=runner, powershell=powershell)
    )

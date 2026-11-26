from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Mapping


POWERSHELL_USB_DESCRIPTOR_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$instanceId = [Environment]::GetEnvironmentVariable('TTG_HUAWEI_USB_INSTANCE_ID')
if ([string]::IsNullOrWhiteSpace($instanceId)) {
    throw 'TTG_HUAWEI_USB_INSTANCE_ID is required'
}
$device = Get-PnpDevice -InstanceId $instanceId -ErrorAction Stop
$get = {
    param($keyName)
    return (Get-PnpDeviceProperty -InstanceId $device.InstanceId -KeyName $keyName -ErrorAction Stop).Data
}
$parent = [string](& $get 'DEVPKEY_Device_Parent')
$port = [int](& $get 'DEVPKEY_Device_Address')
if ([string]::IsNullOrWhiteSpace($parent) -or $port -lt 1) {
    throw 'USB parent/port identity unavailable'
}
$hubPath = '\\?\' + ($parent -replace '\\', '#') + '#{f18a0e88-c30c-11d0-8815-00a0c906bed8}'
$source = @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

public static class TtgUsbDescriptorReader {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFile(string name, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool DeviceIoControl(SafeFileHandle handle, uint code, byte[] input, int inputLength, byte[] output, int outputLength, out int bytesReturned, IntPtr overlapped);

    const uint GENERIC_READ = 0x80000000u;

    const uint FILE_SHARE_READ = 1u;
    const uint FILE_SHARE_WRITE = 2u;
    const uint OPEN_EXISTING = 3u;
    const uint IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX = 0x220448u;
    const uint IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION = 0x220410u;

    static byte[] Descriptor(SafeFileHandle handle, int port, int type, int index, int language, int length, out int returned) {
        if (length < 0 || length > UInt16.MaxValue) throw new InvalidOperationException("descriptor length out of range");
        var buffer = new byte[12 + Math.Max(length, 4)];
        Array.Copy(BitConverter.GetBytes(port), 0, buffer, 0, 4);
        buffer[4] = 0x80;
        buffer[5] = 0x06;
        ushort value = (ushort)((type << 8) | index);
        Array.Copy(BitConverter.GetBytes(value), 0, buffer, 6, 2);
        Array.Copy(BitConverter.GetBytes((ushort)language), 0, buffer, 8, 2);
        Array.Copy(BitConverter.GetBytes((ushort)length), 0, buffer, 10, 2);
        if (!DeviceIoControl(handle, IOCTL_USB_GET_DESCRIPTOR_FROM_NODE_CONNECTION, buffer, buffer.Length, buffer, buffer.Length, out returned, IntPtr.Zero)) {
            throw new InvalidOperationException("descriptor ioctl failed: " + Marshal.GetLastWin32Error());
        }
        if (returned < 12) throw new InvalidOperationException("descriptor response shorter than request header");
        return buffer;
    }

    static string UsbString(SafeFileHandle handle, int port, int index, int language) {
        if (index == 0) return "";
        int stringReturned;
        var buffer = Descriptor(handle, port, 3, index, language, 255, out stringReturned);
        if (stringReturned < 14) return "";
        int length = buffer[12];
        if (length < 2 || buffer[13] != 3 || stringReturned < 12 + length) return "";
        return Encoding.Unicode.GetString(buffer, 14, length - 2).TrimEnd('\0');
    }

    static string Escape(string value) {
        if (value == null) return "";
        return value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
    }

    public static string Read(string hubPath, int port) {
        using (var handle = CreateFile(hubPath, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, 0, IntPtr.Zero)) {
            if (handle.IsInvalid) throw new InvalidOperationException("hub open failed: " + Marshal.GetLastWin32Error());
            var info = new byte[64];
            Array.Copy(BitConverter.GetBytes(port), 0, info, 0, 4);
            int returned;
            if (!DeviceIoControl(handle, IOCTL_USB_GET_NODE_CONNECTION_INFORMATION_EX, info, info.Length, info, info.Length, out returned, IntPtr.Zero)) {
                throw new InvalidOperationException("connection ioctl failed: " + Marshal.GetLastWin32Error());
            }
            ushort vid = BitConverter.ToUInt16(info, 12);
            ushort pid = BitConverter.ToUInt16(info, 14);
            ushort bcd = BitConverter.ToUInt16(info, 16);
            int iManufacturer = info[18];
            int iProduct = info[19];
            int configurationCount = info[21];
            int language = 0x0409;
            try {
                int languageReturned;
                var languages = Descriptor(handle, port, 3, 0, 0, 255, out languageReturned);
                if (languageReturned >= 16 && languages[12] >= 4 && languageReturned >= 12 + languages[12]) {
                    language = BitConverter.ToUInt16(languages, 14);
                }
            } catch { }
            string manufacturer = UsbString(handle, port, iManufacturer, language);
            string product = UsbString(handle, port, iProduct, language);
            var interfaces = new List<string>();
            for (int configurationIndex = 0; configurationIndex < configurationCount; configurationIndex++) {
                int headerReturned;
                var header = Descriptor(handle, port, 2, configurationIndex, 0, 9, out headerReturned);
                if (headerReturned < 21 || header[13] != 2) throw new InvalidOperationException("configuration header truncated or invalid");
                int totalLength = BitConverter.ToUInt16(header, 14);
                if (totalLength < 9) throw new InvalidOperationException("configuration total length is invalid");
                int fullReturned;
                var config = Descriptor(handle, port, 2, configurationIndex, 0, totalLength, out fullReturned);
                if (fullReturned < 12 + totalLength) throw new InvalidOperationException("configuration descriptor truncated");
                int offset = 12;
                if (config[offset + 1] != 2) throw new InvalidOperationException("configuration descriptor type mismatch");
                int end = offset + totalLength;
                for (int cursor = offset; cursor + 1 < end;) {
                    int length = config[cursor];
                    int type = config[cursor + 1];
                    if (length < 2) break;
                    if (type == 4 && cursor + 8 < end) {
                        interfaces.Add(string.Format("{{\"number\":{0},\"alternate\":{1},\"class_code\":{2},\"subclass_code\":{3},\"protocol_code\":{4}}}", config[cursor + 2], config[cursor + 3], config[cursor + 5], config[cursor + 6], config[cursor + 7]));
                    }
                    cursor += length;
                }
            }
            return string.Format("{{\"vid\":\"{0:X4}\",\"pid\":\"{1:X4}\",\"bcd_device\":\"{2:X4}\",\"manufacturer\":\"{3}\",\"product\":\"{4}\",\"configuration_count\":{5},\"interfaces\":[{6}]}}", vid, pid, bcd, Escape(manufacturer), Escape(product), configurationCount, string.Join(",", interfaces));
        }
    }
}
"@
Add-Type -TypeDefinition $source -Language CSharp
[TtgUsbDescriptorReader]::Read($hubPath, $port)
'''


class UsbDescriptorError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(code, message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class UsbInterfaceDescriptor:
    number: int
    alternate: int
    class_code: int
    subclass_code: int
    protocol_code: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UsbInterfaceDescriptor":
        return cls(
            number=int(value["number"]),
            alternate=int(value["alternate"]),
            class_code=int(value["class_code"]),
            subclass_code=int(value["subclass_code"]),
            protocol_code=int(value["protocol_code"]),
        )


@dataclass(frozen=True, slots=True)
class UsbRawDescriptor:
    vid: str
    pid: str
    bcd_device: str
    manufacturer: str
    product: str
    configuration_count: int
    interfaces: tuple[UsbInterfaceDescriptor, ...]

    @property
    def mass_storage_only(self) -> bool:
        interface_numbers = {item.number for item in self.interfaces}
        return (
            self.configuration_count == 1
            and len(interface_numbers) == 1
            and all(
                item.class_code == 0x08
                and item.subclass_code == 0x06
                and item.protocol_code == 0x50
                for item in self.interfaces
            )
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UsbRawDescriptor":
        interfaces = value.get("interfaces")
        if not isinstance(interfaces, list):
            raise ValueError("interfaces must be a list")
        return cls(
            vid=str(value["vid"]).upper(),
            pid=str(value["pid"]).upper(),
            bcd_device=str(value["bcd_device"]).upper(),
            manufacturer=str(value.get("manufacturer") or ""),
            product=str(value.get("product") or ""),
            configuration_count=int(value["configuration_count"]),
            interfaces=tuple(UsbInterfaceDescriptor.from_mapping(item) for item in interfaces),
        )


def collect_windows_usb_descriptor(
    instance_id: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    powershell: str | None = None,
) -> UsbRawDescriptor:
    executable = powershell or shutil.which("powershell.exe") or shutil.which("powershell")
    if not executable:
        raise UsbDescriptorError("USB_DESCRIPTOR_UNAVAILABLE", "PowerShell is unavailable")
    environment = os.environ.copy()
    environment["TTG_HUAWEI_USB_INSTANCE_ID"] = str(instance_id)
    command = [
        executable,
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        POWERSHELL_USB_DESCRIPTOR_SCRIPT,
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
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UsbDescriptorError("USB_DESCRIPTOR_UNAVAILABLE", str(exc)) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "USB descriptor query failed").strip()
        raise UsbDescriptorError("USB_DESCRIPTOR_UNAVAILABLE", detail) from None
    try:
        payload = json.loads((completed.stdout or "").lstrip("\ufeff").strip())
    except json.JSONDecodeError as exc:
        raise UsbDescriptorError("USB_DESCRIPTOR_INVALID", str(exc)) from exc
    if not isinstance(payload, dict):
        raise UsbDescriptorError("USB_DESCRIPTOR_INVALID", "descriptor JSON root must be an object")
    try:
        descriptor = UsbRawDescriptor.from_mapping(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise UsbDescriptorError("USB_DESCRIPTOR_INVALID", str(exc)) from exc
    if descriptor.vid != "12D1":
        raise UsbDescriptorError("USB_DESCRIPTOR_INVALID", "descriptor is not Huawei VID 12D1")
    return descriptor

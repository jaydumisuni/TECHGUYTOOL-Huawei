from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from techguy_huawei import device_engine, hdc_toolchain
from techguy_huawei.hdc_identity import HdcIdentity, probe_hdc_identity
from techguy_huawei.evidence import EvidenceJournal
from techguy_huawei.usb_discovery import discover_huawei_usb


ROOT_ID = r"USB\VID_12D1&PID_1100\SAFETEST123"


def pnp_hdc():
    return discover_huawei_usb([{
        "instance_id": ROOT_ID,
        "container_id": "{AABBCCDD-1111-2222-3333-444455556666}",
        "class_name": "USBDevice",
        "friendly_name": "HarmonyOS Device",
        "bus_reported_desc": "HarmonyOS Device",
        "hardware_ids": [r"USB\VID_12D1&PID_1100&REV_0224"],
        "compatible_ids": [r"USB\MS_COMP_WINUSB"],
    }])


class SyntheticHdc:
    def __init__(self, listing="KEY-2026 USB Connected localhost hdc",
                 model="PLR-AL00", brand="HUAWEI", build="HarmonyOS 5.0"):
        self.listing = listing
        self.model = model
        self.brand = brand
        self.build = build
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args[1:])
        assert kwargs["shell"] is False
        if args[1:] == ["-v"]:
            return CompletedProcess(args, 0, "Ver: 3.2.0e", "")
        if args[1:] == ["list", "targets", "-v"]:
            return CompletedProcess(args, 0, self.listing, "")
        param = args[1:]
        assert param[:5] == ["-t", "KEY-2026", "shell", "param", "get"]
        values = {
            "const.product.model": self.model,
            "const.product.brand": self.brand,
            "const.product.software.version": self.build,
        }
        return CompletedProcess(args, 0, values.get(param[-1], ""), "")


def test_harmony_winusb_is_not_mtp_or_fastboot():
    report = pnp_hdc()
    assert report.state == "harmony_hdc"
    assert report.transport == "windows_winusb_hdc"
    assert report.pid == "1100"
    assert "HarmonyOS HDC (WinUSB)" in report.interfaces
    assert report.model == "identity_pending"
    assert report.write_authority == "none"


def test_hdc_returns_model_only_after_connected_usb_property_read():
    fake = SyntheticHdc()
    result = probe_hdc_identity("hdc.exe", runner=fake)
    assert result.identity_verified is True
    assert result.model == "PLR-AL00"
    assert result.brand == "HUAWEI"
    assert result.build == "HarmonyOS 5.0"
    assert len(fake.calls) == 5
    assert not any(any(x in args for x in ("install","flash","reboot","mount","param set")) for args in fake.calls)
    assert result.target_key_sha256 == sha256(b"KEY-2026").hexdigest()


@pytest.mark.parametrize("listing,state", [
    ("[Empty]", "empty"),
    ("KEY-2026 USB Unauthorized localhost hdc", "unauthorized"),
    ("KEY-2026 USB Offline localhost hdc", "offline"),
    ("KEY-2026 USB Connected localhost hdc\nKEY-2027 USB Connected localhost hdc", "multiple_usb_targets"),
    ("127.0.0.1:5555 TCP Connected localhost hdc", "empty_or_unrecognized"),
    ("COM14\t\tUART\tReady\tunknown...\thdc", "non_usb_targets_only"),
])
def test_non_authorized_or_ambiguous_target_never_reads_properties(listing, state):
    fake = SyntheticHdc(listing=listing)
    result = probe_hdc_identity("hdc.exe", runner=fake)
    assert not result.identity_verified
    assert result.status == state
    assert fake.calls == [["-v"], ["list", "targets", "-v"]]


def test_no_fake_model_when_property_not_available():
    fake = SyntheticHdc(model="Permission denied")
    result = probe_hdc_identity("hdc.exe", runner=fake)
    assert result.status == "property_unavailable"
    assert not result.model
    assert len(fake.calls) == 3


def test_non_huawei_brand_fails_closed():
    fake = SyntheticHdc(brand="OTHER")
    result = probe_hdc_identity("hdc.exe", runner=fake)
    assert result.status == "brand_mismatch"
    assert not result.model


def test_missing_hdc_binary_is_explicit_not_transport_failure():
    result = probe_hdc_identity("")
    assert result.status == "missing_tool"
    assert not result.identity_verified


def test_read_device_uses_hdc_not_adb_or_fastboot_when_pnp_1100(monkeypatch, tmp_path):
    monkeypatch.setattr(device_engine, "discover_windows_huawei_usb", pnp_hdc)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True)
    monkeypatch.setattr(device_engine, "resolve_hdc_tool", lambda root: "mock-hdc.exe")
    monkeypatch.setattr(
        device_engine, "probe_hdc_identity",
        lambda path: HdcIdentity("model_read", "PLR-AL00", "HUAWEI", "5.0", "a"*64),
    )
    engine = device_engine.DeviceEngine(tmp_path, EvidenceJournal(tmp_path / "events.jsonl"))
    monkeypatch.setattr(engine, "_run", lambda *args: pytest.fail("ADB/Fastboot must not be called"))
    response = engine.probe()
    assert response.ok
    assert engine.snapshot.interface == "HarmonyOS HDC"
    assert engine.snapshot.model == "PLR-AL00"
    assert response.payload["identity_binding"] == "unbound_protocol_and_usb_cohort"
    assert response.payload["hdc_probe"]["identity_verified"]


def test_read_device_detects_hdc_when_tool_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(device_engine, "discover_windows_huawei_usb", pnp_hdc)
    monkeypatch.setattr(device_engine, "_is_windows", lambda: True)
    monkeypatch.setattr(device_engine, "resolve_hdc_tool", lambda root: None)
    engine = device_engine.DeviceEngine(tmp_path, EvidenceJournal(tmp_path / "events.jsonl"))
    monkeypatch.setattr(engine, "_run", lambda *args: pytest.fail("ADB/Fastboot must not be called"))
    response = engine.probe()
    assert response.ok
    assert engine.snapshot.model == "Huawei device (identity pending)"
    assert "HDC executable not installed" in response.message
    assert response.payload["hdc_probe"]["status"] == "missing_tool"


def test_hdc_toolchain_requires_verified_manifest_and_detects_tampering(tmp_path):
    root = tmp_path / "runtime" / "harmonyos" / "toolchains"
    root.mkdir(parents=True)
    binary = root / "hdc.exe"
    binary.write_bytes(b"SYNTHETIC-SIGNED-SDK-TOOL")
    assert hdc_toolchain.resolve_hdc_tool(tmp_path) is None
    manifest = root / "hdc-manifest.json"
    manifest.write_text(json.dumps({
        "schema": hdc_toolchain.SCHEMA, "source": "synthetic unit test",
        "files": {"hdc.exe": sha256(binary.read_bytes()).hexdigest()},
    }), encoding="utf8")
    assert hdc_toolchain.resolve_hdc_tool(tmp_path) == str(binary)
    binary.write_bytes(b"ALTERED")
    assert hdc_toolchain.resolve_hdc_tool(tmp_path) is None


def test_outdated_hdc_refused_before_hardware_queries():
    fake = SyntheticHdc()
    original = fake.__call__
    def old_version(args, **kw):
        if args[1:] == ["-v"]:
            fake.calls.append(args[1:])
            return CompletedProcess(args, 0, "Ver: 1.2.0a", "")
        return original(args, **kw)
    result = probe_hdc_identity("hdc.exe", runner=old_version)
    assert result.status == "unsupported_version"
    assert not result.identity_verified
    assert fake.calls == [["-v"]]

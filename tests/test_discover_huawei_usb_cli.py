from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from techguy_huawei.usb_discovery import discover_huawei_usb

ROOT = Path(__file__).resolve().parents[1]


def _load_cli_module():
    path = ROOT / "tools" / "discover_huawei_usb.py"
    spec = importlib.util.spec_from_file_location("discover_huawei_usb_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_and_proof_file_do_not_expose_raw_pnp_descriptions(monkeypatch, capsys) -> None:
    report = discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E&MI_01\PRIVATE-SERIAL",
                "class_name": "AndroidUsbDeviceClass",
                "friendly_name": "HUAWEI ADB PRIVATE-SERIAL",
                "device_desc": "PRIVATE-SERIAL device description",
                "bus_reported_desc": "PRIVATE-SERIAL HUAWEI ADB",
                "manufacturer": "HUAWEI",
                "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_01"],
                "container_id": "private-interface-container",
                "parent_instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL",
            }
        ]
    )
    module = _load_cli_module()
    monkeypatch.setattr(module, "discover_windows_huawei_usb", lambda: report)
    proof_root = ROOT / "proof" / "tests" / "usb-cli-private"
    shutil.rmtree(proof_root, ignore_errors=True)
    output = proof_root / "discovery.json"
    try:
        assert module.main(["--output", str(output)]) == 0
        stdout = capsys.readouterr().out
        file_text = output.read_text(encoding="utf-8")
        assert "PRIVATE-SERIAL" not in stdout
        assert "PRIVATE-SERIAL" not in file_text
        assert '"ADB"' in file_text
    finally:
        shutil.rmtree(proof_root, ignore_errors=True)

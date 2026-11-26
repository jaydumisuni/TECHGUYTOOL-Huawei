"""Builder-owned Support consumption: deterministic, no live install changes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from techguy_huawei import platform_tools


FILES=("adb.exe","fastboot.exe","AdbWinApi.dll","AdbWinUsbApi.dll")


def install_fixture(support: Path) -> Path:
    tool_root=support/"Android"/"platform-tools"
    tool_root.mkdir(parents=True)
    hashes={}
    for name in FILES:
        data=(name+" fixture bytes").encode("utf-8")
        (tool_root/name).write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    manifest=support/"manifests"/"android-platform-tools.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"schema":"ttg.shared-support.android-platform-tools.v1",
                                    "version":"fixture-2026","files":hashes}))
    return tool_root


def test_verified_shared_tools_are_preferred_for_both_binaries(tmp_path,monkeypatch):
    support=tmp_path/"Program Files (x86)"/"THETECHGUY Digital Solutions"/"Support"
    shared=install_fixture(support)
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    app=tmp_path/"app"
    existing=app/"runtime/platform-tools"
    existing.mkdir(parents=True)
    (existing/"adb.exe").write_bytes(b"old-app-adb")
    (existing/"fastboot.exe").write_bytes(b"old-app-fastboot")
    assert Path(platform_tools.resolve_tool(app,"adb"))==shared/"adb.exe"
    assert Path(platform_tools.resolve_tool(app,"fastboot"))==shared/"fastboot.exe"


def test_missing_manifest_falls_back_without_writing(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    shared=install_fixture(support)
    (support/"manifests"/"android-platform-tools.json").unlink()
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    app=tmp_path/"app"
    legacy=app/"runtime/platform-tools"
    legacy.mkdir(parents=True)
    (legacy/"adb.exe").write_bytes(b"legacy")
    assert Path(platform_tools.resolve_tool(app,"adb"))==legacy/"adb.exe"
    assert (shared/"adb.exe").read_bytes()==b"adb.exe fixture bytes"


def test_tampered_shared_binary_never_selected(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    shared=install_fixture(support)
    (shared/"fastboot.exe").write_bytes(b"tampered")
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    app=tmp_path/"app"
    local=app/"runtime/platform-tools"
    local.mkdir(parents=True)
    (local/"adb.exe").write_bytes(b"local-adb")
    (local/"fastboot.exe").write_bytes(b"local-fastboot")
    assert Path(platform_tools.resolve_tool(app,"adb"))==local/"adb.exe"
    assert Path(platform_tools.resolve_tool(app,"fastboot"))==local/"fastboot.exe"


def test_missing_shared_companion_rejects_shared_package(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    shared=install_fixture(support)
    (shared/"AdbWinUsbApi.dll").unlink()
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    assert platform_tools._verified_shared_dir() is None


def test_unrecognized_support_schema_rejected(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    install_fixture(support)
    manifest=support/"manifests"/"android-platform-tools.json"
    content=json.loads(manifest.read_text())
    content["schema"]="other-vendor-schema"
    manifest.write_text(json.dumps(content))
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    assert platform_tools._verified_shared_dir() is None


def test_unlisted_extra_shared_file_cannot_be_selected(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    shared=install_fixture(support)
    (shared/"extra.exe").write_bytes(b"unexpected")
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    assert platform_tools._verified_shared_dir() is None


def test_shared_inventory_tamper_is_rejected(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    shared=install_fixture(support)
    (shared/"AdbWinApi.dll").write_bytes(b"modified after install")
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    assert platform_tools._verified_shared_dir() is None


def test_tools_reject_unrecognized_names(tmp_path,monkeypatch):
    support=tmp_path/"Support"
    install_fixture(support)
    monkeypatch.setattr(platform_tools,"shared_support_root",lambda:support)
    assert platform_tools.resolve_tool(tmp_path,"bash") is None
    assert platform_tools.resolve_tool(tmp_path,"cmd") is None

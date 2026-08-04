from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_source_compiles() -> None:
    for path in [ROOT / "main.py", *(ROOT / "techguy_huawei").glob("*.py")]:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_all_qml_action_calls_are_declared() -> None:
    manifest = json.loads((ROOT / "data" / "action_manifest.json").read_text(encoding="utf-8"))
    declared = {entry["id"] for entry in manifest["actions"]}
    used: set[str] = set()
    for path in (ROOT / "qml").rglob("*.qml"):
        used.update(re.findall(r'runAction\("([a-z0-9_]+)"\)', path.read_text(encoding="utf-8")))
    assert used <= declared
    assert {"read_device", "open_terminal", "fix_drivers", "flash_firmware"} <= used


def test_manifest_ids_are_unique_and_guard_reasons_are_present() -> None:
    manifest = json.loads((ROOT / "data" / "action_manifest.json").read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in manifest["actions"]]
    assert len(ids) == len(set(ids))
    for entry in manifest["actions"]:
        if entry.get("guarded"):
            assert entry.get("guard_reason", "").strip()


def test_no_shell_execution_or_destructive_fastboot_commands() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "techguy_huawei").glob("*.py"))
    assert "shell=True" not in source
    for forbidden in ("fastboot erase", "fastboot format", "fastboot flashing unlock", "fastboot oem unlock"):
        assert forbidden not in source.lower()


def test_reference_geometry_and_brand_assets_exist() -> None:
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    assert re.search(r"\bwidth:\s*1586\b", main)
    assert re.search(r"\bheight:\s*992\b", main)
    for relative in ("assets/brand/techguy_logo.svg", "assets/brand/techguy_mascot.svg", "assets/brand/techguy_logo.svg"):
        path = ROOT / relative
        assert path.is_file() and path.stat().st_size > 0


def test_onefile_deployment_contract() -> None:
    spec = (ROOT / "pysidedeploy.spec").read_text(encoding="utf-8")
    assert "mode = onefile" in spec
    assert "TECHGUYTOOL_Huawei.exe" in spec
    build = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert "pyside6-deploy" in build
    assert "pyside6-rcc" in build
    assert "Get-FileHash -Algorithm SHA256" in build

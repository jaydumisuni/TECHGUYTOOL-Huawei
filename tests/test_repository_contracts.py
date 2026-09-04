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
    assert "title = TECHGUY TOOL Huawei" in spec
    assert "--msvc=latest" in spec
    assert "--assume-yes-for-downloads" in spec
    assert "--output-filename=" not in spec

    build = (ROOT / "build_windows.ps1").read_text(encoding="utf-8")
    assert "pyside6-deploy" in build
    assert "pyside6-rcc" in build
    assert 'Filter "TECHGUY TOOL Huawei.exe"' in build
    assert 'Filter "main.exe"' in build
    assert '"TECHGUYTOOL_Huawei.exe"' in build
    assert "New-Item -ItemType Directory -Force $TargetDirectory" in build
    assert "Move-Item" in build
    assert "Get-FileHash -Algorithm SHA256" in build


def test_qt_release_dependency_is_frozen() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    proof_workflow = (ROOT / ".github" / "workflows" / "proof.yml").read_text(encoding="utf-8")

    exact = "PySide6==6.11.1"
    assert exact in pyproject
    assert exact in requirements
    assert exact in proof_workflow
    assert "PySide6>=6.8,<7" not in pyproject
    assert "PySide6>=6.8,<7" not in requirements


def test_visual_comparator_tracks_seven_state_capture_contract() -> None:
    source = (ROOT / "tools" / "compare_final_ui_states.py").read_text(encoding="utf-8")
    assert '("06-terminal.png", "07-terminal.png")' in source
    assert 'text.split("## Required seventh Phase 15 state", 1)[0]' in source
    assert 're.findall(r"`([a-fA-F0-9]{64})`", locked_section)' in source
    assert "import numpy" not in source

def test_source_freeze_uses_committed_git_blob_authority() -> None:
    generator = (ROOT / "tools" / "build_source_inventory.py").read_text(encoding="utf-8")
    verifier = (ROOT / "tools" / "verify_source_freeze.py").read_text(encoding="utf-8")
    head_tree = '["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"]'
    head_blob = '["git", "show", f"HEAD:{rel}"]'
    assert head_tree in generator
    assert head_tree in verifier
    assert head_blob in generator
    assert head_blob in verifier
    assert "tracked source modified outside committed authority" in verifier


def test_ui_proof_workflow_quotes_yaml_colon_command() -> None:
    workflow = (ROOT / ".github" / "workflows" / "proof.yml").read_text(encoding="utf-8")
    assert "--only-binary=:all:" in workflow
    assert not re.search(r"^\s*run:\s+[^\n]*--only-binary=:all:\s", workflow, re.MULTILINE)

def test_resources_qrc_matches_deterministic_generator_order() -> None:
    expected = [
        path.relative_to(ROOT).as_posix()
        for folder in (ROOT / "qml", ROOT / "assets")
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    ]
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    actual = re.findall(r'<file alias="([^"]+)">', qrc)
    assert actual == expected

def test_smoke_qml_wraps_application_window_as_qquickwindow() -> None:
    source = (ROOT / "tools" / "smoke_qml.py").read_text(encoding="utf-8")
    assert "from PySide6.QtQuick import QQuickWindow" in source
    assert "def as_quick_window" in source
    assert "window = as_quick_window(engine.rootObjects()[0])" in source

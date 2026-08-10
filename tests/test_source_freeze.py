from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_verifier():
    path = ROOT / "tools" / "verify_source_freeze.py"
    spec = importlib.util.spec_from_file_location("verify_source_freeze", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase1_source_freeze_is_coherent() -> None:
    verifier = _load_verifier()
    assert verifier.verify() == []


def test_release_filename_matches_frozen_plan() -> None:
    expected = "TECHGUYTOOL_Huawei.exe"
    checked = (
        "build_windows.ps1",
        "README.md",
        "tools/review_20_for_2.py",
        "tests/test_repository_contracts.py",
    )
    for rel in checked:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert expected in text
        assert "TECHGUY" + "_TOOL_Huawei.exe" not in text

    deploy_spec = (ROOT / "pysidedeploy.spec").read_text(encoding="utf-8")
    assert "mode = onefile" in deploy_spec
    assert "--output-filename=" not in deploy_spec

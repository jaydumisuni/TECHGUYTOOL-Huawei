from __future__ import annotations

"""End-to-end click/keyboard regression for the six shared Huawei selectors."""

from pathlib import Path
import os
import subprocess
import sys
import pytest

pytest.importorskip("PySide6")
ROOT = Path(__file__).resolve().parents[1]


def test_model_chipset_tabs_search_suggestion_clicks_and_autofill():
    temp = ROOT / ".workspace" / ".tmp" / "device-selector-ui-test"
    temp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "QT_QPA_PLATFORM": "offscreen",
        "QT_QUICK_CONTROLS_STYLE": "Basic",
        "PYTHONIOENCODING": "utf-8",
        "TEMP": str(temp),
        "TMP": str(temp),
        "TMPDIR": str(temp),
    })
    result = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "support" / "verify_device_target_selector.py")],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "UI_CLICK_AND_SEARCH_PASS" in result.stdout
    assert "SIX_PAGES_SELECTOR_ACTIVE_PASS" in result.stdout

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

from techguy_huawei.action_health import ActionRegistry
from techguy_huawei.desktop_worker import HealthAuditWorker

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "runtime" / "health" / ("techguy_health_core.exe" if os.name == "nt" else "techguy_health_core")
MANIFEST = ROOT / "data" / "action_manifest.json"


def _expected_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def test_periodic_health_worker_runs_silently_and_reports(tmp_path: Path) -> None:
    executable = tmp_path / ("health.exe" if os.name == "nt" else "health")
    executable.write_bytes(b"fixture")
    results = []
    worker = HealthAuditWorker(executable, MANIFEST)
    worker.signals.finished.connect(results.append)
    process = subprocess.CompletedProcess(
        [str(executable), str(MANIFEST)],
        0,
        stdout=json.dumps({"ok": True, "action_count": 8}),
        stderr="",
    )
    with patch("subprocess.run", return_value=process) as run:
        worker.run()
    assert results == [{"ok": True, "action_count": 8}]
    args, kwargs = run.call_args
    assert args[0] == [str(executable), str(MANIFEST)]
    assert kwargs["creationflags"] == _expected_flags()
    assert kwargs["capture_output"] is True
    assert kwargs["shell"] is False


def test_direct_registry_audit_uses_no_console_flag(tmp_path: Path) -> None:
    executable = tmp_path / ("health.exe" if os.name == "nt" else "health")
    executable.write_bytes(b"fixture")
    registry = ActionRegistry({}, MANIFEST)
    process = subprocess.CompletedProcess(
        [str(executable), str(MANIFEST)],
        0,
        stdout=json.dumps({"ok": True, "action_count": 8}),
        stderr="",
    )
    with patch("subprocess.run", return_value=process) as run:
        result = registry.run_rust_audit(executable)
    assert result == {"ok": True, "action_count": 8}
    args, kwargs = run.call_args
    assert args[0] == [str(executable), str(MANIFEST)]
    assert kwargs["creationflags"] == _expected_flags()
    assert kwargs["capture_output"] is True
    assert kwargs["shell"] is False

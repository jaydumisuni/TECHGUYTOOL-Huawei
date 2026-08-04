from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from techguy_huawei.action_health import ActionRegistry, ActionState


@dataclass
class Result:
    message: str
    health_state: ActionState


def manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "actions": [
                    {"id": "ready", "label": "Ready", "guarded": False},
                    {"id": "guarded", "label": "Guarded", "guarded": True, "guard_reason": "Proof required"},
                    {"id": "missing", "label": "Missing", "guarded": False},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_registry_detects_wiring_and_guarded_state(tmp_path: Path) -> None:
    reg = ActionRegistry(
        {
            "ready": lambda: Result("ok", ActionState.READY),
            "guarded": lambda: Result("blocked", ActionState.GUARDED),
        },
        manifest(tmp_path / "manifest.json"),
    )
    snapshot = {item["action_id"]: item for item in reg.snapshot()}
    assert snapshot["ready"]["state"] == ActionState.READY
    assert snapshot["guarded"]["state"] == ActionState.GUARDED
    assert snapshot["missing"]["state"] == ActionState.NOT_IMPLEMENTED
    assert reg.expected_ids() == {"ready", "guarded", "missing"}


def test_registry_records_invocation_outcome(tmp_path: Path) -> None:
    reg = ActionRegistry(
        {"ready": lambda: Result("completed", ActionState.READY), "guarded": lambda: Result("proof required", ActionState.GUARDED)},
        manifest(tmp_path / "manifest.json"),
    )
    assert reg.invoke("ready").message == "completed"
    snapshot = {item["action_id"]: item for item in reg.snapshot()}
    assert snapshot["ready"]["invocations"] == 1
    assert snapshot["ready"]["detail"] == "completed"


def test_registry_refuses_undeclared_action(tmp_path: Path) -> None:
    reg = ActionRegistry({}, manifest(tmp_path / "manifest.json"))
    with pytest.raises(KeyError):
        reg.invoke("not-in-manifest")

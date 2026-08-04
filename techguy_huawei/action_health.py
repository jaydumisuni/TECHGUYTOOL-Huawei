from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Mapping
import json
import subprocess


class ActionState(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    GUARDED = "GUARDED"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    FAILED = "FAILED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass(slots=True)
class ActionHealth:
    action_id: str
    state: ActionState
    detail: str
    checked_at: str
    invocations: int = 0
    failures: int = 0

    @classmethod
    def initial(cls, action_id: str, state: ActionState, detail: str) -> "ActionHealth":
        return cls(action_id, state, detail, datetime.now(timezone.utc).isoformat())


class ActionRegistry:
    """Runtime wiring ledger used by every visible action.

    A button cannot invoke anonymous code. It must name a registered action, and
    every invocation updates an inspectable health record. This makes dead wiring,
    missing dependencies and guarded write operations visible to the UI and logs.
    """

    def __init__(self, handlers: Mapping[str, Callable[[], object]], manifest_path: Path) -> None:
        self._handlers = dict(handlers)
        self._manifest_path = manifest_path
        self._health: dict[str, ActionHealth] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        for item in payload["actions"]:
            action_id = item["id"]
            guarded = bool(item.get("guarded", False))
            if action_id not in self._handlers:
                state = ActionState.NOT_IMPLEMENTED
                detail = "No backend handler is registered."
            elif guarded:
                state = ActionState.GUARDED
                detail = item.get("guard_reason", "Write operation requires an approved engine and authorization.")
            else:
                state = ActionState.READY
                detail = "Handler registered."
            self._health[action_id] = ActionHealth.initial(action_id, state, detail)

    def invoke(self, action_id: str) -> object:
        health = self._health.get(action_id)
        if health is None:
            raise KeyError(f"Undeclared action: {action_id}")
        if action_id not in self._handlers:
            health.failures += 1
            health.state = ActionState.NOT_IMPLEMENTED
            health.detail = "Action is declared but no handler is registered."
            health.checked_at = datetime.now(timezone.utc).isoformat()
            raise RuntimeError(health.detail)
        health.invocations += 1
        health.state = ActionState.RUNNING
        health.detail = "Action running."
        health.checked_at = datetime.now(timezone.utc).isoformat()
        try:
            result = self._handlers[action_id]()
        except Exception as exc:
            health.failures += 1
            health.state = ActionState.FAILED
            health.detail = str(exc)
            health.checked_at = datetime.now(timezone.utc).isoformat()
            raise
        state = getattr(result, "health_state", None)
        if state in set(ActionState):
            health.state = ActionState(state)
        else:
            health.state = ActionState.READY
        health.detail = getattr(result, "message", "Action completed.")
        health.checked_at = datetime.now(timezone.utc).isoformat()
        return result

    def expected_ids(self) -> set[str]:
        return set(self._health)

    def snapshot(self) -> list[dict[str, object]]:
        return [asdict(self._health[key]) for key in sorted(self._health)]

    def summary(self) -> str:
        counts: dict[str, int] = {}
        for value in self._health.values():
            counts[value.state.value] = counts.get(value.state.value, 0) + 1
        return " · ".join(f"{key} {counts[key]}" for key in sorted(counts))

    def run_rust_audit(self, executable: Path) -> dict[str, object] | None:
        if not executable.is_file():
            return None
        completed = subprocess.run(
            [str(executable), str(self._manifest_path)],
            check=False,
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode != 0:
            return {"ok": False, "error": completed.stderr.strip() or "Rust health audit failed."}
        return json.loads(completed.stdout)

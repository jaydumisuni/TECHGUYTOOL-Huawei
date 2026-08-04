from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import uuid


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8", errors="replace")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    envelope_id: str
    session_id: str
    action_id: str
    captured_at: str
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        action_id: str,
        command: list[str],
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> "EvidenceEnvelope":
        return cls(
            envelope_id=str(uuid.uuid4()),
            session_id=session_id,
            action_id=action_id,
            captured_at=datetime.now(timezone.utc).isoformat(),
            command=tuple(command),
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=_digest(stdout),
            stderr_sha256=_digest(stderr),
        )

    def verify(self) -> bool:
        return self.stdout_sha256 == _digest(self.stdout) and self.stderr_sha256 == _digest(self.stderr)


class EvidenceJournal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, envelope: EvidenceEnvelope) -> None:
        if not envelope.verify():
            raise ValueError("Evidence envelope failed self-verification.")
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(envelope), sort_keys=True, ensure_ascii=False) + "\n")

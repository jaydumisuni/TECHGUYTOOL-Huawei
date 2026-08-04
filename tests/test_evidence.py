from __future__ import annotations

import json
from pathlib import Path

from techguy_huawei.evidence import EvidenceEnvelope, EvidenceJournal


def test_envelope_hashes_and_journal_round_trip(tmp_path: Path) -> None:
    envelope = EvidenceEnvelope.create(
        session_id="session",
        action_id="read_device",
        command=["adb", "devices", "-l"],
        return_code=0,
        stdout="ABC device\n",
        stderr="",
    )
    assert envelope.verify()
    path = tmp_path / "journal.jsonl"
    EvidenceJournal(path).append(envelope)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["envelope_id"] == envelope.envelope_id
    assert payload["stdout_sha256"] == envelope.stdout_sha256
    assert payload["command"] == ["adb", "devices", "-l"]

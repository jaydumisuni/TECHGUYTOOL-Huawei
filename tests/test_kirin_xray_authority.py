from __future__ import annotations

from pathlib import Path

import pytest

from techguy_huawei.kirin_xray import KirinReplayError, load_replay

ROOT = Path(__file__).resolve().parents[1]
P30 = ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json"


def test_changed_source_hash_is_rejected_by_frozen_authority() -> None:
    replay = load_replay(P30)
    replay["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(KirinReplayError, match="SOURCE_AUTHORITY_MISMATCH"):
        load_replay(replay)


def test_changed_donor_commit_is_rejected_by_frozen_authority() -> None:
    replay = load_replay(P30)
    replay["donor"]["commit"] = "0" * 40
    with pytest.raises(KirinReplayError, match="DONOR_AUTHORITY_MISMATCH"):
        load_replay(replay)

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SOURCE_AUTHORITY_PATH = ROOT / "manifests" / "kirin_xray_sources.json"
PRIVATE_ARCHIVE_PATH = ROOT / "manifests" / "private_source_archive.json"
SOURCE_AUTHORITY_SCHEMA = "techguytool-huawei.phase4-kirin-xray-sources.v1"

ErrorFactory = Callable[[str, str], Exception]


@lru_cache(maxsize=1)
def load_source_authority() -> dict[str, Any]:
    """Load and cross-check the public Phase 4 source authority."""

    try:
        authority = json.loads(SOURCE_AUTHORITY_PATH.read_text(encoding="utf-8"))
        archive = json.loads(PRIVATE_ARCHIVE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Kirin Xray source authority is unavailable: {exc}") from exc

    if not isinstance(authority, dict) or authority.get("schema") != SOURCE_AUTHORITY_SCHEMA:
        raise ValueError("Kirin Xray source authority schema is unsupported")
    if not isinstance(archive, dict):
        raise ValueError("private recovery archive manifest must be an object")

    private = authority.get("private_archive")
    archive_identity = archive.get("authority")
    if not isinstance(private, dict) or not isinstance(archive_identity, dict):
        raise ValueError("Kirin Xray source authority is missing private archive identity")
    if private.get("drive_file_id") != archive_identity.get("drive_file_id"):
        raise ValueError("Kirin Xray source authority Drive identity does not match recovery")
    if private.get("sha256") != archive_identity.get("sha256"):
        raise ValueError("Kirin Xray source authority archive SHA-256 does not match recovery")
    if private.get("publish_raw_contents") is not False:
        raise ValueError("Kirin Xray source authority must prohibit raw publication")

    sources = authority.get("sources")
    selected = archive.get("selected_records")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Kirin Xray source authority must contain reviewed sources")
    if not isinstance(selected, list):
        raise ValueError("private recovery archive has no selected records")

    reviewed = {_source_identity(record) for record in selected}
    frozen = [_source_identity(record) for record in sources]
    if len(frozen) != len(set(frozen)):
        raise ValueError("Kirin Xray source authority contains duplicate records")
    unknown = sorted(set(frozen) - reviewed)
    if unknown:
        raise ValueError(f"Kirin Xray source authority contains unreviewed records: {unknown}")

    donor = authority.get("donor")
    if not isinstance(donor, dict) or set(donor) != {"commit", "repository", "version"}:
        raise ValueError("Kirin Xray donor authority is malformed")
    return authority


def validate_replay_authority(
    replay: Mapping[str, Any], *, error_factory: ErrorFactory
) -> None:
    """Reject replay donor or source identities outside the frozen authority."""

    try:
        authority = load_source_authority()
    except ValueError as exc:
        raise error_factory("SOURCE_AUTHORITY_UNAVAILABLE", str(exc)) from exc

    donor = replay.get("donor")
    if donor != authority["donor"]:
        raise error_factory(
            "DONOR_AUTHORITY_MISMATCH",
            "replay donor does not match the frozen Kirin Xray donor authority",
        )

    allowed = {_source_identity(record) for record in authority["sources"]}
    sources = replay.get("sources")
    if not isinstance(sources, list):
        raise error_factory("SOURCE_AUTHORITY_MISMATCH", "replay sources must be an array")
    actual = [_source_identity(record) for record in sources]
    unknown = sorted(set(actual) - allowed)
    if unknown:
        raise error_factory(
            "SOURCE_AUTHORITY_MISMATCH",
            f"replay references source identities outside the frozen authority: {unknown}",
        )


def _source_identity(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("source authority record must be an object")
    required = {"classification", "path", "sha256"}
    if not required <= set(value):
        raise ValueError("source authority record must contain classification, path and sha256")
    classification = value.get("classification")
    path = value.get("path")
    sha256 = value.get("sha256")
    if not all(isinstance(item, str) and item for item in (classification, path, sha256)):
        raise ValueError("source authority record values must be non-empty strings")
    return path, sha256, classification

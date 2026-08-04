from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "contracts" / "registry.json"
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def load_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = (path or DEFAULT_REGISTRY_PATH).resolve(strict=True)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "techguytool-huawei.contract-registry.v1":
        raise ValueError("unsupported contract registry schema")
    if payload.get("registry_version") != 1:
        raise ValueError("unsupported contract registry version")
    return payload


def canonical_json(value: Any) -> str:
    reject_non_json_numbers(value, path="$")
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_timestamp(value: str) -> datetime:
    if not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def try_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return parse_timestamp(value)
    except ValueError:
        return None


def reject_non_json_numbers(value: Any, *, path: str) -> None:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite number at {path}")
        raise ValueError(f"floating-point number is forbidden at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            reject_non_json_numbers(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_non_json_numbers(child, path=f"{path}[{index}]")

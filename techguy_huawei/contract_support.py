from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "contracts" / "registry.json"
_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

_REGISTRY_SCHEMA = "techguytool-huawei.contract-registry.v1"
_REGISTRY_TOP_LEVEL = {
    "canonical_json",
    "contracts",
    "envelope",
    "registry_version",
    "schema",
}
_CANONICAL_JSON_KEYS = {"array_order", "encoding", "numbers", "object_keys", "whitespace"}
_ENVELOPE_KEYS = {"required", "fields"}
_DEFINITION_REQUIRED = {
    "authority",
    "expiry",
    "payload_fields",
    "payload_required",
    "physical_session",
    "single_use",
}
_DEFINITION_ALLOWED = _DEFINITION_REQUIRED | {"dangerous_auto_promotion", "timestamp_order"}
_FIELD_ALLOWED = {
    "const",
    "enum",
    "format",
    "items",
    "max_items",
    "max_length",
    "maximum",
    "min_items",
    "min_length",
    "minimum",
    "nullable",
    "pattern",
    "sorted_unique",
    "type",
}
_FIELD_TYPES = {"array", "boolean", "integer", "object", "string"}
_FIELD_FORMATS = {"semver", "sha256", "timestamp", "uuid"}
_PHYSICAL_SESSION_POLICIES = {"forbidden", "optional", "required"}
_EXPIRY_POLICIES = {"forbidden", "optional", "required"}


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load and fully validate the reviewed contract registry."""

    registry_path = (path or DEFAULT_REGISTRY_PATH).resolve(strict=True)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    return validate_registry(payload)


def validate_registry(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a registry mapping at every authority boundary and return a copy."""

    if not isinstance(payload, Mapping):
        raise ValueError("contract registry must be an object")
    registry = dict(payload)
    _reject_unknown_or_missing(
        registry,
        required=_REGISTRY_TOP_LEVEL,
        allowed=_REGISTRY_TOP_LEVEL,
        path="$registry",
    )
    if registry["schema"] != _REGISTRY_SCHEMA:
        raise ValueError("unsupported contract registry schema")
    if registry["registry_version"] != 1:
        raise ValueError("unsupported contract registry version")

    canonical = _require_mapping(registry["canonical_json"], "$registry.canonical_json")
    _reject_unknown_or_missing(
        canonical,
        required=_CANONICAL_JSON_KEYS,
        allowed=_CANONICAL_JSON_KEYS,
        path="$registry.canonical_json",
    )
    expected_canonical = {
        "array_order": "preserved",
        "encoding": "utf-8",
        "numbers": "json-integer-only",
        "object_keys": "lexicographic",
        "whitespace": "none",
    }
    if canonical != expected_canonical:
        raise ValueError("unsupported canonical JSON policy")

    envelope = _require_mapping(registry["envelope"], "$registry.envelope")
    _reject_unknown_or_missing(
        envelope,
        required=_ENVELOPE_KEYS,
        allowed=_ENVELOPE_KEYS,
        path="$registry.envelope",
    )
    envelope_required = _require_string_list(
        envelope["required"], "$registry.envelope.required", allow_empty=False
    )
    envelope_fields = _require_mapping(envelope["fields"], "$registry.envelope.fields")
    if not envelope_fields:
        raise ValueError("$registry.envelope.fields must not be empty")
    for name, spec in envelope_fields.items():
        if not isinstance(name, str) or not name:
            raise ValueError("$registry.envelope.fields keys must be non-empty strings")
        _validate_field_spec(spec, f"$registry.envelope.fields.{name}")
    missing_envelope_specs = sorted(set(envelope_required) - set(envelope_fields))
    if missing_envelope_specs:
        raise ValueError(
            "$registry.envelope.required references undefined fields: "
            + ", ".join(missing_envelope_specs)
        )

    contracts = _require_mapping(registry["contracts"], "$registry.contracts")
    if not contracts:
        raise ValueError("$registry.contracts must not be empty")
    for contract_type, definition in contracts.items():
        if not isinstance(contract_type, str) or not contract_type:
            raise ValueError("$registry.contracts keys must be non-empty strings")
        _validate_contract_definition(definition, f"$registry.contracts.{contract_type}")

    contract_type_spec = envelope_fields.get("contract_type")
    if not isinstance(contract_type_spec, Mapping):
        raise ValueError("$registry.envelope.fields.contract_type is required")
    contract_type_enum = contract_type_spec.get("enum")
    if not isinstance(contract_type_enum, list) or set(contract_type_enum) != set(contracts):
        raise ValueError("contract_type enum must exactly match registered contracts")

    return registry


def canonical_json(value: Any) -> str:
    """Return strict canonical UTF-8 JSON or fail on unsupported values."""

    reject_non_json_numbers(value, path="$")
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return canonical.encode("utf-8", errors="strict").decode("utf-8", errors="strict")


def canonical_sha256(value: Any) -> str:
    """Hash strict canonical UTF-8 JSON."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_timestamp(value: str) -> datetime:
    """Parse the frozen UTC timestamp form used by shared contracts."""

    if not _TIMESTAMP_RE.fullmatch(value):
        raise ValueError("timestamp must use YYYY-MM-DDTHH:MM:SSZ")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def try_timestamp(value: Any) -> datetime | None:
    """Return a parsed timestamp when the value is valid, otherwise None."""

    if not isinstance(value, str):
        return None
    try:
        return parse_timestamp(value)
    except ValueError:
        return None


def reject_non_json_numbers(value: Any, *, path: str) -> None:
    """Reject floats and non-finite numbers from the shared canonical domain."""

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


def _validate_contract_definition(value: Any, path: str) -> None:
    definition = _require_mapping(value, path)
    _reject_unknown_or_missing(
        definition,
        required=_DEFINITION_REQUIRED,
        allowed=_DEFINITION_ALLOWED,
        path=path,
    )
    if not isinstance(definition["authority"], str) or not definition["authority"]:
        raise ValueError(f"{path}.authority must be a non-empty string")
    if definition["physical_session"] not in _PHYSICAL_SESSION_POLICIES:
        raise ValueError(f"{path}.physical_session has an unsupported policy")
    if definition["expiry"] not in _EXPIRY_POLICIES:
        raise ValueError(f"{path}.expiry has an unsupported policy")
    if not isinstance(definition["single_use"], bool):
        raise ValueError(f"{path}.single_use must be boolean")
    if "dangerous_auto_promotion" in definition and not isinstance(
        definition["dangerous_auto_promotion"], bool
    ):
        raise ValueError(f"{path}.dangerous_auto_promotion must be boolean")

    required = _require_string_list(
        definition["payload_required"], f"{path}.payload_required", allow_empty=False
    )
    fields = _require_mapping(definition["payload_fields"], f"{path}.payload_fields")
    if not fields:
        raise ValueError(f"{path}.payload_fields must not be empty")
    for name, spec in fields.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{path}.payload_fields keys must be non-empty strings")
        _validate_field_spec(spec, f"{path}.payload_fields.{name}")
    missing_specs = sorted(set(required) - set(fields))
    if missing_specs:
        raise ValueError(
            f"{path}.payload_required references undefined fields: " + ", ".join(missing_specs)
        )

    timestamp_order = definition.get("timestamp_order", [])
    if not isinstance(timestamp_order, list):
        raise ValueError(f"{path}.timestamp_order must be an array")
    for index, pair in enumerate(timestamp_order):
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or not all(isinstance(name, str) for name in pair)
        ):
            raise ValueError(f"{path}.timestamp_order[{index}] must contain two field names")
        if pair[0] not in fields or pair[1] not in fields:
            raise ValueError(f"{path}.timestamp_order[{index}] references undefined fields")


def _validate_field_spec(value: Any, path: str) -> None:
    spec = _require_mapping(value, path)
    _reject_unknown_or_missing(spec, required={"type"}, allowed=_FIELD_ALLOWED, path=path)
    field_type = spec["type"]
    if field_type not in _FIELD_TYPES:
        raise ValueError(f"{path}.type is unsupported")
    if "nullable" in spec and not isinstance(spec["nullable"], bool):
        raise ValueError(f"{path}.nullable must be boolean")
    if "sorted_unique" in spec and not isinstance(spec["sorted_unique"], bool):
        raise ValueError(f"{path}.sorted_unique must be boolean")
    if "format" in spec and spec["format"] not in _FIELD_FORMATS:
        raise ValueError(f"{path}.format is unsupported")
    if "pattern" in spec:
        if not isinstance(spec["pattern"], str):
            raise ValueError(f"{path}.pattern must be a string")
        try:
            re.compile(spec["pattern"])
        except re.error as exc:
            raise ValueError(f"{path}.pattern is invalid: {exc}") from exc
    if "enum" in spec and (not isinstance(spec["enum"], list) or not spec["enum"]):
        raise ValueError(f"{path}.enum must be a non-empty array")

    for key in ("minimum", "maximum", "min_length", "max_length", "min_items", "max_items"):
        if key in spec and (not isinstance(spec[key], int) or isinstance(spec[key], bool)):
            raise ValueError(f"{path}.{key} must be an integer")
    for key in ("min_length", "max_length", "min_items", "max_items"):
        if key in spec and spec[key] < 0:
            raise ValueError(f"{path}.{key} must be non-negative")
    for lower, upper in (
        ("minimum", "maximum"),
        ("min_length", "max_length"),
        ("min_items", "max_items"),
    ):
        if lower in spec and upper in spec and spec[lower] > spec[upper]:
            raise ValueError(f"{path}.{lower} must not exceed {upper}")

    if field_type == "array":
        if "items" not in spec:
            raise ValueError(f"{path}.items is required for arrays")
        _validate_field_spec(spec["items"], f"{path}.items")
    elif "items" in spec:
        raise ValueError(f"{path}.items is valid only for arrays")


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return dict(value)


def _require_string_list(value: Any, path: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{path} must be an array of non-empty strings")
    if not allow_empty and not value:
        raise ValueError(f"{path} must not be empty")
    if len(value) != len(set(value)):
        raise ValueError(f"{path} must not contain duplicates")
    return list(value)


def _reject_unknown_or_missing(
    value: Mapping[str, Any],
    *,
    required: set[str],
    allowed: set[str],
    path: str,
) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise ValueError(f"{path} contains unknown members: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{path} is missing required members: {', '.join(missing)}")

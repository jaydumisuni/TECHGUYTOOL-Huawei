from __future__ import annotations

import re
from typing import Any, Mapping

from .contract_models import ContractError
from .contract_support import SHA256_RE, SEMVER_RE, UUID_RE, canonical_json, parse_timestamp

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1


def validate_field(
    value: Any,
    spec: Mapping[str, Any],
    *,
    path: str,
    errors: list[ContractError],
) -> None:
    """Validate one value against a reviewed registry field specification."""

    if value is None:
        if not spec.get("nullable", False):
            errors.append(ContractError("INVALID_FIELD_TYPE", path, "null is not permitted"))
        return
    field_type = spec.get("type")
    type_valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(field_type)
    if type_valid is None:
        errors.append(
            ContractError(
                "INVALID_REGISTRY_FIELD_TYPE",
                path,
                f"unknown registry type {field_type!r}",
            )
        )
        return
    if not type_valid:
        errors.append(
            ContractError(
                "INVALID_FIELD_TYPE",
                path,
                f"expected {field_type}, got {type(value).__name__}",
            )
        )
        return
    if "const" in spec and value != spec["const"]:
        code = (
            "UNSUPPORTED_SCHEMA_VERSION"
            if path == "$.schema_version"
            else "CONST_VALUE_MISMATCH"
        )
        errors.append(ContractError(code, path, f"value must equal {spec['const']!r}"))
    if "enum" in spec and value not in spec["enum"]:
        errors.append(
            ContractError("ENUM_VALUE_INVALID", path, f"value {value!r} is not permitted")
        )
    if field_type == "string":
        _validate_string(value, spec, path, errors)
    elif field_type == "integer":
        _validate_integer(value, spec, path, errors)
    elif field_type == "array":
        _validate_array(value, spec, path, errors)


def _validate_integer(
    value: int,
    spec: Mapping[str, Any],
    path: str,
    errors: list[ContractError],
) -> None:
    if value < _I64_MIN or value > _I64_MAX:
        errors.append(
            ContractError(
                "INTEGER_OUT_OF_RANGE",
                path,
                "integer exceeds signed 64-bit contract range",
            )
        )
        return
    minimum, maximum = spec.get("minimum"), spec.get("maximum")
    if (minimum is not None and value < minimum) or (
        maximum is not None and value > maximum
    ):
        errors.append(
            ContractError(
                "INTEGER_OUT_OF_RANGE",
                path,
                f"integer must be between {minimum} and {maximum}",
            )
        )


def _validate_string(
    value: str,
    spec: Mapping[str, Any],
    path: str,
    errors: list[ContractError],
) -> None:
    minimum, maximum = spec.get("min_length"), spec.get("max_length")
    if (minimum is not None and len(value) < minimum) or (
        maximum is not None and len(value) > maximum
    ):
        errors.append(
            ContractError(
                "STRING_LENGTH_OUT_OF_RANGE",
                path,
                f"string length must be between {minimum} and {maximum}",
            )
        )
    pattern = spec.get("pattern")
    if pattern and re.fullmatch(pattern, value) is None:
        errors.append(
            ContractError(
                "STRING_PATTERN_MISMATCH",
                path,
                "string does not match required pattern",
            )
        )
    fmt = spec.get("format")
    if fmt == "uuid" and UUID_RE.fullmatch(value) is None:
        errors.append(
            ContractError(
                "INVALID_UUID", path, "value is not a canonical lowercase UUID"
            )
        )
    elif fmt == "sha256" and SHA256_RE.fullmatch(value) is None:
        errors.append(
            ContractError(
                "INVALID_SHA256", path, "value is not a lowercase SHA-256 digest"
            )
        )
    elif fmt == "timestamp":
        try:
            parse_timestamp(value)
        except ValueError as exc:
            errors.append(ContractError("INVALID_TIMESTAMP", path, str(exc)))
    elif fmt == "semver" and SEMVER_RE.fullmatch(value) is None:
        errors.append(
            ContractError("INVALID_SEMVER", path, "value must use MAJOR.MINOR.PATCH")
        )


def _validate_array(
    value: list[Any],
    spec: Mapping[str, Any],
    path: str,
    errors: list[ContractError],
) -> None:
    minimum, maximum = spec.get("min_items"), spec.get("max_items")
    if (minimum is not None and len(value) < minimum) or (
        maximum is not None and len(value) > maximum
    ):
        errors.append(
            ContractError(
                "ARRAY_LENGTH_OUT_OF_RANGE",
                path,
                f"array length must be between {minimum} and {maximum}",
            )
        )
    before = len(errors)
    item_spec = spec.get("items")
    if not isinstance(item_spec, Mapping):
        errors.append(
            ContractError(
                "INVALID_REGISTRY_FIELD_TYPE",
                path,
                "array field specification is missing items",
            )
        )
        return
    for index, child in enumerate(value):
        validate_field(child, item_spec, path=f"{path}[{index}]", errors=errors)
    if spec.get("sorted_unique") and len(errors) == before:
        canonical_items = [canonical_json(child) for child in value]
        if canonical_items != sorted(set(canonical_items)):
            code = (
                "HASH_LIST_NOT_SORTED_UNIQUE"
                if item_spec.get("format") == "sha256"
                else "ARRAY_NOT_SORTED_UNIQUE"
            )
            errors.append(
                ContractError(
                    code, path, "array must be lexicographically sorted and unique"
                )
            )

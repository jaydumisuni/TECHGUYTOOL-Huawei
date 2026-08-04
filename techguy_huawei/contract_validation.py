from __future__ import annotations

import hashlib
import json
from datetime import UTC
from typing import Any, Mapping, Sequence

from .contract_fields import validate_field
from .contract_models import ContractError, ValidationContext, ValidationResult
from .contract_support import (
    canonical_json,
    load_registry,
    parse_timestamp,
    try_timestamp,
    validate_registry,
)

_DANGEROUS_LEARNING_KINDS = {
    "write_target",
    "write_offset",
    "destructive_recipe",
    "expanded_authority",
}


def validate_contract(
    document: Mapping[str, Any] | str | bytes,
    *,
    context: ValidationContext | Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> ValidationResult:
    """Validate one shared contract against the frozen authority registry."""

    try:
        value = _decode_document(document)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        return ValidationResult(
            ok=False,
            errors=(ContractError("MALFORMED_JSON", "$", str(exc)),),
        )
    if not isinstance(value, dict):
        return ValidationResult(
            ok=False,
            errors=(
                ContractError(
                    "INVALID_DOCUMENT_TYPE", "$", "contract document must be an object"
                ),
            ),
        )

    try:
        active_registry = load_registry() if registry is None else validate_registry(registry)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return ValidationResult(
            ok=False,
            errors=(ContractError("REGISTRY_UNAVAILABLE", "$registry", str(exc)),),
        )

    try:
        active_context = (
            context
            if isinstance(context, ValidationContext)
            else ValidationContext.from_mapping(context)
        )
    except (TypeError, ValueError) as exc:
        return ValidationResult(
            ok=False,
            errors=(
                ContractError("INVALID_VALIDATION_CONTEXT", "$context", str(exc)),
            ),
        )

    errors: list[ContractError] = []
    envelope = active_registry["envelope"]
    required = list(envelope["required"])
    field_specs = dict(envelope["fields"])
    for name in required:
        if name not in value:
            errors.append(
                ContractError(
                    "MISSING_TOP_LEVEL_FIELD",
                    f"$.{name}",
                    f"required top-level field {name!r} is missing",
                )
            )
    for name in sorted(set(value) - set(field_specs)):
        errors.append(
            ContractError(
                "UNKNOWN_TOP_LEVEL_FIELD",
                f"$.{name}",
                f"unknown top-level field {name!r}",
            )
        )
    for name in sorted(set(value) & set(field_specs)):
        validate_field(value[name], field_specs[name], path=f"$.{name}", errors=errors)

    contract_type = value.get("contract_type")
    definition = None
    if isinstance(contract_type, str):
        definition = active_registry.get("contracts", {}).get(contract_type)
        if definition is None:
            errors.append(
                ContractError(
                    "UNKNOWN_CONTRACT_TYPE",
                    "$.contract_type",
                    f"contract type {contract_type!r} is not registered",
                )
            )
    if definition is not None:
        _validate_definition(value, definition, errors)
        _validate_context(value, active_context, errors)
    _validate_envelope(value, active_context, errors)

    ordered = tuple(sorted(set(errors)))
    if ordered:
        return ValidationResult(ok=False, errors=ordered)
    try:
        canonical = canonical_json(value)
    except (TypeError, ValueError, UnicodeError) as exc:
        return ValidationResult(
            ok=False,
            errors=(ContractError("NON_CANONICAL_JSON_VALUE", "$", str(exc)),),
        )
    return ValidationResult(
        ok=True,
        canonical=canonical,
        sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _decode_document(document: Mapping[str, Any] | str | bytes) -> Any:
    if isinstance(document, Mapping):
        return dict(document)
    if isinstance(document, bytes):
        document = document.decode("utf-8")
    if isinstance(document, str):
        return json.loads(document)
    raise TypeError("contract input must be an object, JSON string, or UTF-8 bytes")


def _validate_definition(
    document: Mapping[str, Any],
    definition: Mapping[str, Any],
    errors: list[ContractError],
) -> None:
    if document.get("authority") != definition.get("authority"):
        errors.append(
            ContractError(
                "AUTHORITY_MISMATCH",
                "$.authority",
                f"contract requires authority {definition.get('authority')!r}",
            )
        )
    policy, session = definition.get("physical_session"), document.get(
        "physical_session_id"
    )
    if policy == "required" and session is None:
        errors.append(
            ContractError(
                "PHYSICAL_SESSION_REQUIRED",
                "$.physical_session_id",
                "physical session is required",
            )
        )
    elif policy == "forbidden" and session is not None:
        errors.append(
            ContractError(
                "PHYSICAL_SESSION_FORBIDDEN",
                "$.physical_session_id",
                "physical session is forbidden",
            )
        )
    expiry_policy, expires_at = definition.get("expiry"), document.get("expires_at")
    if expiry_policy == "required" and expires_at is None:
        errors.append(
            ContractError("EXPIRY_REQUIRED", "$.expires_at", "expiry is required")
        )
    elif expiry_policy == "forbidden" and expires_at is not None:
        errors.append(
            ContractError("EXPIRY_FORBIDDEN", "$.expires_at", "expiry is forbidden")
        )
    expected_single = bool(definition.get("single_use", False))
    if document.get("single_use") is not expected_single:
        errors.append(
            ContractError(
                "SINGLE_USE_MISMATCH",
                "$.single_use",
                f"contract requires single_use={expected_single}",
            )
        )

    payload = document.get("payload")
    if not isinstance(payload, dict):
        return
    field_specs = definition.get("payload_fields", {})
    required = definition.get("payload_required", [])
    for name in required:
        if name not in payload:
            errors.append(
                ContractError(
                    "MISSING_PAYLOAD_FIELD",
                    f"$.payload.{name}",
                    f"required payload field {name!r} is missing",
                )
            )
        )
    for name in sorted(set(payload) - set(field_specs)):
        errors.append(
            ContractError(
                "UNKNOWN_PAYLOAD_FIELD",
                f"$.payload.{name}",
                f"unknown payload field {name!r}",
            )
        )
    for name in sorted(set(payload) & set(field_specs)):
        validate_field(
            payload[name],
            field_specs[name],
            path=f"$.payload.{name}",
            errors=errors,
        )
    for earlier_name, later_name in definition.get("timestamp_order", []):
        earlier, later = payload.get(earlier_name), payload.get(later_name)
        try:
            if (
                isinstance(earlier, str)
                and isinstance(later, str)
                and parse_timestamp(later) < parse_timestamp(earlier)
            ):
                errors.append(
                    ContractError(
                        "TIMESTAMP_ORDER_INVALID",
                        f"$.payload.{later_name}",
                        f"{later_name} must not precede {earlier_name}",
                    )
                )
        except ValueError:
            pass
    if definition.get("dangerous_auto_promotion"):
        kind = payload.get("change_kind")
        if kind in _DANGEROUS_LEARNING_KINDS and payload.get(
            "auto_promotion_allowed"
        ) is True:
            errors.append(
                ContractError(
                    "DANGEROUS_AUTO_PROMOTION_FORBIDDEN",
                    "$.payload.auto_promotion_allowed",
                    f"{kind} can never be promoted automatically",
                )
            )


def _validate_envelope(
    document: Mapping[str, Any],
    context: ValidationContext,
    errors: list[ContractError],
) -> None:
    created = try_timestamp(document.get("created_at"))
    expires = try_timestamp(document.get("expires_at"))
    consumed = try_timestamp(document.get("consumed_at"))
    now = context.now.astimezone(UTC) if context.now is not None else None
    if created is not None and now is not None and created > now:
        errors.append(
            ContractError(
                "CREATED_AT_IN_FUTURE",
                "$.created_at",
                "created_at is later than validation time",
            )
        )
    if created is not None and expires is not None and expires <= created:
        errors.append(
            ContractError(
                "EXPIRY_NOT_AFTER_CREATED",
                "$.expires_at",
                "expires_at must be later than created_at",
            )
        )
    if expires is not None and now is not None and expires <= now:
        errors.append(
            ContractError("CONTRACT_EXPIRED", "$.expires_at", "contract has expired")
        )
    if consumed is None:
        return
    if document.get("single_use") is not True:
        errors.append(
            ContractError(
                "CONSUMED_AT_FORBIDDEN",
                "$.consumed_at",
                "only single-use contracts may be consumed",
            )
        )
    if created is not None and consumed < created:
        errors.append(
            ContractError(
                "CONSUMED_AT_INVALID",
                "$.consumed_at",
                "consumed_at precedes created_at",
            )
        )
    if document.get("single_use") is True and not context.allow_consumed:
        errors.append(
            ContractError(
                "SINGLE_USE_CONTRACT_ALREADY_CONSUMED",
                "$.consumed_at",
                "single-use contract has already been consumed",
            )
        )


def _validate_context(
    document: Mapping[str, Any],
    context: ValidationContext,
    errors: list[ContractError],
) -> None:
    if (
        context.expected_contract_type is not None
        and document.get("contract_type") != context.expected_contract_type
    ):
        errors.append(
            ContractError(
                "CONTRACT_TYPE_MISMATCH",
                "$.contract_type",
                "contract type does not match validation context",
            )
        )
    if (
        context.expected_physical_session_id is not None
        and document.get("physical_session_id")
        != context.expected_physical_session_id
    ):
        errors.append(
            ContractError(
                "PHYSICAL_SESSION_MISMATCH",
                "$.physical_session_id",
                "physical session does not match validation context",
            )
        )
    if (
        context.expected_authority is not None
        and document.get("authority") != context.expected_authority
    ):
        errors.append(
            ContractError(
                "AUTHORITY_CONTEXT_MISMATCH",
                "$.authority",
                "authority does not match validation context",
            )
        )
    payload = document.get("payload")
    if not isinstance(payload, dict):
        return
    if (
        context.expected_recipe_hash is not None
        and payload.get("recipe_hash") != context.expected_recipe_hash
    ):
        errors.append(
            ContractError(
                "RECIPE_HASH_MISMATCH",
                "$.payload.recipe_hash",
                "recipe hash does not match validation context",
            )
        )
    if context.expected_artifact_hashes is None:
        return
    actual: Sequence[str] | None
    if document.get("contract_type") == "execution_lease":
        candidate = payload.get("artifact_hashes")
        actual = candidate if isinstance(candidate, list) else None
    elif document.get("contract_type") == "artifact_manifest":
        candidate = payload.get("sha256")
        actual = [candidate] if isinstance(candidate, str) else None
    else:
        actual = None
    if actual is None or tuple(actual) != tuple(context.expected_artifact_hashes):
        errors.append(
            ContractError(
                "ARTIFACT_HASH_MISMATCH",
                "$.payload",
                "artifact hashes do not match validation context",
            )
        )

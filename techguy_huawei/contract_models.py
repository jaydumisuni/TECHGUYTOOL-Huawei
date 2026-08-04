from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from .contract_support import parse_timestamp

_CONTEXT_FIELDS = {
    "allow_consumed",
    "expected_artifact_hashes",
    "expected_authority",
    "expected_contract_type",
    "expected_physical_session_id",
    "expected_recipe_hash",
    "now",
}


@dataclass(frozen=True, order=True)
class ContractError:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return the stable wire representation for one validation error."""

        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class ValidationContext:
    now: datetime | None = None
    expected_contract_type: str | None = None
    expected_physical_session_id: str | None = None
    expected_recipe_hash: str | None = None
    expected_artifact_hashes: tuple[str, ...] | None = None
    expected_authority: str | None = None
    allow_consumed: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "ValidationContext":
        """Build a fail-closed validation context from its wire mapping."""

        if value is None:
            return cls()
        if not isinstance(value, Mapping):
            raise TypeError("validation context must be an object")
        unknown = sorted(set(value) - _CONTEXT_FIELDS)
        if unknown:
            raise TypeError(f"unknown validation context fields: {', '.join(unknown)}")

        now = value.get("now")
        if isinstance(now, str):
            try:
                now = parse_timestamp(now)
            except ValueError as exc:
                raise TypeError(
                    "context.now must use YYYY-MM-DDTHH:MM:SSZ"
                ) from exc
        elif now is not None and not isinstance(now, datetime):
            raise TypeError("context.now must be an RFC3339 UTC string or datetime")
        if isinstance(now, datetime) and now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        string_fields = {
            "expected_contract_type": value.get("expected_contract_type"),
            "expected_physical_session_id": value.get("expected_physical_session_id"),
            "expected_recipe_hash": value.get("expected_recipe_hash"),
            "expected_authority": value.get("expected_authority"),
        }
        for name, candidate in string_fields.items():
            if candidate is not None and not isinstance(candidate, str):
                raise TypeError(f"context.{name} must be a string or null")

        artifacts = value.get("expected_artifact_hashes")
        if artifacts is not None:
            if (
                not isinstance(artifacts, list)
                or not all(isinstance(item, str) for item in artifacts)
            ):
                raise TypeError("context.expected_artifact_hashes must be an array of strings")
            artifacts = tuple(artifacts)

        allow_consumed = value.get("allow_consumed", False)
        if not isinstance(allow_consumed, bool):
            raise TypeError("context.allow_consumed must be boolean")

        return cls(
            now=now,
            expected_contract_type=string_fields["expected_contract_type"],
            expected_physical_session_id=string_fields[
                "expected_physical_session_id"
            ],
            expected_recipe_hash=string_fields["expected_recipe_hash"],
            expected_artifact_hashes=artifacts,
            expected_authority=string_fields["expected_authority"],
            allow_consumed=allow_consumed,
        )


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[ContractError, ...] = field(default_factory=tuple)
    canonical: str | None = None
    sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the stable validation result used by Python/Rust proofs."""

        payload: dict[str, Any] = {
            "ok": self.ok,
            "errors": [error.as_dict() for error in self.errors],
        }
        if self.ok:
            payload["canonical"] = self.canonical
            payload["sha256"] = self.sha256
        return payload

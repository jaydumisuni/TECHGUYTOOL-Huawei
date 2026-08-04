from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from .contract_support import parse_timestamp


@dataclass(frozen=True, order=True)
class ContractError:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
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
        if not value:
            return cls()
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
        artifacts = value.get("expected_artifact_hashes")
        return cls(
            now=now,
            expected_contract_type=value.get("expected_contract_type"),
            expected_physical_session_id=value.get("expected_physical_session_id"),
            expected_recipe_hash=value.get("expected_recipe_hash"),
            expected_artifact_hashes=None if artifacts is None else tuple(artifacts),
            expected_authority=value.get("expected_authority"),
            allow_consumed=bool(value.get("allow_consumed", False)),
        )


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[ContractError, ...] = field(default_factory=tuple)
    canonical: str | None = None
    sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "errors": [error.as_dict() for error in self.errors],
        }
        if self.ok:
            payload["canonical"] = self.canonical
            payload["sha256"] = self.sha256
        return payload

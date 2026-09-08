from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256


class RecoveryAuthorizationError(ValueError):
    pass


class AuthorizationMode(str, Enum):
    H = "H"
    E = "E"


def _digest(value: str | bytes) -> str:
    raw=value if isinstance(value,bytes) else value.encode("utf-8",errors="strict")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class OfficialAuthorizationMaterial:
    mode: AuthorizationMode
    payload: bytes
    source_ref: str
    device_id_sha256: str
    update_token_sha256: str
    payload_sha256: str

    @classmethod
    def create(
        cls,
        *,
        mode: AuthorizationMode,
        payload: bytes,
        source_ref: str,
        device_id: str,
        update_token: str,
    ) -> "OfficialAuthorizationMaterial":
        if not payload:
            raise RecoveryAuthorizationError("AUTH_PAYLOAD_REQUIRED")
        if not source_ref.startswith("huawei://query.hicloud.com/"):
            raise RecoveryAuthorizationError("AUTH_SOURCE_NOT_OFFICIAL")
        if not device_id or not update_token:
            raise RecoveryAuthorizationError("AUTH_DEVICE_AUTHORITY_REQUIRED")
        return cls(
            mode=mode,
            payload=bytes(payload),
            source_ref=source_ref,
            device_id_sha256=_digest(device_id),
            update_token_sha256=_digest(update_token),
            payload_sha256=_digest(payload),
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "source_ref": self.source_ref,
            "device_id_sha256": self.device_id_sha256,
            "update_token_sha256": self.update_token_sha256,
            "payload_sha256": self.payload_sha256,
        }


@dataclass(frozen=True, slots=True)
class HuaweiAuthorizationProviderContract:
    check_endpoint: str
    authorize_endpoint: str
    device_fields: tuple[str, ...]
    pki_fields: tuple[str, ...]
    request_schema_certified: bool
    ready: bool
    blockers: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return asdict(self)


def observed_huawei_authorization_provider() -> HuaweiAuthorizationProviderContract:
    return HuaweiAuthorizationProviderContract(
        check_endpoint="https://query.hicloud.com/BL/v1/CheckAndAuthorize",
        authorize_endpoint="https://query.hicloud.com/BL/v1/Authorize",
        device_fields=("device_id","update_token"),
        pki_fields=("device_certificate","key_attestantion"),
        request_schema_certified=False,
        ready=False,
        blockers=("REQUEST_SCHEMA_NOT_CERTIFIED", "LIVE_PROVIDER_PROOF_PENDING"),
    )


def build_system_update_auth_frame(material: OfficialAuthorizationMaterial) -> bytes:
    return material.mode.value.encode("ascii") + material.payload


def system_update_auth_accepted(response: bytes) -> bool:
    return bool(response) and response[0] == 0x02

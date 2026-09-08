from __future__ import annotations

from dataclasses import asdict, dataclass

from .native_recovery_transport import TransportCapability, TransportStatus
from .recovery_identity import RecoveryIdentity, RecoveryIdentityStatus
from .recovery_packages import RecoveryPackageSet


DESTRUCTIVE_WARNING = (
    "Native Huawei System Recovery writes stock recovery/system firmware and may erase user data. "
    "Bootloader unlock is not part of this workflow."
)


@dataclass(frozen=True, slots=True)
class RecoveryReadiness:
    family: str | None
    build: str | None
    android_major: int | None
    board_id: str | None
    lock_state: str | None
    identity_status: str
    model: str | None
    region: str | None
    preload_region: str | None
    package_ready: bool
    package_roles: tuple[str, ...]
    anti_rollback_state: str
    transport_id: str
    transport_status: str
    official_authorization_ready: bool
    start_enabled: bool
    blockers: tuple[str, ...]
    destructive_warning: str

    def to_public_dict(self) -> dict[str, object]:
        return asdict(self)


def build_recovery_readiness(
    identity: RecoveryIdentity,
    package_set: RecoveryPackageSet | None,
    transport: TransportCapability,
    *,
    official_authorization_ready: bool,
) -> RecoveryReadiness:
    blockers: list[str] = []
    if identity.status is not RecoveryIdentityStatus.READY:
        blockers.append("IDENTITY_NOT_READY")

    package_ready = package_set is not None and package_set.ready
    package_roles = tuple(sorted(package_set.artifacts)) if package_set is not None else ()
    anti_rollback_state = package_set.anti_rollback_state if package_set is not None else "unresolved"
    if not package_ready:
        blockers.append("PACKAGE_SET_NOT_READY")

    transport_ready = (
        transport.status is TransportStatus.HARDWARE_CERTIFIED
        and transport.write_certified
    )
    if not transport_ready:
        blockers.append("TRANSPORT_NOT_CERTIFIED")

    if official_authorization_ready is not True:
        blockers.append("OFFICIAL_AUTHORIZATION_NOT_READY")

    return RecoveryReadiness(
        family=identity.family,
        build=identity.build,
        android_major=identity.android_major,
        board_id=identity.board_id,
        lock_state=identity.lock_state,
        identity_status=identity.status.value,
        model=identity.model,
        region=identity.region,
        preload_region=identity.preload_region,
        package_ready=package_ready,
        package_roles=package_roles,
        anti_rollback_state=anti_rollback_state,
        transport_id=transport.transport_id,
        transport_status=transport.status.value,
        official_authorization_ready=official_authorization_ready,
        start_enabled=not blockers,
        blockers=tuple(blockers),
        destructive_warning=DESTRUCTIVE_WARNING,
    )

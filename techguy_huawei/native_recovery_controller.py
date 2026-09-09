from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .native_recovery_readiness import RecoveryReadiness, build_recovery_readiness
from .native_recovery_transport import TransportCapability, probe_transport_capability
from .recovery_identity import RecoveryIdentity
from .recovery_packages import (
    ROLES,
    RecoveryPackageArtifact,
    RecoveryPackageError,
    RecoveryPackageSet,
    inspect_recovery_package,
    resolve_recovery_package_set,
)


class NativeRecoveryController:
    package_roles=("base","cust","preload")

    def __init__(
        self,
        identity_provider: Callable[[], RecoveryIdentity],
        *,
        transport_provider: Callable[[], TransportCapability] | None = None,
    ) -> None:
        self._identity_provider=identity_provider
        self._transport_provider=transport_provider
        self._package_inputs: dict[str,tuple[str,str]]={}
        self._package_artifacts: dict[str,RecoveryPackageArtifact]={}
        self._anti_rollback_state="unresolved"
        self._official_authorization_ready=False
        self._last_package_error: str | None=None
        self._last_identity: RecoveryIdentity | None=None
        self._last_package_set: RecoveryPackageSet | None=None
        self._last_readiness: RecoveryReadiness | None=None

    def set_package(self, role: str, path: str, authority_label: str) -> None:
        role=role.strip().lower()
        if role not in ROLES:
            raise ValueError("RECOVERY_PACKAGE_ROLE_INVALID")
        self._package_inputs[role]=(path,authority_label)
        self._package_artifacts.pop(role,None)
        self._last_package_set=None
        self._last_package_error=None

    def set_anti_rollback_state(self, state: str) -> None:
        self._anti_rollback_state=str(state)

    def set_official_authorization_ready(self, ready: bool) -> None:
        self._official_authorization_ready=ready is True

    def _transport(self, identity: RecoveryIdentity) -> TransportCapability:
        if self._transport_provider is not None:
            return self._transport_provider()
        return probe_transport_capability(identity,{"normal_fastboot":True})

    def _inspect_packages(self, identity: RecoveryIdentity) -> RecoveryPackageSet | None:
        self._last_package_error=None
        if set(self._package_inputs)!=set(ROLES):
            return None
        try:
            artifacts={}
            for role in self.package_roles:
                path,label=self._package_inputs[role]
                artifacts[role]=inspect_recovery_package(path,role,authority_label=label)
            self._package_artifacts=artifacts
            return resolve_recovery_package_set(
                identity,artifacts.values(),anti_rollback_state=self._anti_rollback_state
            )
        except RecoveryPackageError as exc:
            self._last_package_error=str(exc)
            return None

    def preflight(self) -> RecoveryReadiness:
        identity=self._identity_provider()
        package_set=self._inspect_packages(identity)
        readiness=build_recovery_readiness(
            identity,package_set,self._transport(identity),
            official_authorization_ready=self._official_authorization_ready,
        )
        self._last_identity=identity
        self._last_package_set=package_set
        self._last_readiness=readiness
        return readiness

    def package_public_state(self) -> dict[str,dict[str,object]]:
        state: dict[str,dict[str,object]]={}
        for role in self.package_roles:
            selected=role in self._package_inputs
            path,label=self._package_inputs.get(role,("",""))
            artifact=self._package_artifacts.get(role)
            state[role]={
                "selected":selected,
                "display_name":Path(path).name if selected else "",
                "authority_label":label if selected else "",
                "sha256":artifact.sha256 if artifact is not None else "",
                "size_bytes":artifact.size_bytes if artifact is not None else 0,
            }
        return state

    def public_state(self) -> dict[str,object]:
        readiness=self._last_readiness or self.preflight()
        payload=readiness.to_public_dict()
        payload["packages"]=self.package_public_state()
        payload["package_error"]=self._last_package_error
        return payload

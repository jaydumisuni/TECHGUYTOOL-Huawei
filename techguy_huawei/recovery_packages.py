from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .recovery_identity import RecoveryIdentity, RecoveryIdentityStatus

ROLES=frozenset({"base","cust","preload"})


class RecoveryPackageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RecoveryPackageArtifact:
    role: str
    path: str
    sha256: str
    size_bytes: int
    authority_label: str
    family: str
    model: str | None
    region: str | None
    version: str


@dataclass(frozen=True, slots=True)
class RecoveryPackageSet:
    ready: bool
    blocker: str | None
    family: str
    model: str
    region: str
    artifacts: dict[str, RecoveryPackageArtifact]
    anti_rollback_state: str


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def inspect_recovery_package(path: str|Path, role: str, *, authority_label: str) -> RecoveryPackageArtifact:
    path=Path(path)
    role=role.lower()
    if role not in ROLES:
        raise RecoveryPackageError('PACKAGE_ROLE_INVALID')
    if not authority_label.strip():
        raise RecoveryPackageError('PACKAGE_AUTHORITY_LABEL_REQUIRED')
    if not path.is_file() or path.stat().st_size<=0:
        raise RecoveryPackageError('PACKAGE_FILE_INVALID')
    label=authority_label.strip().upper()
    family_match=re.match(r'([A-Z0-9]{3})-',label)
    if not family_match:
        raise RecoveryPackageError('PACKAGE_LABEL_INVALID')
    family=family_match.group(1)
    version_match=re.search(r'(\d+\.\d+\.\d+(?:\.\d+)?)',label)
    if not version_match:
        raise RecoveryPackageError('PACKAGE_VERSION_MISSING')
    model=None; region=None
    if role=='base':
        if '-LGRP' not in label:
            raise RecoveryPackageError('PACKAGE_BASE_LABEL_INVALID')
    elif role=='cust':
        m=re.match(r'([A-Z0-9]{3}-L(?:09|29))-CUST\s+[^()]+\((C\d{3})\)$',label)
        if not m:
            raise RecoveryPackageError('PACKAGE_CUST_LABEL_INVALID')
        model,region=m.group(1),m.group(2)
    else:
        m=re.match(r'([A-Z0-9]{3}-L(?:09|29))-PRELOAD\s+[^()]+\((C\d{3}R\d+)\)$',label)
        if not m:
            raise RecoveryPackageError('PACKAGE_PRELOAD_LABEL_INVALID')
        model=m.group(1); region=re.match(r'(C\d{3})',m.group(2)).group(1)
    return RecoveryPackageArtifact(role,str(path.resolve()),_sha256(path),path.stat().st_size,label,family,model,region,version_match.group(1))


def resolve_recovery_package_set(identity: RecoveryIdentity, artifacts: Iterable[RecoveryPackageArtifact], *, anti_rollback_state: str) -> RecoveryPackageSet:
    if identity.status is not RecoveryIdentityStatus.READY or not identity.family or not identity.model or not identity.region:
        raise RecoveryPackageError('IDENTITY_NOT_READY')
    by_role={a.role:a for a in artifacts}
    missing=sorted(ROLES-set(by_role))
    extra=sorted(set(by_role)-ROLES)
    if missing:
        raise RecoveryPackageError('PACKAGE_ROLE_MISSING:'+','.join(missing))
    if extra:
        raise RecoveryPackageError('PACKAGE_ROLE_UNKNOWN:'+','.join(extra))
    hashes=[a.sha256 for a in by_role.values()]
    if len(hashes)!=len(set(hashes)):
        raise RecoveryPackageError('PACKAGE_HASH_REUSED')
    for a in by_role.values():
        if a.family!=identity.family:
            raise RecoveryPackageError('PACKAGE_FAMILY_MISMATCH')
    for role in ('cust','preload'):
        a=by_role[role]
        if a.model!=identity.model:
            raise RecoveryPackageError('PACKAGE_MODEL_MISMATCH')
        if a.region!=identity.region:
            raise RecoveryPackageError('PACKAGE_REGION_MISMATCH')
    ready=anti_rollback_state=='compatible'
    blocker=None if ready else 'ANTI_ROLLBACK_UNRESOLVED'
    return RecoveryPackageSet(ready,blocker,identity.family,identity.model,identity.region,by_role,anti_rollback_state)

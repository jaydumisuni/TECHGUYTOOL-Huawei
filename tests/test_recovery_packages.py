from __future__ import annotations

from pathlib import Path

import pytest

from techguy_huawei.recovery_identity import RecoveryIdentity, RecoveryIdentityStatus
from techguy_huawei.recovery_packages import (
    RecoveryPackageError,
    inspect_recovery_package,
    resolve_recovery_package_set,
)


def identity() -> RecoveryIdentity:
    return RecoveryIdentity(
        RecoveryIdentityStatus.READY,
        "CLT",
        "CLT-LGRP2-OVS 9.1.0.325",
        9,
        "6546",
        "LOCKED",
        "CLT-L29",
        "C432",
        "C432R1",
    )


def artifact(tmp_path: Path, role: str, label: str, data: bytes):
    path=tmp_path/f"{role}.zip"
    path.write_bytes(data)
    return inspect_recovery_package(path, role, authority_label=label)


def test_resolves_exact_base_cust_preload_set(tmp_path: Path):
    items=[
        artifact(tmp_path,"base","CLT-LGRP2-OVS 9.1.0.325",b"base"),
        artifact(tmp_path,"cust","CLT-L29-CUST 9.0.0.7(C432)",b"cust"),
        artifact(tmp_path,"preload","CLT-L29-PRELOAD 9.1.0.14(C432R1)",b"preload"),
    ]
    result=resolve_recovery_package_set(identity(),items,anti_rollback_state="compatible")
    assert result.ready is True
    assert result.family=="CLT"
    assert result.model=="CLT-L29"
    assert result.region=="C432"
    assert set(result.artifacts)=={"base","cust","preload"}
    assert len({a.sha256 for a in result.artifacts.values()})==3


def test_missing_role_is_rejected(tmp_path: Path):
    items=[artifact(tmp_path,"base","CLT-LGRP2-OVS 9.1.0.325",b"base")]
    with pytest.raises(RecoveryPackageError,match="PACKAGE_ROLE_MISSING"):
        resolve_recovery_package_set(identity(),items,anti_rollback_state="compatible")


def test_duplicate_hash_is_rejected(tmp_path: Path):
    items=[
        artifact(tmp_path,"base","CLT-LGRP2-OVS 9.1.0.325",b"same"),
        artifact(tmp_path,"cust","CLT-L29-CUST 9.0.0.7(C432)",b"same"),
        artifact(tmp_path,"preload","CLT-L29-PRELOAD 9.1.0.14(C432R1)",b"other"),
    ]
    with pytest.raises(RecoveryPackageError,match="PACKAGE_HASH_REUSED"):
        resolve_recovery_package_set(identity(),items,anti_rollback_state="compatible")


def test_wrong_model_or_region_is_rejected(tmp_path: Path):
    items=[
        artifact(tmp_path,"base","CLT-LGRP2-OVS 9.1.0.325",b"base"),
        artifact(tmp_path,"cust","CLT-L09-CUST 9.0.0.7(C432)",b"cust"),
        artifact(tmp_path,"preload","CLT-L09-PRELOAD 9.1.0.14(C432R1)",b"preload"),
    ]
    with pytest.raises(RecoveryPackageError,match="PACKAGE_MODEL_MISMATCH"):
        resolve_recovery_package_set(identity(),items,anti_rollback_state="compatible")


def test_anti_rollback_unknown_blocks_ready(tmp_path: Path):
    items=[
        artifact(tmp_path,"base","CLT-LGRP2-OVS 9.1.0.325",b"base"),
        artifact(tmp_path,"cust","CLT-L29-CUST 9.0.0.7(C432)",b"cust"),
        artifact(tmp_path,"preload","CLT-L29-PRELOAD 9.1.0.14(C432R1)",b"preload"),
    ]
    result=resolve_recovery_package_set(identity(),items,anti_rollback_state="unknown")
    assert result.ready is False
    assert result.blocker=="ANTI_ROLLBACK_UNRESOLVED"


def test_authority_label_is_required(tmp_path: Path):
    path=tmp_path/'base.zip'; path.write_bytes(b'x')
    with pytest.raises(RecoveryPackageError,match="PACKAGE_AUTHORITY_LABEL_REQUIRED"):
        inspect_recovery_package(path,"base",authority_label="")

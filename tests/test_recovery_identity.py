from __future__ import annotations

import subprocess

from techguy_huawei.recovery_identity import (
    RecoveryIdentityStatus,
    resolve_fastboot_recovery_identity,
)


def runner_for(mapping):
    def run(command, **kwargs):
        key=tuple(command)
        code,out,err=mapping.get(key,(1,"","FAILED"))
        return subprocess.CompletedProcess(command,code,stdout=out,stderr=err)
    return run


def test_resolves_clt_family_but_blocks_exact_identity_when_model_region_missing():
    serial="PRIVATE123"
    mapping={
        ("fastboot","-s",serial,"oem","get-build-number"):(0,"","(bootloader) :CLT-LGRP2-OVS 9.1.0.325\nOKAY\n"),
        ("fastboot","-s",serial,"oem","get-bootinfo"):(0,"","(bootloader) locked\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-ANDROID_VERSION"):(0,"","(bootloader) 9\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-BOARDID"):(0,"","(bootloader) 6546\nOKAY\n"),
        ("fastboot","-s",serial,"oem","get-product-model"):(0,"","(bootloader) :\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-CUST"):(1,"","FAILED"),
        ("fastboot","-s",serial,"oem","oeminforead-PRELOAD"):(1,"","FAILED"),
    }
    identity=resolve_fastboot_recovery_identity(runner_for(mapping),"fastboot",serial)
    assert identity.status is RecoveryIdentityStatus.NEED_IDENTITY_EVIDENCE
    assert identity.family=="CLT"
    assert identity.build=="CLT-LGRP2-OVS 9.1.0.325"
    assert identity.android_major==9
    assert identity.board_id=="6546"
    assert identity.lock_state=="LOCKED"
    assert identity.model is None
    assert identity.region is None
    assert serial not in repr(identity)
    assert serial not in str(identity.to_public_dict())


def test_exact_model_and_region_can_make_identity_ready():
    serial="S"
    mapping={
        ("fastboot","-s",serial,"oem","get-build-number"):(0,"","(bootloader) :CLT-LGRP2-OVS 9.1.0.325\nOKAY\n"),
        ("fastboot","-s",serial,"oem","get-bootinfo"):(0,"","(bootloader) locked\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-ANDROID_VERSION"):(0,"","(bootloader) 9\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-BOARDID"):(0,"","(bootloader) 6546\nOKAY\n"),
        ("fastboot","-s",serial,"oem","get-product-model"):(0,"","(bootloader) CLT-L29\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-CUST"):(0,"","(bootloader) C432\nOKAY\n"),
        ("fastboot","-s",serial,"oem","oeminforead-PRELOAD"):(0,"","(bootloader) C432R1\nOKAY\n"),
    }
    identity=resolve_fastboot_recovery_identity(runner_for(mapping),"fastboot",serial)
    assert identity.status is RecoveryIdentityStatus.READY
    assert identity.model=="CLT-L29"
    assert identity.region=="C432"
    assert identity.preload_region=="C432R1"


def test_non_clt_family_is_unsupported_for_first_native_recipe():
    serial="S"
    mapping={
        ("fastboot","-s",serial,"oem","get-build-number"):(0,"","(bootloader) :VOG-LGRP2-OVS 10.0.0.186\nOKAY\n"),
        ("fastboot","-s",serial,"oem","get-bootinfo"):(0,"","(bootloader) locked\nOKAY\n"),
    }
    identity=resolve_fastboot_recovery_identity(runner_for(mapping),"fastboot",serial)
    assert identity.status is RecoveryIdentityStatus.UNSUPPORTED

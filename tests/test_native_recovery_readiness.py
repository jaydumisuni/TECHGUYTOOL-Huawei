from __future__ import annotations

from techguy_huawei.native_recovery_readiness import build_recovery_readiness
from techguy_huawei.native_recovery_transport import TransportCapability, TransportStatus
from techguy_huawei.recovery_identity import RecoveryIdentity, RecoveryIdentityStatus
from techguy_huawei.recovery_packages import RecoveryPackageArtifact, RecoveryPackageSet


def identity(*, ready: bool=True) -> RecoveryIdentity:
    return RecoveryIdentity(
        RecoveryIdentityStatus.READY if ready else RecoveryIdentityStatus.NEED_IDENTITY_EVIDENCE,
        'CLT','CLT-LGRP2-OVS 9.1.0.325',9,'6546','LOCKED',
        'CLT-L29' if ready else None,'C432' if ready else None,'C432R1' if ready else None,
    )

def packages(*, ready: bool=True) -> RecoveryPackageSet:
    artifacts={}
    for role in ('base','cust','preload'):
        artifacts[role]=RecoveryPackageArtifact(role,f'/tmp/{role}.zip',role[0]*64,1,role.upper(),'CLT','CLT-L29' if role!='base' else None,'C432' if role!='base' else None,'9.1.0.325')
    return RecoveryPackageSet(ready,None if ready else 'ANTI_ROLLBACK_UNRESOLVED','CLT','CLT-L29','C432',artifacts,'compatible' if ready else 'unresolved')

def capability(*, certified: bool=False) -> TransportCapability:
    return TransportCapability(
        'clt-native-system-recovery-v1','CLT',
        TransportStatus.HARDWARE_CERTIFIED if certified else TransportStatus.OBSERVED_UNCERTIFIED,
        ('rescue0.5',),('base','cust','preload'),
        'hardware_certified' if certified else 'static_interop_research',
        certified,() if certified else ('AUTH_PROVIDER_PENDING',),
    )

def test_readiness_exposes_exact_blockers_without_raw_identity():
    result=build_recovery_readiness(identity(ready=False),None,capability(),official_authorization_ready=False)
    public=result.to_public_dict()
    assert result.start_enabled is False
    assert public['family']=='CLT'
    assert public['build']=='CLT-LGRP2-OVS 9.1.0.325'
    assert public['lock_state']=='LOCKED'
    assert 'IDENTITY_NOT_READY' in public['blockers']
    assert 'PACKAGE_SET_NOT_READY' in public['blockers']
    assert 'TRANSPORT_NOT_CERTIFIED' in public['blockers']
    assert 'OFFICIAL_AUTHORIZATION_NOT_READY' in public['blockers']
    assert 'serial' not in public

def test_readiness_stays_blocked_when_only_transport_is_uncertified():
    result=build_recovery_readiness(identity(),packages(),capability(),official_authorization_ready=True)
    assert result.start_enabled is False
    assert result.blockers==('TRANSPORT_NOT_CERTIFIED',)

def test_readiness_stays_blocked_when_authorization_is_missing():
    result=build_recovery_readiness(identity(),packages(),capability(certified=True),official_authorization_ready=False)
    assert result.start_enabled is False
    assert result.blockers==('OFFICIAL_AUTHORIZATION_NOT_READY',)

def test_readiness_can_enable_only_when_all_authorities_are_green():
    result=build_recovery_readiness(identity(),packages(),capability(certified=True),official_authorization_ready=True)
    assert result.start_enabled is True
    assert result.blockers==()
    assert result.package_roles==('base','cust','preload')
    assert result.destructive_warning

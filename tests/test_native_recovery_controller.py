from __future__ import annotations

from pathlib import Path

from techguy_huawei.native_recovery_controller import NativeRecoveryController
from techguy_huawei.native_recovery_transport import TransportCapability, TransportStatus
from techguy_huawei.recovery_identity import RecoveryIdentity, RecoveryIdentityStatus


def ready_identity() -> RecoveryIdentity:
    return RecoveryIdentity(RecoveryIdentityStatus.READY,'CLT','CLT-LGRP2-OVS 9.1.0.325',9,'6546','LOCKED','CLT-L29','C432','C432R1')

def certified_transport() -> TransportCapability:
    return TransportCapability('clt-native-system-recovery-v1','CLT',TransportStatus.HARDWARE_CERTIFIED,('rescue0.5',),('base','cust','preload'),'hardware_certified',True,())

def write_packages(tmp_path: Path) -> dict[str,tuple[Path,str]]:
    values={
        'base':(tmp_path/'base.zip','CLT-LGRP2-OVS 9.1.0.325'),
        'cust':(tmp_path/'cust.zip','CLT-L29-CUST 9.1.0.12(C432)'),
        'preload':(tmp_path/'preload.zip','CLT-L29-PRELOAD 9.1.0.3(C432R1)'),
    }
    for i,(path,_) in enumerate(values.values(),1): path.write_bytes(bytes([i])*64)
    return values

def test_controller_exposes_three_roles_and_fails_closed_before_selection(tmp_path: Path):
    controller=NativeRecoveryController(ready_identity,transport_provider=certified_transport)
    public=controller.preflight().to_public_dict()
    assert public['start_enabled'] is False
    assert 'PACKAGE_SET_NOT_READY' in public['blockers']
    assert set(controller.package_roles)=={'base','cust','preload'}
    assert controller.package_public_state()['base']['selected'] is False

def test_controller_verifies_base_cust_preload_but_still_requires_auth(tmp_path: Path):
    controller=NativeRecoveryController(ready_identity,transport_provider=certified_transport)
    for role,(path,label) in write_packages(tmp_path).items(): controller.set_package(role,str(path),label)
    controller.set_anti_rollback_state('compatible')
    public=controller.preflight().to_public_dict()
    assert public['package_ready'] is True
    assert public['package_roles']==('base','cust','preload')
    assert public['start_enabled'] is False
    assert public['blockers']==('OFFICIAL_AUTHORIZATION_NOT_READY',)
    state=controller.package_public_state()
    assert all(state[role]['sha256'] for role in controller.package_roles)
    assert all('/' not in state[role]['display_name'] for role in controller.package_roles)

def test_controller_can_enable_only_after_official_auth_is_ready(tmp_path: Path):
    controller=NativeRecoveryController(ready_identity,transport_provider=certified_transport)
    for role,(path,label) in write_packages(tmp_path).items(): controller.set_package(role,str(path),label)
    controller.set_anti_rollback_state('compatible')
    controller.set_official_authorization_ready(True)
    result=controller.preflight()
    assert result.start_enabled is True

def test_controller_rejects_unknown_package_role(tmp_path: Path):
    controller=NativeRecoveryController(ready_identity)
    try:
        controller.set_package('system',str(tmp_path/'x.zip'),'X')
    except ValueError as exc:
        assert str(exc)=='RECOVERY_PACKAGE_ROLE_INVALID'
    else:
        raise AssertionError('unknown role must fail closed')

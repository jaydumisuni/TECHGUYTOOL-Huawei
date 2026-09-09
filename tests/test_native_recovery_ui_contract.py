from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'techguy_huawei'/'backend.py'
PAGE=ROOT/'qml'/'pages'/'FirmwareFlashPage.qml'


def test_backend_exposes_native_recovery_readiness_and_three_package_roles():
    source=BACKEND.read_text(encoding='utf-8')
    assert 'NativeRecoveryController' in source
    assert 'recoverySummaryJson' in source
    assert 'recoveryCanStart' in source
    assert 'setRecoveryPackage' in source
    assert 'native_recovery.preflight()' in source
    for role in ('base','cust','preload'):
        assert role in source.lower()

def test_firmware_page_uses_base_cust_preload_authority_not_single_generic_package():
    source=PAGE.read_text(encoding='utf-8')
    assert 'NATIVE SYSTEM RECOVERY' in source
    assert 'BASE' in source
    assert 'CUST' in source
    assert 'PRELOAD' in source
    assert 'backend.setRecoveryPackage' in source
    assert 'backend.recoverySummaryJson' in source
    assert 'backend.recoveryCanStart' in source
    assert 'START RECOVERY' in source
    assert 'VERIFY RECOVERY PLAN' in source
    assert 'may erase user data' in source

def test_recovery_ui_never_calls_hisuite_or_direct_fastboot_flash():
    combined=(BACKEND.read_text(encoding='utf-8')+'\n'+PAGE.read_text(encoding='utf-8')).lower()
    assert 'hisuite.exe' not in combined
    assert 'fastboot flash' not in combined
    assert 'oem unlock' not in combined

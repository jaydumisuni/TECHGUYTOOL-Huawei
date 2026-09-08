from __future__ import annotations

import pytest

from techguy_huawei.recovery_authorization import (
    AuthorizationMode,
    OfficialAuthorizationMaterial,
    RecoveryAuthorizationError,
    build_system_update_auth_frame,
    observed_huawei_authorization_provider,
    system_update_auth_accepted,
)


def material(mode: AuthorizationMode=AuthorizationMode.H) -> OfficialAuthorizationMaterial:
    return OfficialAuthorizationMaterial.create(
        mode=mode,
        payload=b'official-huawei-issued-material',
        source_ref='huawei://query.hicloud.com/BL/v1/Authorize',
        device_id='DEVICE-PRIVATE',
        update_token='TOKEN-PRIVATE',
    )

def test_auth_frame_prefixes_only_mechanically_proven_mode_byte():
    assert build_system_update_auth_frame(material(AuthorizationMode.H)) == b'Hofficial-huawei-issued-material'
    assert build_system_update_auth_frame(material(AuthorizationMode.E)) == b'Eofficial-huawei-issued-material'

def test_auth_material_public_view_hashes_private_authority_inputs():
    public=material().to_public_dict()
    text=repr(public)
    assert 'DEVICE-PRIVATE' not in text
    assert 'TOKEN-PRIVATE' not in text
    assert public['device_id_sha256']
    assert public['update_token_sha256']
    assert public['payload_sha256']
    assert 'payload' not in public

def test_empty_or_nonofficial_material_is_rejected():
    with pytest.raises(RecoveryAuthorizationError,match='AUTH_PAYLOAD_REQUIRED'):
        OfficialAuthorizationMaterial.create(mode=AuthorizationMode.H,payload=b'',source_ref='huawei://query.hicloud.com/BL/v1/Authorize',device_id='d',update_token='t')
    with pytest.raises(RecoveryAuthorizationError,match='AUTH_SOURCE_NOT_OFFICIAL'):
        OfficialAuthorizationMaterial.create(mode=AuthorizationMode.H,payload=b'x',source_ref='local://fabricated',device_id='d',update_token='t')

def test_response_byte_02_is_the_only_observed_success_marker():
    assert system_update_auth_accepted(b'\x02') is True
    assert system_update_auth_accepted(b'\x02anything') is True
    assert system_update_auth_accepted(b'') is False
    assert system_update_auth_accepted(b'\x00') is False
    assert system_update_auth_accepted(b'\x01') is False

def test_observed_provider_contract_is_fail_closed_until_request_schema_is_certified():
    provider=observed_huawei_authorization_provider()
    assert provider.check_endpoint == 'https://query.hicloud.com/BL/v1/CheckAndAuthorize'
    assert provider.authorize_endpoint == 'https://query.hicloud.com/BL/v1/Authorize'
    assert provider.device_fields == ('device_id','update_token')
    assert provider.pki_fields == ('device_certificate','key_attestantion')
    assert provider.request_schema_certified is False
    assert provider.ready is False
    assert 'REQUEST_SCHEMA_NOT_CERTIFIED' in provider.blockers

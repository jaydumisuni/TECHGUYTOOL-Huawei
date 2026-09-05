from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from techguy_huawei.native_recovery_executor import (
    NativeRecoveryExecutor,
    NativeRecoveryExecutorError,
)
from techguy_huawei.native_recovery_transport import TransportCapability, TransportStatus


def valid_lease() -> dict:
    fixture=json.loads(Path('contracts/fixtures/valid_contracts.json').read_text())
    lease=copy.deepcopy(next(x['contract'] for x in fixture['contracts'] if x['name']=='execution_lease'))
    lease['payload']['stage_id']='prepare_transport'
    return lease

def plan(lease: dict) -> dict:
    return {
        'state':'ready',
        'recipe_hash':lease['payload']['recipe_hash'],
        'physical_session_id':lease['physical_session_id'],
        'artifact_hashes':list(lease['payload']['artifact_hashes']),
        'transport_id':'clt-native-system-recovery-v1',
        'stages':[
            {'id':'prepare_transport','kind':'governed_execution'},
            {'id':'transfer_recovery_payloads','kind':'governed_execution'},
            {'id':'verify_transfer','kind':'observation'},
        ],
        'production_enabled':False,
    }

def certified_capability() -> TransportCapability:
    return TransportCapability('clt-native-system-recovery-v1','CLT',TransportStatus.HARDWARE_CERTIFIED,('rescue0.5',),('base','cust','preload'),'hardware_certified',True,())

def test_start_requires_explicit_owner_approval(tmp_path: Path):
    lease=valid_lease(); ex=NativeRecoveryExecutor(plan(lease),certified_capability(),tmp_path/'journal.jsonl',lambda **kw:{'outcome':'accepted'})
    with pytest.raises(NativeRecoveryExecutorError,match='OWNER_APPROVAL_REQUIRED'):
        ex.start_recovery(owner_approved=False,execution_lease=lease)

def test_uncertified_transport_blocks_before_executor(tmp_path: Path):
    lease=valid_lease(); cap=certified_capability(); cap=TransportCapability(cap.transport_id,cap.family,TransportStatus.OBSERVED_UNCERTIFIED,cap.protocol_versions,cap.package_roles,'static_interop_research',False,('AUTH_UNKNOWN',))
    ex=NativeRecoveryExecutor(plan(lease),cap,tmp_path/'journal.jsonl',lambda **kw:{'outcome':'accepted'})
    with pytest.raises(NativeRecoveryExecutorError,match='TRANSPORT_NOT_CERTIFIED'):
        ex.start_recovery(owner_approved=True,execution_lease=lease)

def test_artifact_hash_drift_is_blocked(tmp_path: Path):
    lease=valid_lease(); bad=copy.deepcopy(lease); bad['payload']['artifact_hashes']=['f'*64]
    ex=NativeRecoveryExecutor(plan(lease),certified_capability(),tmp_path/'journal.jsonl',lambda **kw:{'outcome':'accepted'})
    with pytest.raises(NativeRecoveryExecutorError,match='EXECUTION_LEASE_INVALID'):
        ex.start_recovery(owner_approved=True,execution_lease=bad)

def test_completed_stage_is_not_repeated_on_resume(tmp_path: Path):
    lease=valid_lease(); calls=[]
    def execute(**kwargs):
        calls.append(kwargs['stage_id'])
        return {'outcome':'accepted','raw_result_sha256':'d'*64,'readback_sha256':'e'*64,'bytes_written':1}
    journal=tmp_path/'journal.jsonl'
    ex=NativeRecoveryExecutor(plan(lease),certified_capability(),journal,execute)
    result=ex.start_recovery(owner_approved=True,execution_lease=lease)
    assert result['state']=='stage_completed'
    assert calls==['prepare_transport']
    ex2=NativeRecoveryExecutor(plan(lease),certified_capability(),journal,execute)
    resumed=ex2.resume_recovery(execution_lease=lease)
    assert resumed['next_stage']=='transfer_recovery_payloads'
    assert calls==['prepare_transport']

def test_started_without_completion_never_repeats_write(tmp_path: Path):
    lease=valid_lease(); journal=tmp_path/'journal.jsonl'
    journal.write_text(json.dumps({'event':'stage_started','stage_id':'prepare_transport','lease_id':lease['payload']['lease_id']})+'\n')
    calls=[]
    ex=NativeRecoveryExecutor(plan(lease),certified_capability(),journal,lambda **kw:calls.append(kw))
    with pytest.raises(NativeRecoveryExecutorError,match='RECOVERY_STAGE_OUTCOME_UNKNOWN'):
        ex.resume_recovery(execution_lease=lease)
    assert calls==[]

def test_single_use_lease_cannot_execute_second_time(tmp_path: Path):
    lease=valid_lease(); calls=[]
    def execute(**kwargs):
        calls.append(kwargs['stage_id'])
        return {'outcome':'accepted','raw_result_sha256':'d'*64,'readback_sha256':'e'*64,'bytes_written':1}
    ex=NativeRecoveryExecutor(plan(lease),certified_capability(),tmp_path/'journal.jsonl',execute)
    ex.start_recovery(owner_approved=True,execution_lease=lease)
    with pytest.raises(NativeRecoveryExecutorError,match='LEASE_ALREADY_CONSUMED'):
        ex.start_recovery(owner_approved=True,execution_lease=lease)
    assert calls==['prepare_transport']

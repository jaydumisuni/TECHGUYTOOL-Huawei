from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .contract_validation import validate_contract
from .native_recovery_transport import TransportCapability, TransportStatus


class NativeRecoveryExecutorError(RuntimeError):
    pass


class NativeRecoveryExecutor:
    def __init__(
        self,
        plan: Mapping[str, Any],
        capability: TransportCapability,
        journal_path: str | Path,
        stage_executor: Callable[..., Mapping[str, Any]],
    ) -> None:
        self.plan=dict(plan)
        self.capability=capability
        self.journal_path=Path(journal_path)
        self.journal_path.parent.mkdir(parents=True,exist_ok=True)
        self.stage_executor=stage_executor

    def _events(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        out=[]
        for line in self.journal_path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            value=json.loads(line)
            if not isinstance(value,dict):
                raise NativeRecoveryExecutorError('JOURNAL_CORRUPT')
            out.append(value)
        return out

    def _append(self, event: Mapping[str, Any]) -> None:
        with self.journal_path.open('a',encoding='utf-8',newline='\n') as handle:
            handle.write(json.dumps(dict(event),sort_keys=True,separators=(',',':'))+'\n')

    def _validate_ready(self) -> None:
        if self.plan.get('state')!='ready':
            raise NativeRecoveryExecutorError('RECOVERY_PLAN_NOT_READY')
        if self.plan.get('production_enabled') is not False:
            raise NativeRecoveryExecutorError('PRODUCTION_AUTHORITY_INVALID')
        if (
            not self.capability.write_certified
            or self.capability.status is not TransportStatus.HARDWARE_CERTIFIED
        ):
            raise NativeRecoveryExecutorError('TRANSPORT_NOT_CERTIFIED')
        if self.capability.transport_id!=self.plan.get('transport_id'):
            raise NativeRecoveryExecutorError('TRANSPORT_ID_MISMATCH')

    def _validate_lease(self, lease: Mapping[str, Any]) -> None:
        artifact_hashes=list(self.plan.get('artifact_hashes') or [])
        result=validate_contract(
            lease,
            context={
                'expected_contract_type':'execution_lease',
                'expected_physical_session_id':self.plan.get('physical_session_id'),
                'expected_recipe_hash':self.plan.get('recipe_hash'),
                'expected_artifact_hashes':artifact_hashes,
                'expected_authority':'execution',
            },
        )
        if not result.ok:
            codes=','.join(error.code for error in result.errors)
            raise NativeRecoveryExecutorError('EXECUTION_LEASE_INVALID:'+codes)
        payload=lease.get('payload')
        if not isinstance(payload,Mapping):
            raise NativeRecoveryExecutorError('EXECUTION_LEASE_INVALID:PAYLOAD')
        lease_id=payload.get('lease_id')
        if any(e.get('event')=='lease_consumed' and e.get('lease_id')==lease_id for e in self._events()):
            raise NativeRecoveryExecutorError('LEASE_ALREADY_CONSUMED')

    def _next_execution_stage(self) -> str | None:
        events=self._events()
        completed={e.get('stage_id') for e in events if e.get('event')=='stage_completed'}
        started={e.get('stage_id') for e in events if e.get('event')=='stage_started'}
        unresolved=started-completed
        if unresolved:
            raise NativeRecoveryExecutorError('RECOVERY_STAGE_OUTCOME_UNKNOWN:'+','.join(sorted(str(x) for x in unresolved)))
        for stage in self.plan.get('stages') or []:
            if not isinstance(stage,Mapping):
                continue
            if stage.get('kind')!='governed_execution':
                continue
            stage_id=str(stage.get('id'))
            if stage_id not in completed:
                return stage_id
        return None

    def start_recovery(self, *, owner_approved: bool, execution_lease: Mapping[str, Any]) -> dict[str, Any]:
        if owner_approved is not True:
            raise NativeRecoveryExecutorError('OWNER_APPROVAL_REQUIRED')
        self._validate_ready()
        self._validate_lease(execution_lease)
        stage_id=self._next_execution_stage()
        if stage_id is None:
            return {'state':'execution_stages_complete','next_stage':None}
        payload=execution_lease['payload']
        if payload.get('stage_id')!=stage_id:
            raise NativeRecoveryExecutorError('LEASE_STAGE_MISMATCH')
        lease_id=str(payload['lease_id'])
        artifact_hashes=tuple(str(x) for x in payload['artifact_hashes'])
        self._append({'event':'stage_started','stage_id':stage_id,'lease_id':lease_id})
        result=dict(self.stage_executor(
            stage_id=stage_id,
            artifact_hashes=artifact_hashes,
            capability=self.capability,
            lease=dict(execution_lease),
        ))
        if result.get('outcome')!='accepted':
            self._append({'event':'stage_failed','stage_id':stage_id,'lease_id':lease_id,'outcome':result.get('outcome','failed')})
            raise NativeRecoveryExecutorError('RECOVERY_STAGE_FAILED')
        self._append({
            'event':'stage_completed',
            'stage_id':stage_id,
            'lease_id':lease_id,
            'raw_result_sha256':result.get('raw_result_sha256'),
            'readback_sha256':result.get('readback_sha256'),
            'bytes_written':int(result.get('bytes_written',0)),
        })
        self._append({'event':'lease_consumed','lease_id':lease_id,'stage_id':stage_id})
        return {'state':'stage_completed','stage_id':stage_id,'result':result}

    def resume_recovery(self, *, execution_lease: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_ready()
        payload=execution_lease.get('payload')
        if not isinstance(payload,Mapping):
            raise NativeRecoveryExecutorError('EXECUTION_LEASE_INVALID:PAYLOAD')
        next_stage=self._next_execution_stage()
        return {'state':'resume_ready','next_stage':next_stage}

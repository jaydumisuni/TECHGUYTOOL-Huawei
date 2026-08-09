# Phase 5 — Repair Decision Corps

Status: IMPLEMENTED UNDER PROOF  
Authority: `FULL_PLAN.md`  
Branch: `phase5/repair-decision-corps-v2`

## Purpose

Phase 5 converts the reasoning role used during the historical P30 investigation into deterministic software. It consumes approved technician intent plus frozen read-only Xray evidence and emits Phase 2 governance verdicts.

The Phase 5 exit gate is exact:

> Historical replay blocks premature stock-Fastboot restoration.

Phase 5 does not touch a phone and does not create execution authority.

## Frozen officer order

1. `identity.officer`
2. `mode.officer`
3. `firmware.officer`
4. `artifact.officer`
5. `recovery.officer`
6. `route.planner`
7. `safety.challenger`
8. `verification.judge`
9. `repair.governor` — aggregate governance only

Hard veto authority belongs only to Identity, Recovery, Safety, and Verification. A hard veto must be a `block` verdict. A majority can never override it.

The Governor rejects:

- missing officers;
- duplicate or reordered officers;
- unknown verdicts;
- vetoes fabricated by non-veto officers;
- vetoes attached to non-block verdicts;
- officer recipe hashes that do not match the Governor context.

## Inputs

Phase 5 accepts:

- a valid, unexpired, approved Phase 2 `operation_request`;
- one Phase 4 `ReplayBundle` or equivalent certified read-only evidence snapshot;
- one requested transition: `inspect`, `perform_operation`, `reboot`, `restore_stock_fastboot`, or `finalize`;
- optional reviewed recipe hash;
- explicit artifact-readiness state.

The operation request and Xray evidence must share the same physical-session UUID. Stale, mismatched, rejected, malformed, or unsupported requests fail closed.

## Evidence normalization

Every officer receives the same immutable normalized snapshot:

- evidence subject verdicts;
- endpoint transport, observed state, and read-only capabilities;
- device twin;
- Xray safety state.

Endpoint presence is not enough to select a route. `candidate` or `unauthorized` service endpoints are not promoted into service-route authority.

Xray remains read-only. A transport observation is never converted into permission to write. Phase 5 may select the next governance stage, but Phase 6 must create enforceable leases and Phase 7 must execute within them.

## Historical P30 result

The recovered P30 replay proves:

- MAIN VERSION is missing;
- OEMINFO version identity is missing;
- vendor/country state is contradictory;
- normal Fastboot exposes read capability only;
- HUAWEI USB COM 1.0 is observed as a service endpoint;
- the service environment must be retained;
- reboot is blocked while release conditions are unresolved;
- stock-Fastboot restoration is blocked;
- finalization is blocked until Xray certifies release;
- the bounded main-version repair stage may be selected while service mode remains protected and required artifacts are present.

If the service endpoint is changed to `unauthorized`, both Mode Officer and Route Planner require technician service entry rather than treating the endpoint name as usable authority.

## Phase 2 outputs

Each officer and the Repair Governor emit a valid `decision_verdict` contract with:

- `authority = governance`;
- exact physical-session binding;
- deterministic UUIDv5 identity;
- evidence hashes from the Xray bundle;
- explicit verdict and reason code;
- exact veto flag;
- optional reviewed recipe hash.

Phase 5 never emits:

- `mode_lease`;
- `execution_lease`;
- `executor_result`;
- direct device commands;
- shell commands;
- USB/serial writes;
- partition targets;
- reboot commands.

## Proof requirements

The hosted Phase 5 proof must demonstrate:

- P30 premature stock-Fastboot restoration is blocked;
- P30 reboot and finalization are blocked while release is unresolved;
- the main-version repair stage remains selectable without releasing service mode;
- P10 premature finalization remains blocked;
- unauthorized service endpoints are not promoted into route authority;
- majority voting cannot override a hard veto;
- invalid veto authority fails closed;
- unknown verdicts fail closed;
- incomplete, duplicate, or reordered officer sets fail closed;
- recipe-context mismatch fails closed;
- operation-request physical-session mismatch fails closed;
- unapproved and expired operation requests fail closed;
- unsupported operations/actions fail closed;
- repeated reports are byte deterministic;
- every officer/Governor output validates against the frozen Phase 2 contract registry;
- the implementation contains no device-execution surface;
- Phase 2, Phase 3, and frozen Phase 4 regressions remain green;
- the strict SRG 20-for-2 gate passes `40/40`.

## Authority boundary

```text
xray_authority = read_only
decision_authority = governance_only
execution_authority = none
device_authority = none
```

An `allow_stage` verdict is a governance result, not permission to write the device.

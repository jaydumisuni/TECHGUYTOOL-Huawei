# Phase 5 — Repair Decision Corps

Status: IMPLEMENTED UNDER PROOF  
Authority: `FULL_PLAN.md`  
Branch: `phase5/repair-decision-corps`

## Purpose

Phase 5 replaces the reasoning role that was previously supplied manually during the successful P30 investigation with deterministic Python/Rust-compatible governance logic.

The Decision Corps does not touch a phone. It consumes technician intent plus frozen Xray evidence and emits frozen Phase 2 governance contracts.

The Phase 5 exit gate is:

> Historical replay blocks premature stock-Fastboot restoration.

## Officers

The deterministic officer order is frozen as:

1. `identity.officer`
2. `mode.officer`
3. `firmware.officer`
4. `artifact.officer`
5. `recovery.officer`
6. `route.planner`
7. `safety.challenger`
8. `verification.judge`
9. `repair.governor` — aggregate authority only

Hard-veto authority belongs only to:

- Identity Officer;
- Recovery Officer;
- Safety Challenger;
- Verification Judge.

A majority can never override a hard veto.

## Deterministic inputs

Phase 5 accepts:

- a frozen Phase 2 `operation_request` representing technician intent;
- a Phase 4 Kirin Xray `ReplayBundle` or equivalent certified read-only evidence;
- the requested transition (`inspect`, `perform_operation`, `reboot`, `restore_stock_fastboot`, or `finalize`);
- optional reviewed recipe hash;
- explicit artifact readiness.

Every request must remain bound to the same physical-session UUID as the Xray evidence.

## Deterministic outputs

Each officer emits a frozen Phase 2 `decision_verdict` contract with:

- `authority = governance`;
- exact physical-session binding;
- deterministic contract identity;
- Xray evidence hashes;
- an explicit verdict and reason code;
- a veto flag that is accepted only from one of the four veto authorities;
- optional reviewed recipe hash.

The Repair Governor emits a ninth `decision_verdict` after applying veto precedence and fail-closed non-veto precedence.

Phase 5 never emits:

- `mode_lease`;
- `execution_lease`;
- `executor_result`;
- direct device commands;
- shell commands;
- USB writes;
- partition targets.

Those belong to later phases.

## Historical P30 behavior

For the recovered P30 replay:

- `VERSION` being accepted is not enough to finalize;
- missing MAIN VERSION and OEMINFO version identity remain unresolved evidence;
- normal Fastboot has read capability but no proved main-version/OEMINFO write capability;
- HUAWEI USB COM 1.0 service-entry evidence is recognized;
- the service environment remains protected while the repair is unresolved;
- reboot is blocked;
- stock-Fastboot restoration is blocked;
- finalization is blocked until Xray certification and release conditions are satisfied;
- the main-version repair stage itself may proceed when required artifacts are present.

This reproduces the critical historical lesson without using GPT or another model as repair authority.

## Routing rules

The Route Planner prefers an exact direct route only when its observed endpoint capabilities support the requested operation.

For read-only inspection, observed direct endpoints are sufficient.

For main-version repair:

- a read-only normal-Fastboot endpoint is not promoted into write authority;
- an observed service entry may be selected as the next approved route;
- if no suitable service entry exists, the verdict becomes `need_technician` with `DEC_TESTPOINT_103_SERVICE_ENTRY_REQUIRED`.

The Decision Corps never fabricates a capability from a transport name.

## Phase 5 proof requirements

The proof suite must demonstrate:

- deterministic repeated reports and SHA-256 identity;
- Phase 2 validity for every officer and governor contract;
- exact physical-session binding;
- approved technician intent requirement;
- unsupported operation/action rejection;
- missing artifact fail-closed behavior;
- direct read route selection;
- P10 service-environment finalization block;
- P30 reboot block;
- P30 premature stock-Fastboot block;
- P30 finalization block until verification;
- P30 repair-stage allowance while service mode remains protected;
- majority cannot override a Safety veto;
- incomplete officer sets fail closed;
- no subprocess, Fastboot, ADB, serial, USB, partition-write or OEMINFO-write execution surface.

Every hosted Phase 5 proof also runs the strict SRG 20-for-2 gate (`40/40`) and all previous phase regressions.

## Authority boundary

```text
device_authority = none
xray_authority = read_only
decision_authority = governance_only
execution_authority = none
```

The existence of a governance `allow_stage` verdict is not permission to write a device. Phase 6 must still create and enforce the correct mode/execution authority, and Phase 7 must still provide a bounded executor.

# Phase 6 — Mode and Execution Leases

## Purpose

Phase 6 converts Phase 5 governance decisions into Rust-enforced, bounded authority. It does not execute device commands. The lease guard is deliberately placed in the Rust Device Gateway crate so a later executor cannot bypass Python policy by changing its own request.

## Authority boundary

```text
Kirin Xray             read_only
Repair Decision Corps  governance_only
Mode lease             governance constraint
Execution lease        bounded single-use authority token
Executor               not implemented in Phase 6
Device authority       none in Phase 6 proof
```

A Phase 5 `allow_stage` verdict is never sufficient by itself. A later executor must present an exact execution lease and satisfy the active mode lease.

## Mode lease enforcement

The Rust guard binds a mode lease to:

- one physical-device session;
- one current service mode;
- an expiry;
- reboot permission;
- stock-Fastboot restoration permission;
- explicit release conditions;
- an unreleased state.

For the canonical VOG recovery, `board_service_fastboot` remains protected while main-version identity or remaining firmware stages are unresolved. Reboot and stock-Fastboot restoration remain blocked until the governor can prove every release condition and issue the next valid authority state.

## Execution lease enforcement

A claim binds all of the following before it is accepted:

- physical-device session;
- recipe hash;
- adapter ID and exact adapter version;
- sorted exact artifact hashes;
- allowed partition set;
- range-manifest hash;
- maximum write byte count;
- current expected mode;
- exact stage ID;
- reboot permission;
- contract expiry;
- single-use state.

The lease ID is atomically inserted into a SQLite claim ledger before a permit is returned. Reopening the ledger preserves consumption state, so an interrupted process cannot replay the same execution lease.

## Fail-closed codes

Representative policy failures include:

- `MODE_MISMATCH`
- `REBOOT_BLOCKED_BY_ACTIVE_MODE_LEASE`
- `STOCK_FASTBOOT_RESTORE_BLOCKED_BY_ACTIVE_MODE_LEASE`
- `MODE_LEASE_ALREADY_RELEASED`
- `PARTITION_NOT_AUTHORIZED`
- `WRITE_RANGE_EXCEEDS_LEASE`
- `RANGE_MANIFEST_MISMATCH`
- `STAGE_MISMATCH`
- `ADAPTER_ID_MISMATCH`
- `ADAPTER_VERSION_MISMATCH`
- `REBOOT_NOT_AUTHORIZED_BY_EXECUTION_LEASE`
- `EXECUTION_LEASE_ALREADY_CONSUMED`

Contract-level mismatches such as wrong session, recipe, artifact set, authority, expiry, or consumed envelope are rejected by the frozen Phase 2 contract validator before runtime policy checks.

## SRG 20-for-2 review

Phase 6 must pass two independent 20-check review passes. Every check is evidence/falsifier/verification oriented. No LLM or model outcome can grant lease authority.

## Exit gate

Phase 6 is complete only when automated proof demonstrates that Rust rejects:

1. another physical device/session;
2. wrong or unordered artifact authority;
3. a partition outside the allowlist;
4. a range-manifest mismatch;
5. zero or over-limit write sizes;
6. wrong adapter or adapter version;
7. wrong stage;
8. wrong service mode;
9. expired contracts;
10. prohibited reboot;
11. premature stock-Fastboot restoration;
12. a released mode lease reused as active authority;
13. an execution lease reused in the same process; and
14. an execution lease reused after process/database reopen.

The proof must also show the positive path: the exact device/session, recipe, artifacts, partition, range, stage, adapter, mode and size produce one bounded permit and no device command is executed.

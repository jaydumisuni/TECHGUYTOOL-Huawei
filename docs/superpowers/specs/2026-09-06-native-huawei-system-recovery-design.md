# Native Huawei System Recovery Design

**Date:** 2026-09-06
**Status:** Approved architecture
**Target:** TECHGUYTOOL-Huawei

## Goal

Replace HiSuite as a runtime dependency for locked/dead-screen Huawei system recovery. TECHGUYTOOL-Huawei must own recovery planning, package authority, transport orchestration, evidence, interruption recovery, and verification while preserving the existing fail-closed write-governance model.

## Proven starting point

The current physically proven CLT/P20 Pro-family handset reaches normal Fastboot with a locked bootloader. Read-only Huawei OEM probes expose the CLT build family and lock state. The repository already owns the physical-session, artifact-manifest, recipe, decision, mode-lease, execution-lease, executor-result, verification-result, recovery-plan, journal, and source-freeze contracts.

## Non-goals

- No dependency on a locally installed HiSuite process.
- No bootloader unlock/relock as a recovery prerequisite.
- No guessed model/region/customization.
- No generic `fastboot flash` fallback on a locked retail bootloader.
- No write before exact artifact/profile authority and explicit owner approval.
- No automatic production enablement from software tests.

## Architecture

### 1. Recovery identity resolver

A read-only `HuaweiRecoveryIdentity` is built from physical-session continuity plus fixed Fastboot OEM queries. It records family/build/Android/board/customization evidence and whether exact model/region identity is resolved. The resolver returns `READY`, `NEED_IDENTITY_EVIDENCE`, or `UNSUPPORTED`; it never guesses CLT-L09/CLT-L29 or region.

### 2. Package-set resolver

A recovery package set is Base + CUST + PRELOAD. Each package is represented by a local artifact manifest: path, SHA-256, size, package role, parsed version/family/customization metadata, custody, and provenance hash. The resolver rejects mixed family, mixed customization, downgrade/anti-rollback uncertainty, missing package roles, duplicate hashes, and packages whose metadata cannot be bound to the exact resolved target.

The network/download layer is deliberately separate. The first production contract accepts already-downloaded local packages and exposes a download-plan interface; downloading from Huawei/Firmware Finder sources may be added without changing execution authority.

### 3. Recovery recipe

`clt_native_system_recovery_v1` is a planning-only recipe. Stages:

1. certify physical continuity;
2. verify Huawei normal Fastboot;
3. resolve exact recovery identity;
4. bind Base/CUST/PRELOAD artifacts;
5. verify package relationship and anti-rollback constraints;
6. acquire recovery mode lease;
7. prepare native recovery transport;
8. transfer only lease-bound recovery payloads;
9. verify each transfer/result;
10. enter stock update/recovery application stage;
11. verify resulting build/identity;
12. close the recovery plan.

The recipe remains blocked until the native transport adapter reports a hardware-supported capability for the connected family.

### 4. Native recovery transport

A `HuaweiNativeRecoveryTransport` interface separates protocol characterization from execution. It exposes read-only `probe_capabilities()` and guarded `prepare()` / `execute_stage()` methods. No adapter may receive an execution lease until its exact command sequence, target artifact type, device mode, and verification signal are hardware-certified.

For CLT/Kirin970, the initial adapter recognizes Huawei normal Fastboot and records the presence/absence of known rescue capabilities. It must not claim HiSuite System Recovery equivalence merely because Fastboot is present. If the proprietary Rescue/System-Recovery transition is not yet characterized, the transport returns `TRANSPORT_NOT_CERTIFIED` and the recipe stays blocked.

### 5. Clean-room protocol characterization

HiSuite may be used only as an interoperability research artifact, never as a runtime dependency. Protocol research is isolated from execution source. Findings must be converted into replay fixtures and then into a bounded adapter with independent tests. No Huawei DLL/executable is bundled or invoked by production TECHGUYTOOL-Huawei.

### 6. Guarded executor

The executor consumes only a valid single-use `execution_lease`. It validates recipe hash, physical session, artifact hashes, stage id, allowed target, byte/range ceiling, expected mode, and expiry. It journals before/after evidence and produces `executor_result`. Destructive execution requires explicit owner approval in the operation request.

### 7. Interruption and verification

Every stage writes a recovery-plan checkpoint. Restart never repeats a completed write blindly. Resume re-probes the physical device, revalidates artifact hashes and mode, and either resumes the next safe stage or blocks. Final success requires post-recovery build/identity verification and a boot-state observation.

## UI

The existing Firmware Flash page becomes a recovery-aware preflight surface. It must show:

- detected family/build/lock state;
- exact identity status;
- Base/CUST/PRELOAD package status;
- package hashes and compatibility verdict;
- data-loss/destructive warning;
- recovery stage and journal state;
- a disabled Start Recovery button until all governance conditions pass.

No new standalone application is created.

## Safety invariants

1. Locked bootloader remains locked.
2. Identity ambiguity blocks execution.
3. Package ambiguity blocks execution.
4. Transport uncertainty blocks execution.
5. Every write is artifact-hash and stage bound.
6. Every destructive stage is owner-approved.
7. Physical proof may promote only the exact capability demonstrated.
8. Packaging/build status remains separate from source correctness.

## Success criteria

The feature is complete when: resolver/package/recipe/executor software contracts are fully proven; a native CLT recovery transport has replay proof; the connected CLT handset can execute a physically certified stock recovery end-to-end without HiSuite; resulting build/identity is verified; interrupted recovery can resume safely; and the physical matrix records only those capabilities actually demonstrated.

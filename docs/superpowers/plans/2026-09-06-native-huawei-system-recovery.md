# Native Huawei System Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HiSuite-free, fail-closed native Huawei recovery path from verified normal Fastboot through exact package authority and governed execution.

**Architecture:** Reuse the existing DeviceEngine, Phase 2 contracts, Decision Corps, mode/execution leases, evidence journal, and firmware UI. Add focused resolver/package/transport/executor modules; no write-capable code is added until read-only identity, package authority, and transport certification exist.

**Tech Stack:** Python 3.11+, PySide6/QML, existing JSON contracts, standard `fastboot` CLI for read-only probes, SHA-256 artifact authority.

**Spec:** `docs/superpowers/specs/2026-09-06-native-huawei-system-recovery-design.md`

## Global Constraints

- HiSuite is never a production/runtime dependency.
- Bootloader remains locked.
- Exact model/region ambiguity blocks execution.
- Base/CUST/PRELOAD package ambiguity blocks execution.
- Generic `fastboot flash` is not a recovery fallback.
- No execution lease is issued until the native transport is hardware-certified.
- Every write is physical-session, recipe, artifact-hash, stage, and range bound.
- Production remains disabled until physical recovery proof exists.

---

### Task 1: CLT recovery identity resolver

**Files:**
- Create: `techguy_huawei/recovery_identity.py`
- Test: `tests/test_recovery_identity.py`
- Modify: `techguy_huawei/device_engine.py`

**Interfaces:**
- Produces: `RecoveryIdentity`, `RecoveryIdentityStatus`, `resolve_fastboot_recovery_identity(run, fastboot, serial)`.
- Consumes fixed read-only OEM commands only.

- [ ] Write failing tests proving CLT family/build/Android/board/lock parsing, blank exact-model handling, unsupported family handling, and no full serial in the public result.
- [ ] Run `python3 -m pytest -q tests/test_recovery_identity.py` and verify RED because the module is absent.
- [ ] Implement the immutable resolver and fail-closed parsers.
- [ ] Re-run the focused tests and `tests/test_device_engine.py`.
- [ ] Commit `feat(huawei): add recovery identity resolver`.

### Task 2: Base/CUST/PRELOAD package-set authority

**Files:**
- Create: `techguy_huawei/recovery_packages.py`
- Test: `tests/test_recovery_packages.py`

**Interfaces:**
- Produces: `RecoveryPackageArtifact`, `RecoveryPackageSet`, `inspect_recovery_package(path, role)`, `resolve_recovery_package_set(identity, artifacts)`.
- Consumes local files only; no network download occurs in this task.

- [ ] Write failing tests for SHA-256/size, role completeness, duplicate-hash rejection, family mismatch, exact-model/customization ambiguity, and anti-rollback unknown -> blocked.
- [ ] Verify RED.
- [ ] Implement local artifact hashing plus filename/metadata normalization with strict unknown handling.
- [ ] Verify GREEN and commit `feat(huawei): add recovery package authority`.

### Task 3: Native recovery recipe and planner

**Files:**
- Create: `recipes/clt_native_system_recovery_v1.json`
- Create: `techguy_huawei/native_recovery_recipe.py`
- Test: `tests/test_native_recovery_recipe.py`

**Interfaces:**
- Produces: `compile_native_recovery_plan(identity, package_set, physical_session_id, transport_capability)` and deterministic recipe hash.
- Returns blocked plan when identity/package/transport is unresolved.

- [ ] Write failing recipe validation/ordering tests and blocked/eligible plan tests.
- [ ] Verify RED.
- [ ] Implement planning-only recipe validation and compilation.
- [ ] Verify GREEN and commit `feat(huawei): add native recovery recipe`.

### Task 4: Clean-room CLT recovery transport characterization

**Files:**
- Create: `techguy_huawei/native_recovery_transport.py`
- Create: `replay/kirin/clt_native_recovery_transport.json`
- Test: `tests/test_native_recovery_transport.py`
- Create: `tools/probe_native_recovery_transport.py`

**Interfaces:**
- Produces: `TransportCapability`, `probe_capabilities()` and a guarded `execute_stage()` interface.
- Initial execution status must remain `TRANSPORT_NOT_CERTIFIED` until a replay fixture and live CLT evidence prove an exact stage.

- [ ] Write failing tests that normal Fastboot alone is insufficient, unsupported/ambiguous commands fail closed, and execution cannot occur while uncertified.
- [ ] Verify RED.
- [ ] Implement read-only capability probes and replay parser; do not add a device write yet.
- [ ] On ATHENA, use the connected CLT handset to collect only read-only command support/evidence and update the replay fixture.
- [ ] If an exact safe recovery transition is mechanically established, add that single transition behind a certification flag with a new failing test first; otherwise keep execution blocked and record the concrete protocol blocker.
- [ ] Commit `feat(huawei): add native recovery transport authority`.

### Task 5: Guarded recovery executor and restart journal

**Files:**
- Create: `techguy_huawei/native_recovery_executor.py`
- Test: `tests/test_native_recovery_executor.py`
- Modify: `techguy_huawei/backend.py`

**Interfaces:**
- Produces: `prepare_recovery()`, `start_recovery(approved: bool)`, `resume_recovery()`.
- Consumes compiled plan + existing operation/decision/mode/execution lease contracts.

- [ ] Write failing tests for no-approval block, identity drift block, artifact-hash drift block, expired/single-use lease block, stage journaling, and resume-without-repeat.
- [ ] Verify RED.
- [ ] Implement executor with execution disabled unless transport capability is certified.
- [ ] Wire `flash_firmware` to recovery preflight rather than bare file-size preflight.
- [ ] Verify GREEN and commit `feat(huawei): add governed native recovery executor`.

### Task 6: Firmware UI recovery preflight

**Files:**
- Modify: `qml/pages/FirmwareFlashPage.qml`
- Modify: `techguy_huawei/backend.py`
- Test: `tests/test_repository_contracts.py`
- Test: `tests/test_device_engine.py`

**Interfaces:**
- Displays identity, package-set, transport, destructive warning, and recovery-plan state.
- Start remains disabled until backend reports `recoveryReady == true`.

- [ ] Add failing contract tests for required state labels and guarded Start Recovery binding.
- [ ] Verify RED.
- [ ] Implement minimal UI/backend properties without redesigning the approved visual language.
- [ ] Verify source QML construction and UI-state capture.
- [ ] Commit `feat(huawei): expose native recovery preflight`.

### Task 7: Freeze, physical proof, and integration

**Files:**
- Modify: `manifests/phase15_physical_proof_matrix.json` only for capabilities actually demonstrated.
- Modify: `manifests/source_inventory.json` through the canonical generator.
- Modify: `ROADMAP.md` / recovery docs only to reflect proven state.

- [ ] Run full pytest and strict `review_20_for_2.py --strict`.
- [ ] Run source-freeze verification and diff hygiene.
- [ ] On ATHENA, re-probe the connected CLT handset and generate evidence packets for every newly proven capability.
- [ ] Promote only exact hardware-proven rows; keep recovery execution pending if the transport is not yet certified.
- [ ] Push the branch and open a focused PR; cancel packaging-only CI after meaningful Windows/source stages are proven.
- [ ] Merge only after source/Gateway/security/review gates are clean.

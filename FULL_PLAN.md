# TECHGUYTOOL Huawei — Full Plan and Recovery Authority

**Document version:** 1.0.0  
**Status:** OWNER-ACCEPTED PLANNING AUTHORITY  
**Effective date:** 2026-08-04  
**Product name:** TECHGUYTOOL Huawei  
**GitHub authority:** https://github.com/jaydumisuni/TECHGUYTOOL-Huawei/blob/main/FULL_PLAN.md  
**Google Drive recovery mirror:** https://docs.google.com/document/d/1q2_Ym9CqzVPAsPcI-0w4JLIQzEWRbWhjjY8CK-5nxGw/edit  
**Planning folder:** https://drive.google.com/drive/folders/13G5NKZ1al7LvZ6PaQJDEyx2dkDaYCE4e

---

## 0. Purpose of this document

This is the complete project handoff, planning authority, architecture boundary, build order, and recovery memory for TECHGUYTOOL Huawei.

A new chat, AI system, engineer, programmer, reviewer, or technician must be able to read this file and continue without the owner repeating the project history.

This file prevents drift. It defines:

- what TECHGUYTOOL Huawei is;
- what has already been proven;
- which donor work made the project possible;
- the exact authority boundaries between Xray, governors, and executors;
- the correct Huawei repair sequence;
- the first production recipe;
- the implementation phases and exit gates;
- the proof required before any operation is called supported;
- the rules for improving Kirin Xray and promoting mature capability into TTG Device X-Ray.

This document authorizes implementation. It does **not** by itself prove that all repair adapters, hardware lanes, Windows packaging, or model coverage are complete.

---

## 1. Source-of-truth and recovery order

### 1.1 Canonical authority

GitHub is the implementation and planning source of truth:

1. `TECHGUYTOOL-Huawei/FULL_PLAN.md`
2. Current source on the repository default branch
3. Versioned recipes, contracts, tests, and proof records in the repository

Google Drive is the recovery and handoff mirror:

1. This native Google Doc
2. The Huawei planning folder
3. Large evidence files, firmware references, logs, and archives that do not belong in Git

The THETECHGUY Recovery Master contains a pointer to this plan.

Chat history is context only. It must never override the canonical plan or current repository evidence.

### 1.2 Conflict rule

If GitHub and Google Drive disagree:

- stop implementation;
- compare revisions;
- recover the most recently owner-approved content;
- update both locations in the same change;
- record the correction in Recovery Master.

No engineer should silently choose one interpretation.

### 1.3 Update rule

Every meaningful architecture or phase change must update:

- this GitHub file;
- the Drive mirror;
- the plan version and change log;
- Recovery Master when the recovery route or current milestone changes.

Implementation progress belongs in project status files or repository issues/PRs. This document remains the stable full plan.

---

## 2. Current project boundary

### 2.1 Authoritative supplied source

The full source supplied by the owner is authoritative. There is no missing Athena source to recover.

The owner deliberately removed oversized runtime artifacts, including large firmware and SUPER data, so the archive could be transferred. Those files are external inputs, not missing source code.

Authoritative evidence files:

- Huawei Revive archive / P10 and P30 working material:  
  https://drive.google.com/file/d/1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs/view
- VOG-L29 recovery chat and handoff:  
  https://drive.google.com/file/d/1rIu3HdbRhR70G1VQCs4Y0VFQwI5ImwWJ/view
- Specialist Kirin/Xray repository:  
  https://github.com/jaydumisuni/kirin
- Consolidated read-only Xray repository:  
  https://github.com/jaydumisuni/TTG-Device-X-Ray
- Huawei tool repository:  
  https://github.com/jaydumisuni/TECHGUYTOOL-Huawei

### 2.2 Large external artifacts

The following remain outside normal source control:

- retail firmware packages;
- board firmware packages;
- SUPER images and extracted dynamic-partition data;
- device backups;
- customer evidence;
- loader/programmer/DA binaries where licensing or size requires external custody;
- operation journals containing sensitive device identifiers.

Source control stores manifests, hashes, provenance, required paths, compatibility rules, and proof records—not uncontrolled opaque binaries.

### 2.3 UI authority

The approved TECHGUYTOOL Huawei UI already exists.

This plan does not authorize a redesign.

Approved UI images are retained under:

`resources/expected ui/`

New functions must use the established QML visual system, spacing, typography, glass surfaces, navigation, dialogs, and status language.

---

## 3. Product purpose

TECHGUYTOOL Huawei is a deterministic, evidence-driven Huawei service and recovery tool.

The technician selects the repair objective, for example:

- read device information;
- repair main version / verlist;
- repair or normalize OEMINFO;
- restore branding;
- repair approved FRP or Huawei ID conditions;
- service bootloader;
- repair IMEI or serial only under an authorized profile;
- backup or restore;
- flash retail, downgrade, or board firmware;
- perform a reviewed board-recovery recipe.

The technician should not have to guess:

- which partition to write;
- which mode is required;
- which loader is compatible;
- whether the connected endpoint is the same phone;
- whether a command result means the phone is repaired;
- whether it is safe to reboot;
- whether stock Fastboot may be restored.

The system must understand first, decide second, execute narrowly, and verify independently.

---

## 4. Proven donor lineage

## 4.1 P10Revive is the golden workflow donor

Most of the successful P30 recovery became possible because the old P10Revive package supplied the complete working sequence.

P10Revive proved this workflow theorem:

```text
enter and retain the service environment
→ flash the required base/device stack
→ install or reach a compatible maintenance environment
→ write the complete target OEMINFO identity
→ restore version and regional state
→ continue the target retail firmware
→ restore stock recovery/Fastboot only at finalization
```

The P10 package referenced small files such as `verlist.img`, `curver.img`, `package_type.img`, and `sha256rsa.img`, but those files were absent from the studied package. The working repair came from the complete OEMINFO write.

Therefore:

> A named metadata file is not automatically a writable partition image. The successful workflow must be understood as a whole.

## 4.2 P30/VOG adaptation

The P10 theorem was adapted rather than copied blindly:

- P10/VTR partition order was replaced by the official VOG board XML.
- The VOG board workflow was parsed into 103 ordered operations.
- P10 OEMINFO was replaced by a model-correct 96 MiB VOG OEMINFO structure.
- The 96 MiB image contains two 48 MiB copies.
- Device-specific board records are preserved rather than blindly replaced.
- VTR C432 identity was replaced with VOG-L29 / `hw` / `meafnaf` / C185.
- P10 recovery and binary artifacts are never reused as if they were VOG artifacts.
- Base, CUST, PRELOAD, VERSION, PRELOAD, SUPER, recovery, and final Fastboot stages are derived from the exact target package set.

## 4.3 Proven P30 failure mechanism

The P30 problem was not merely “firmware failed.”

The evidence established:

```text
VERSION.img was valid
VERSION write completed
MAIN VERSION remained missing
the P30 exposed no usable writable verlist partition
small BASE/CUST/PRELOAD VERLIST files were package metadata
the required version identity was missing from OEMINFO
```

The missing OEMINFO version state prevented the complete target firmware process from finishing. The device could not boot because the required remaining stages had not completed.

After the OEMINFO-derived main-version/verlist state was restored:

- target version identity became readable;
- VERSION and PRELOAD stages completed;
- the remaining firmware continued;
- SUPER was written in sparse chunks;
- stock recovery and Fastboot were restored at finalization;
- the device booted.

The remaining issue was a smaller branding/model identity normalization task.

## 4.4 Proven sequencing mistake

During investigation, the device was restored or rebooted into stock Fastboot too early. It returned to a locked state and lost the service capability needed to complete the repair.

Canonical rule:

> If an unresolved repair still requires unlocked Factory/Board-Service Fastboot, preserve that mode. Do not reboot or restore stock Fastboot until Xray verifies the release conditions.

---

## 5. Frozen authority architecture

```text
Technician intent
        ↓
TTG Device Gateway
        ↓
Specialist Xray
        ↓
Repair Decision Corps
        ↓
Repair Governor
        ↓
Bounded Executor
        ↓
Specialist Xray verification
        ↓
Inquiry Governor
        ↓
Xray Knowledge Workshop
        ↓
Specialist Xray improvement
        ↓
Mature capability promotion to TTG Device X-Ray
```

No model is required in the repair authority path.

---

## 6. Xray authority

## 6.1 Xray is always read-only

This applies to:

- Kirin Xray;
- TTG Device X-Ray;
- future Qualcomm, MTK, Apple, Samsung, and UNISOC specialist providers.

Xray may:

- observe;
- identify;
- correlate;
- challenge;
- classify;
- diagnose;
- recommend;
- predict;
- certify evidence dimensions;
- verify outcomes.

Xray may never:

- flash;
- erase;
- format;
- unlock;
- relock;
- reboot;
- upload a destructive loader;
- write OEMINFO;
- modify a partition;
- grant itself write authority.

## 6.2 Why Xray exists

Xray gives the executor purpose and precision so the executor does not act blindly.

It must understand:

- which physical phone is connected;
- whether endpoints across re-enumeration belong to the same device;
- model, board, SoC, region, vendor/country, firmware family, and branding evidence;
- current mode and actual capabilities;
- contradictions such as `get-bootinfo` versus `get-lockstate`;
- partition inventory and storage layout;
- firmware package structure;
- what is missing;
- why a previous action did not resolve the condition;
- what evidence proves success.

A command returning `OKAY` is not a repair verdict.

## 6.3 Kirin Xray responsibility

Kirin Xray is the deep Huawei/Kirin specialist proving ground.

It must become extremely capable before capabilities are promoted upward.

Required Huawei evidence depth:

- MTP;
- ADB and authorization state;
- normal Fastboot;
- Recovery;
- Upgrade Mode;
- HUAWEI USB COM 1.0;
- Factory/Board-Service Fastboot;
- physical-session continuity;
- partition inventory;
- UPDATE.APP parsing;
- official board XML interpretation;
- Base/CUST/PRELOAD relationship;
- board versus retail firmware;
- model/vendor/country/build identity;
- OEMINFO version evidence;
- main-version/verlist diagnosis;
- branding mismatch diagnosis;
- pre/post device twins;
- stable error codes.

## 6.4 TTG Device X-Ray responsibility

TTG Device X-Ray is the consolidated read-first intelligence core for the future combined tool.

It benefits from mature specialist capability packs.

It does not replace specialist development. Kirin Xray first proves Huawei understanding; TTG Device X-Ray later receives the reviewed provider, rules, fixtures, error definitions, and verification logic.

Execution code never moves into Xray.

---

## 7. Repair Decision Corps and Repair Governor

## 7.1 Why the governor is required

During the successful P30 investigation, GPT temporarily performed this missing role:

- interpreted Xray evidence;
- recognized the incomplete causal explanation;
- preserved the necessary mode;
- selected the next bounded action;
- stopped incorrect retries.

That behavior must become deterministic software.

## 7.2 Deterministic Decision Corps

The Decision Corps uses ordinary Python/Rust logic and declarative recipes—not an LLM.

Officers:

1. Identity Officer
2. Mode Officer
3. Firmware Officer
4. Artifact Officer
5. Recovery Officer
6. Route Planner
7. Safety Challenger
8. Verification Judge
9. Repair Governor

Each officer evaluates the same typed evidence independently.

Identity, Recovery, Safety, and Verification have veto authority. A majority cannot override a hard safety block.

## 7.3 Repair Governor duties

The Repair Governor:

- holds technician intent;
- selects an approved recipe;
- maintains operation stage;
- creates and enforces mode leases;
- creates execution leases;
- blocks premature reboot/finalization;
- requests Testpoint when required;
- authorizes one executor stage at a time;
- waits for Xray verification;
- advances, retries, escalates, or stops.

It never touches the device directly.

---

## 8. Inquiry Governor and continuous improvement

## 8.1 Purpose

The Inquiry Governor prevents blind confidence in Xray.

It compares:

```text
Xray predicted outcome
vs
Executor raw result
vs
Xray post-operation evidence
```

If those disagree, it raises a structured knowledge gap.

Example:

```text
Prediction:
Writing VERSION restores MAIN VERSION.

Executor:
VERSION write accepted and readback matched.

Post-Xray:
MAIN VERSION still missing.
```

Result:

```text
EXPECTED_RESULT_NOT_OBSERVED
XRAY_EXPLANATION_INCOMPLETE
ADDITIONAL_READ_ONLY_EVIDENCE_REQUIRED
```

## 8.2 Inquiry Corps

1. Prediction Auditor
2. Evidence Completeness Officer
3. Contradiction Officer
4. Probe Planner
5. Hypothesis Officer
6. Challenger
7. Learning Judge
8. Inquiry Governor

The Probe Planner may request only registered read-only probes.

## 8.3 Knowledge lifecycle

```text
OBSERVED
→ QUESTIONED
→ CANDIDATE
→ REPLAY_SUPPORTED
→ HARDWARE_SUPPORTED
→ SPECIALIST_APPROVED
→ TTG_PROMOTED
```

Safe automatic promotion:

- read-only parser improvement: after replay and regression proof;
- new diagnostic rule: specialist canary after replay proof;
- verification requirement: replay plus hardware proof;
- write target, offset, destructive recipe, or expanded authority: never automatic.

Every gap packet records origin evidence, hashes, prediction, result, failed explanations, requested probes, replay results, hardware proof, and limitations.

---

## 9. TTG Device Gateway

Borrow OpenClaw’s operating structure, not its model agent.

The Rust Gateway is an always-running control plane that owns:

- physical-device sessions;
- operation sessions;
- typed event bus;
- provider/plugin lifecycle;
- ordered policy hooks;
- SQLite durable state;
- evidence journal;
- worker supervision;
- watchdogs;
- crash recovery;
- diagnostics;
- capability allowlists.

The UI is a client.

```text
UI closes or crashes
→ Gateway remains alive
→ Xray session remains pinned
→ operation stage and leases remain known
→ UI reconnects to the same operation
```

OpenClaw patterns to borrow:

- Gateway/control-plane structure;
- isolated per-device sessions;
- typed lifecycle hooks;
- plugin manifests and eligibility;
- durable job/run history;
- `doctor` diagnostics;
- direct deterministic command dispatch;
- reviewed knowledge workshop;
- capability-restricted workers.

Do not borrow:

- prompt-based repair authority;
- unrestricted shell execution;
- autonomous public plugin installation;
- conversational memory as device evidence;
- model voting as write authorization.

---

## 10. Shared contracts

Python and Rust must validate equivalent versioned schemas.

Required contracts:

- `PhysicalDeviceSession`
- `EndpointObservation`
- `DeviceEvidence`
- `DeviceTwin`
- `OperationRequest`
- `RepairRecipe`
- `RecipeCandidate`
- `DecisionVerdict`
- `ModeLease`
- `ExecutionLease`
- `ExecutorResult`
- `VerificationResult`
- `KnowledgeGap`
- `LearningProposal`
- `CapabilityPack`
- `ArtifactManifest`
- `RecoveryPlan`

Every contract includes:

- schema version;
- producing component;
- timestamp;
- physical-session ID where applicable;
- evidence hashes;
- confidence/evidence state;
- expiry where applicable;
- authority boundary.

Malformed, stale, reused, mismatched, or contradictory contracts fail closed.

---

## 11. Correct routing and service entry

The technician selects the repair—not a random transport.

```text
selected operation
→ Xray inspects the current phone
→ use an approved direct route if it can perform the operation
→ if direct routes are unavailable or insufficient, require Testpoint
→ identify the chipset-specific service entry
→ validate the exact service artifact
→ establish the required service environment
→ automatically resume the original operation
```

Direct routes:

- MTP where the exact operation is supported;
- authorized ADB;
- normal Fastboot where the exact operation is supported.

Testpoint entries:

```text
Kirin
→ HUAWEI USB COM 1.0
→ exact signed Kirin loader
→ Factory/Board-Service Fastboot

Qualcomm
→ Qualcomm HS-USB QDLoader 9008
→ exact Firehose programmer
→ verified Firehose service session

MediaTek
→ MediaTek BootROM / Preloader
→ exact Download Agent
→ verified DA service session
```

Upgrade Mode is separate. It is used only by firmware/recovery recipes that explicitly support it. It is not the first route and does not replace Testpoint when Factory/Board-Service access is required.

---

## 12. Mode leases and execution leases

## 12.1 Mode lease

Example for the P30 repair:

```json
{
  "mode": "board_service_fastboot",
  "reason": "OEMINFO/main-version repair and firmware continuation unresolved",
  "reboot_allowed": false,
  "stock_fastboot_restore_allowed": false,
  "release_conditions": [
    "main_version_verified",
    "remaining_firmware_stages_completed",
    "target_boot_environment_ready"
  ]
}
```

No code path may reboot or restore stock Fastboot while this lease is active.

## 12.2 Execution lease

An execution lease binds:

- one certified physical session;
- one recipe hash;
- one adapter version;
- exact loader/programmer/DA hashes;
- exact firmware hashes;
- allowed partitions;
- allowed records or byte ranges;
- maximum write size;
- expected starting mode;
- current stage;
- reboot permission;
- expiry;
- single-use status.

Rust rejects:

- another phone;
- another artifact;
- another partition;
- unexpected offset/range;
- expired or reused lease;
- wrong mode;
- prohibited reboot.

---

## 13. Bounded executor architecture

## 13.1 Python responsibility

Python owns:

- evidence normalization;
- deterministic officers;
- route planning;
- workflow state machines;
- recipe compilation;
- package coordination;
- worker orchestration;
- technician explanations;
- replay and simulation;
- error-code generation.

## 13.2 Rust responsibility

Rust owns:

- USB/serial framing;
- binary parsing;
- hashing and CRC;
- loader transfer;
- partition I/O;
- byte-range enforcement;
- execution-lease validation;
- crash-safe journaling;
- cancellation boundaries;
- readback verification;
- process containment.

The executor receives a narrow instruction, never “repair the phone.”

Example:

```text
Write these reviewed version-identity records
to this certified physical session
using this artifact set
inside this bounded authority
while Board-Service Fastboot remains active
without rebooting
then return raw readback evidence.
```

---

## 14. Firmware intelligence

A selected file existing is not adequate firmware validation.

The firmware layer must understand:

- Base/CUST/PRELOAD relationships;
- board firmware versus retail firmware;
- downgrade packages;
- UPDATE.APP contents;
- official board XML;
- model and board target;
- vendor/country and region;
- build number and C-version;
- customization/preload version;
- anti-rollback and version constraints;
- partition payloads versus descriptive metadata;
- required and optional components;
- package hashes and provenance;
- sparse SUPER structure;
- missing or contradictory components.

A package must be rejected with specific evidence, for example:

```text
TARGET_MODEL_MISMATCH
TARGET_REGION_MISMATCH
BASE_CUST_PRELOAD_RELATIONSHIP_INVALID
REQUIRED_PARTITION_PAYLOAD_MISSING
BOARD_PACKAGE_REQUIRED
ANTI_ROLLBACK_CONSTRAINT_UNRESOLVED
ARTIFACT_HASH_MISMATCH
```

---

## 15. Device and Testpoint catalogue

The catalogue connects:

```text
marketing name
→ exact model/variant
→ board
→ SoC
→ supported USB modes
→ Testpoint reference
→ loader/programmer/DA manifest
→ firmware regions
→ supported operations
→ known hazards
→ proof status
```

Unknown or similar-looking models remain unsupported.

Testpoint policy:

- no SigmaKey scraping;
- no automatic web lookup;
- no similar-model substitution;
- library remains blank until the owner supplies the approved list;
- every image record identifies exact model, variant, board side, chipset, source, hash, expected interface, and verification status.

The existing Testpoint popup remains in the approved UI and displays only owner-approved local references.

---

## 16. Error-code architecture

Error codes belong to separate authorities.

### 16.1 Xray diagnosis

Examples:

- `XR-HUA-VERSION-001 MAIN_VERSION_RECORD_MISSING`
- `XR-HUA-PARTITION-002 WRITABLE_VERLIST_PARTITION_NOT_PRESENT`
- `XR-HUA-IDENTITY-003 BRANDING_IDENTITY_MISMATCH`
- `XR-HUA-SECURITY-004 LOCK_STATE_EVIDENCE_CONFLICT`
- `XR-SESSION-005 PHYSICAL_DEVICE_CONTINUITY_LOST`

### 16.2 Planner/Governor decisions

- `DEC-DIRECT-101 ANDROID_CHARGE_ONLY_DETECTED`
- `DEC-FASTBOOT-102 NORMAL_FASTBOOT_INSUFFICIENT`
- `DEC-TESTPOINT-103 SERVICE_ENTRY_REQUIRED`
- `DEC-ARTIFACT-104 COMPATIBLE_SERVICE_ARTIFACT_MISSING`
- `DEC-REBOOT-105 REBOOT_BLOCKED_BY_ACTIVE_MODE_LEASE`

### 16.3 Executor results

- `EXEC-WRITE-201 PARTITION_WRITE_ACCEPTED`
- `EXEC-WRITE-202 PARTITION_WRITE_REJECTED`
- `EXEC-LOADER-203 LOADER_TRANSFER_COMPLETED`
- `EXEC-TRANSPORT-204 DEVICE_DISCONNECTED_DURING_STAGE`
- `EXEC-READBACK-205 READBACK_CAPTURED`

### 16.4 Verification

- `VERIFY-HASH-301 READBACK_HASH_MATCH`
- `VERIFY-VERSION-302 MAIN_VERSION_RESTORED`
- `VERIFY-IDENTITY-303 TARGET_BRANDING_CONFIRMED`
- `VERIFY-REPAIR-304 REPAIR_CONFIRMED`
- `VERIFY-PARTIAL-305 CORE_REPAIR_COMPLETE_BRANDING_REMAINS`

### 16.5 Inquiry

- `INQ-PREDICTION-401 EXPECTED_RESULT_NOT_OBSERVED`
- `INQ-EVIDENCE-402 REQUIRED_EVIDENCE_MISSING`
- `INQ-KNOWLEDGE-403 XRAY_EXPLANATION_INCOMPLETE`
- `INQ-PROBE-404 ADDITIONAL_READ_ONLY_PROBE_REQUIRED`

A successful write never automatically becomes a successful repair.

---

## 17. Golden Huawei revive workflow

Encode P10Revive as a reusable theorem:

```yaml
id: huawei-revive-golden-v1

invariants:
  - preserve_service_environment_until_identity_repair_verified
  - complete_oeminfo_identity_before_retail_finalization
  - do_not_treat_package_metadata_as_partition_images
  - stock_fastboot_is_finalization_only
  - verify_target_identity_before_remaining_firmware
  - stop_on_first_unexplained_failure
  - reread_device_after_every_stage
```

P10-specific binaries, partition names, recovery images, offsets, and C432 identity remain in the VTR profile. They are not inherited by VOG.

VOG inherits the workflow law only.

---

## 18. First production recipe: VOG-L29 C185

This is the first complete vertical lane and the first proof of the whole architecture.

### 18.1 Target transition

```text
VOG-AL00 board/service state
→ VOG-L29 C185 target identity
→ restore main version/verlist
→ continue target Base/CUST/PRELOAD firmware
→ complete SUPER
→ boot
→ restore branding/model identity
→ verify
→ stock finalization
```

### 18.2 Required evidence

Before writes:

- one pinned physical-device session;
- VOG/Kirin 980 evidence;
- current service mode certified;
- exact board and target profile;
- exact Base, CUST, and PRELOAD package identity;
- loader hash;
- OEMINFO backup;
- rollback artifacts;
- target firmware hashes;
- storage/partition inventory;
- active no-reboot mode lease.

### 18.3 OEMINFO stage

The recipe must:

- derive target identity from the exact firmware;
- construct/validate the 96 MiB VOG OEMINFO format;
- handle both 48 MiB copies;
- preserve device-specific board records;
- avoid blindly replacing unrelated identity;
- restore the required VOG-L29 C185 version state;
- read back and verify before continuing.

### 18.4 Firmware continuation

After Xray confirms main-version/verlist restoration:

- continue Base/CUST/PRELOAD stages;
- write VERSION/PRELOAD where required;
- perform the reviewed target partition order;
- write/rebuild SUPER using the validated sparse strategy;
- preserve service mode until all required stages complete.

The proven case used a large SUPER transfer divided into sparse chunks. The production recipe must derive the exact chunk set from the validated artifact rather than hard-code an assumed count for every package.

### 18.5 Finalization

Only after required firmware stages and target identity are verified:

- restore target stock recovery;
- restore target stock Fastboot;
- release the service-mode lease;
- reboot intentionally;
- verify normal boot;
- create a final Xray device twin.

### 18.6 Branding normalization

Branding is a separate stage.

The tool must distinguish:

```text
CORE_REPAIR_CONFIRMED
BOOT_CONFIRMED
VERSION_STATE_RESTORED
BRANDING_NORMALIZATION_REQUIRED
```

from:

```text
FULL_REPAIR_CONFIRMED
```

Restore Branding should modify only reviewed identity fields proven incorrect. It must not repeat complete board recovery on an already working phone.

---

## 19. Specialist capability promotion

Kirin Xray publishes versioned read-only packs:

- `kirin-xray-provider-pack`
- `kirin-xray-knowledge-pack`
- `kirin-xray-error-pack`
- `kirin-xray-replay-pack`
- `kirin-xray-verification-pack`

Promotion into TTG Device X-Ray includes:

- providers;
- evidence schemas;
- session-correlation rules;
- firmware parsers;
- error definitions;
- contradiction rules;
- verification rules;
- replay fixtures;
- proven model records;
- explicit limitations.

Promotion excludes:

- partition writes;
- loader execution;
- OEMINFO construction;
- firmware flashing;
- repair recipes that change devices.

---

## 20. Implementation phases and exit gates

## Phase 1 — Freeze source and external-artifact manifests

Tasks:

- inventory the supplied full source;
- remove obsolete transfer/import material;
- hash included source and proof files;
- declare intentionally omitted large artifacts;
- create clean source checkpoint.

Exit gate:

- every source/proof file has provenance;
- omitted firmware/SUPER data is represented by manifests;
- no Athena recovery is requested.

## Phase 2 — Shared Python/Rust contracts

Implement the contracts in Section 10.

Exit gate:

- both languages serialize, validate, and reject the same malformed/stale cases.

## Phase 3 — TTG Device Gateway

Build persistent sessions, event bus, hooks, plugins, journal, watchdog, diagnostics, and UI reconnection.

Exit gate:

- UI restart does not lose physical-device identity or operation stage.

## Phase 4 — Harden Kirin Xray

Implement the complete read-only Huawei evidence lane and replay the P10/P30 evidence.

Exit gate:

- Kirin Xray explains the original P30 failure and mode hazard without write access.

## Phase 5 — Repair Decision Corps

Implement all deterministic officers and veto rules.

Exit gate:

- historical replay blocks premature stock-Fastboot restoration.

## Phase 6 — Mode and execution leases

Implement Rust-enforced mode, artifact, session, range, and reboot constraints.

Exit gate:

- wrong device/artifact/partition/mode/reused lease is rejected.

## Phase 7 — Bounded executor framework

Implement one-stage workers, journaling, cancellation, backup, readback, and raw results.

Exit gate:

- executors cannot exceed the lease even if Python requests it.

## Phase 8 — P10 golden theorem

Encode P10 ordering and invariants separately from VTR-specific data.

Exit gate:

- VOG inherits no VTR binary, offset, or identity value.

## Phase 9 — VOG-L29 C185 recipe

Complete the exact first production recipe, including branding.

Exit gate:

- simulation and replay pass;
- then physical VOG proof passes end to end.

## Phase 10 — Inquiry Governor

Implement prediction comparison, gap packets, read-only probe planning, and learning candidates.

Exit gate:

- unexplained outcomes create a structured gap instead of a generic retry.

## Phase 11 — Xray Knowledge Workshop

Implement quarantine, replay, challenge, canary, hardware proof, and promotion lifecycle.

Exit gate:

- read-only understanding can improve without expanding write authority.

## Phase 12 — Kirin capability packs

Package and version specialist providers, rules, errors, fixtures, and verification.

Exit gate:

- TECHGUYTOOL Huawei can consume packs without importing Kirin executor code.

## Phase 13 — TTG Device X-Ray promotion

Promote mature Huawei/Kirin read-only capability.

Exit gate:

- TTG Device X-Ray independently explains the VOG case from promoted capability.

## Phase 14 — Qualcomm and MediaTek expansion

After the Kirin vertical lane is proven:

Qualcomm:

- 9008 observation;
- Sahara;
- exact Firehose validation;
- read-only storage/GPT proof;
- bounded write proof later.

MediaTek:

- BootROM/Preloader observation;
- exact DA validation;
- auth/SLA/DAA state;
- read-only partition proof;
- bounded write proof later.

Exit gate:

- each model/operation pair earns its own proof level.

## Phase 15 — Windows packaging and certification

Build and sign `TECHGUYTOOL_Huawei.exe`.

Exit gate:

- clean Windows servicing machine;
- drivers;
- one-file packaging;
- runtime extraction;
- crash recovery;
- signed binary;
- checksums;
- physical proof matrix.

---

## 21. Physical proof matrix

Minimum required proof:

- VOG/Kirin 980 full recovery and branding;
- historical P10/VTR regression;
- MTP direct route;
- authorized ADB direct route;
- normal Fastboot direct route;
- Recovery detection;
- Upgrade Mode detection and recipe eligibility;
- Kirin Testpoint → HUAWEI USB COM 1.0;
- loader → Factory/Board-Service Fastboot;
- active mode lease blocking reboot;
- wrong loader rejection;
- wrong firmware/region rejection;
- multiple-device rejection;
- interrupted OEMINFO stage recovery;
- interrupted SUPER write recovery;
- stock finalization only after release conditions;
- UI restart recovery;
- Gateway restart recovery;
- Qualcomm 9008 read-only proof;
- MediaTek BROM/Preloader read-only proof;
- clean Windows driver/install proof.

Only proven model/operation combinations are enabled in production.

---

## 22. UI behavior

The UI exposes intent and evidence-backed state.

Expected statuses:

- Inspecting device
- Direct route available
- Direct route insufficient
- Testpoint required
- Waiting for HUAWEI USB COM 1.0
- Waiting for Qualcomm QDLoader 9008
- Waiting for MediaTek BootROM/Preloader
- Validating service artifact
- Establishing service environment
- Factory/Board-Service mode confirmed
- Mode protected — reboot blocked
- Backing up
- Executing bounded stage
- Reading back
- Verifying result
- Continuing firmware
- Writing SUPER
- Finalization permitted
- Branding normalization required
- Repair confirmed
- Unsupported
- Need artifact
- Need technician action
- Blocked by conflicting evidence

Every visible state must map to a real Gateway, Xray, Governor, or Executor event.

No fake progress and no fake success.

---

## 23. Windows release boundaries

Bundle or resolve:

- PySide6/Qt;
- QML/resources;
- Rust Gateway;
- Xray capability packs;
- Decision and Inquiry Corps;
- bounded executors;
- approved ADB/Fastboot utilities;
- driver manifests/installers;
- recipes;
- device profiles;
- error packs.

Store outside the executable:

- firmware;
- SUPER images;
- customer backups;
- testpoint catalogue images;
- operation journals;
- registration/license data;
- downloaded artifacts.

Runtime data belongs under controlled THETECHGUY application-data directories with access controls and cleanup policy.

---

## 24. Non-negotiable “do not” rules

Do not:

- redesign the approved UI;
- treat a successful command as a successful repair;
- let Xray write;
- let the executor choose its own target;
- use a model as repair authority;
- reboot while an active mode lease forbids it;
- restore stock Fastboot early;
- assume a metadata file is a partition image;
- infer support from a similar model;
- use a loader/programmer/DA without exact compatibility and hash;
- substitute another model’s Testpoint image;
- scrape SigmaKey;
- auto-promote destructive knowledge;
- ship opaque large binaries without manifests/provenance;
- call an operation supported before physical proof;
- let another connected device inherit the current session;
- let chat history override this plan.

---

## 25. Immediate implementation order

1. Publish and freeze this plan in Drive, Recovery Master, and GitHub.
2. Inventory the supplied source and external-artifact manifests.
3. Implement shared contracts.
4. Build TTG Device Gateway.
5. Harden Kirin Xray against P10/P30 evidence.
6. Build the deterministic Repair Decision Corps.
7. Implement mode and execution leases.
8. Encode P10Revive as the golden workflow theorem.
9. Finish Kirin bounded executors.
10. Complete the VOG-L29 C185 recipe.
11. Physically prove the VOG lane including Restore Branding.
12. Add Inquiry Governor.
13. Add Xray Knowledge Workshop.
14. Publish Kirin capability packs.
15. Promote mature capability into TTG Device X-Ray.
16. Expand Qualcomm and MediaTek lanes.
17. Build, test, sign, and release TECHGUYTOOL Huawei.

---

## 26. First milestone definition

The first milestone is complete only when:

> A technician selects Repair Main Version/Verlist for a VOG-L29 target; Kirin Xray certifies the phone and explains the missing OEMINFO version state; the Repair Governor preserves Board-Service Fastboot and blocks premature reboot; the bounded executor writes only the approved VOG-L29 C185 identity under a valid lease; Xray verifies main version; the governor permits the remaining Base/CUST/PRELOAD and SUPER stages; the device boots; Restore Branding completes the remaining model identity; Xray produces a final certified device twin; and the Inquiry Governor records any prediction mismatch for specialist improvement.

Passing software tests alone does not complete this milestone. Physical evidence is required.

---

## 27. Recovery quick start for a new chat or engineer

Before working:

1. Read this file completely.
2. Confirm the plan version and current GitHub revision.
3. Read the latest repository status and open PRs.
4. Read the P10Revive study and VOG recovery evidence.
5. Read current Kirin Xray and TTG Device X-Ray boundaries.
6. Identify the active phase and its exit gate.
7. Recover evidence before reasoning.
8. Do not assume previous chats completed implementation.
9. Make the smallest phase-correct change.
10. Review, freeze, prove, then submit.

When asked “what is next,” answer from the active phase—not from general ideas.

---

## 28. Change log

### 1.0.0 — 2026-08-04

- Created the canonical TECHGUYTOOL Huawei full plan.
- Recorded P10Revive as the golden workflow donor.
- Recorded the proven P30/VOG failure and recovery mechanism.
- Froze Xray as read-only.
- Added deterministic Repair Decision Corps and Repair Governor.
- Added Inquiry Governor and Xray Knowledge Workshop.
- Added OpenClaw-inspired Gateway patterns without model authority.
- Froze direct-route → Testpoint → service-environment routing.
- Defined mode/execution leases.
- Defined the VOG-L29 C185 first production recipe.
- Defined specialist Kirin Xray → TTG Device X-Ray promotion.
- Defined implementation phases, exit gates, proof matrix, and release boundaries.

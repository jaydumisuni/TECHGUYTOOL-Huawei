# TECHGUYTOOL Huawei — Current Execution Roadmap

**Status:** ACTIVE CURRENT-WORK AUTHORITY  
**Effective:** 2026-08-16  
**Last reconciled:** 2026-09-04
**Repository:** `jaydumisuni/TECHGUYTOOL-Huawei`

## 0. Purpose

This file is the current execution roadmap and pickup authority for TECHGUYTOOL Huawei.

It exists so a new chat, AI, programmer, reviewer, or technician can continue the project without reconstructing intent from conversation history.

It does **not** replace `FULL_PLAN.md`.

- `FULL_PLAN.md` owns the architecture, invariants, authority boundaries, donor lineage, repair theorem, contracts, and original Phase 1–15 design.
- `ROADMAP.md` owns the current project state, next execution milestones, machine/build route, proof sequence, and pickup rules.
- `manifests/*.receipt.json` own exact proof claims.
- `resources/expected ui/README.md` owns the approved visual contract.
- Chat history is context only.

If status text conflicts, prefer the newest evidence-backed receipt and this roadmap. If architecture conflicts, stop and reconcile against `FULL_PLAN.md`; do not silently invent a new architecture.

---

## 1. Current frozen truth

### 1.1 Software state

The Phase 1–15 **software scope is complete**. Do not create a new software phase merely because physical certification is still open.

Current `main` recovery point before this roadmap:

```text
fd3f7bb1587b65faaa7d37e0057683dcb07975ed
```

That commit published the final Phase 15 UI closeout receipt.

Final approved software/UI authority recorded by `manifests/phase15_ui_closeout.receipt.json`:

```text
status                  FROZEN
frozen source revision  a5109f643b90ae14b8c9d407622f7039c36edad0
source-freeze run       31744140635
software proof run      31744325728  PASS
Windows run             31744325830  PASS
visual QA               PASS
source QML startup      PASS
packaged QML startup    PASS
forced-close/restart    PASS
CI test signing         PASS
artifact id             9198694460
executable              TECHGUYTOOL_Huawei.exe
SHA-256                 b0709e2d46c793609456877f55fdecc6620382ea55777684cc4b9c5199f14080
```

The approved UI is frozen. Do not redesign it while performing certification or coverage work.

### 1.1A Current owner-machine source authority

The historical Phase 15 UI closeout receipt above remains valid evidence for its recorded CI candidate, but it is no longer the newest source revision. ATHENA owner-machine review exposed and corrected dependency, source-freeze portability and visual-comparator defects without redesigning the approved UI.

Current merged authorities are:

```text
Huawei main merge              ac3c460cf1aaf9165bd7eabbd0b3bd2b6c692eab
proven source head             1010dbe22fe10a03142a375547f99e075a413551
Builder main merge             440d9e59ac062a83ff82d230ed2754138e434ed3
Builder reviewed head          dcba3263f4982071221dc66d61e69dcf2f059257
owner pytest                   207/207 PASS
owner strict review            40/40 PASS
source QML construction        PASS
source visual capture          7/7 at 1586x992, zero QML warnings
```

The current Phase 15 Windows packaging receipt deliberately remains `UNFROZEN` with `windows_ci=PENDING` and `ci_test_signing=PENDING`. Packaging/signing is a later release-artifact confirmation and must not be confused with source/UI correctness.

### 1.2 Production state

Software completion does **not** mean every Huawei model/operation is physically certified.

Until applicable physical proof and production signing exist:

```text
production_enabled = false
production_release_status = EXTERNAL_CERTIFICATION_PENDING
```

Only evidence-backed model/operation pairs may become supported.

### 1.3 Historical P10/P30 evidence

P10Revive and the historical P30/VOG work are donor/proof lineage.

They taught and proved important Kirin/Xray/repair-sequencing behavior, including preservation of the service environment, complete OEMINFO/version-state reasoning, finalization ordering, and the distinction between a successful write and a successful repair.

**The old P30 handset is not a current project target and is not required to finish TECHGUYTOOL Huawei.**

Do not tell a future session to recover, reboot, repair, or certify that retired handset.

---

## 2. Frozen architecture boundary

The system remains:

```text
Technician intent
    ↓
TTG Device Gateway
    ↓
Specialist Xray (read-only)
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
Specialist improvement / mature read-only promotion
```

Non-negotiable boundaries:

- Xray is read-only understanding and verification.
- The executor never chooses its own target or expands authority.
- A command succeeding is not proof that the repair succeeded.
- Reboot/finalization is governed by evidence and active leases.
- Similar-looking models do not inherit support.
- Exact model/board/SoC/artifact/firmware evidence governs support.
- New destructive knowledge is never auto-promoted.

Service-entry families remain:

```text
Kirin      → HUAWEI USB COM 1.0 → exact signed loader → Factory/Board-Service Fastboot
Qualcomm   → QDLoader 9008      → exact Firehose programmer → verified service session
MediaTek   → BROM/Preloader     → exact DA → verified service session
```

Direct MTP/ADB/Fastboot routes are used when the selected operation is actually supported by that route. Upgrade Mode is recipe-specific; it is not a substitute for Testpoint when service access is required.

---

## 3. Authoritative engineering transport

### 3.1 Direct machine route

For real-machine engineering and proof, use:

```text
ChatGPT / authorised AI
        ↓
MCP
        ↓
Oracle Live
        ↓
workstation RPC
        ↓
ATHENA terminal / Windows environment
```

Oracle is transport/execution, not Huawei architecture authority.

The unfinished Oracle plugin is **not** the required route for this work.

GitHub queue/relay transport is fallback/recovery only. Do not claim GitHub queue activity as local ATHENA terminal proof.

### 3.2 ATHENA Builder authority

The shared Builder is on ATHENA at:

```text
D:\projects\THETECHGUY Software Builder - Installer Test
```

The Builder is the shared build/provisioning/hygiene layer. It owns shared build engines, dependency checks, caches, signing/release controls, worker/task coordination and its own environment.

The Huawei repository owns its source, project assets, project-specific configuration, final dist, and retained proof artifacts.

**Do not use the Builder directory as the Huawei project root.**

Before the first local Huawei write/build in a new session, discover and declare the contained Huawei project root on ATHENA. If no suitable contained checkout exists, create one deliberately under an approved project root; do not clone into Downloads, Desktop, drive root, another repository, or the Builder tree.

Builder must inventory/reuse existing shared capabilities before installing or downloading anything.

---

## 4. ATHENA owner-machine proof — source/UI complete, packaging confirmation deferred

The owner-machine source/UI milestone is now complete and merged. The A0-A5 procedure below is retained as the recovery/proof procedure for future release-candidate confirmation; it is **not** the current source-development frontier.

Current result:

- direct Oracle Live -> ATHENA identity/readiness: PASS;
- A0/A1 source/Builder recovery and clean isolated proof worktree: PASS;
- A2 Builder `doctor -> plan -> targets`: PASS;
- source/runtime/UI correctness: PASS and merged;
- long one-file packaging build: intentionally deferred as release confirmation;
- current packaging receipt: `UNFROZEN`, not falsely promoted.

### A0 — Recover live machine truth

Through Oracle MCP/RPC on ATHENA:

1. identify the current Huawei project checkout/worktree, if one exists;
2. declare the Huawei project root;
3. inspect `git status`, branch, remote and exact revision;
4. inspect Builder revision and health;
5. inventory required shared tools before installing anything;
6. verify available disk/storage locations and containment;
7. do not modify unknown files during discovery.

Exit gate:

- exact Huawei project root known;
- exact source revision known;
- exact Builder root/revision known;
- required dependencies either proven available or specifically identified as missing.

### A1 — Synchronize without destroying local evidence

1. preserve intentional local work if present;
2. fetch current `main`;
3. use a clean branch/worktree for any required correction;
4. do not overwrite unknown local files merely to force a clean build;
5. record the source revision selected for the local candidate.

Exit gate:

- build source is clean, identified and reproducible;
- no unrelated project files were changed.

### A2 — Builder preflight

From the shared Builder contract:

```text
ttg-builder doctor
ttg-builder plan <huawei-project-root>
ttg-builder targets <huawei-project-root>
```

Use the equivalent current Builder commands if its live contract has changed; recover them from the Builder repository first rather than guessing.

Exit gate:

- project scan passes or gives specific actionable defects;
- target and dependency ownership are understood;
- no unnecessary duplicate shared dependency is installed.

### A3 — Build the Windows candidate on ATHENA

Build `TECHGUYTOOL_Huawei.exe` through the shared Builder/current Huawei build contract.

Required evidence:

- exact Huawei source revision;
- exact Builder revision;
- build command/target;
- build stage log;
- dependency/preflight report;
- executable path;
- SHA-256;
- signing state;
- retained build receipt/provenance;
- storage/cleanup report.

Do not require the local executable SHA-256 to equal an older CI artifact unless the build contract explicitly proves byte-for-byte reproducibility. A mismatch must be explained by inputs/provenance, never waved away.

### A4 — Local runtime proof

On ATHENA prove at minimum:

- application launches;
- QML root reaches ready state;
- packaged resources load;
- approved mascot/header assets load;
- primary navigation works;
- six approved visual states remain reachable;
- forced close/restart succeeds;
- no placeholder route returns;
- logs/evidence stay inside approved project/application-data locations.

If a physical device is not connected, device-sensitive actions must remain truthful unavailable/unsupported states rather than simulated success.

### A5 — Freeze local proof

If ATHENA exposes a defect:

```text
Understand → correct → Review → Freeze → Prove → merge
```

If ATHENA exposes no defect, record the result as **Verification**, not as invented new implementation.

The Athena proof should be linked from the project/recovery system and, where appropriate, TTG-deploy-lab.

---

## 5. External certification tracks

These are certification/coverage tracks, not Phase 16.

### Dead-screen USB discovery coverage correction

A connected dead-screen Huawei proved that direct-route certification cannot assume the technician can select MTP on the handset. The current read-only discovery layer therefore starts from Windows PnP/USB evidence, anchors Huawei identity before generic ADB/Fastboot enumeration, and classifies storage-only/pre-service, MTP, ADB, Fastboot, Recovery, Upgrade Mode and `HUAWEI USB COM 1.0` only from observed interfaces. Shared VID/PID values never identify an exact model by themselves.

The cross-cutting matrix row `dead_screen_normal_android_charge_only_discovery` certifies detection/classification only. Passing it does not promote MTP, ADB, Fastboot, Recovery, Upgrade Mode, Testpoint, loader, firmware or repair support.

### Track B — Direct-route certification

Certify representative supported devices for:

- MTP detection and eligible operations;
- authorised ADB route;
- normal Fastboot route;
- Recovery detection;
- Upgrade Mode detection and recipe eligibility;
- multiple-device rejection/selection behavior;
- driver detection/repair on Windows.

Every result must record exact model, board, SoC, mode, operation, tool revision, artifacts and evidence.

### Track C — Kirin certification

Progressively certify Kirin generations/models using exact profiles.

Required proof categories include:

- read-only Xray explanation;
- Testpoint/service-entry recognition;
- `HUAWEI USB COM 1.0` correlation to the same physical device;
- exact loader validation;
- Factory/Board-Service Fastboot establishment;
- active mode-lease/reboot protection;
- bounded operation authority where a reviewed recipe exists;
- readback/Xray verification;
- finalization only after release conditions.

Historical P10/P30 evidence may be replayed as regression data but does not replace proof on a currently available supported device.

### Track D — Qualcomm Huawei certification

Start with read-only support:

- QDLoader 9008 detection;
- physical-device continuity;
- Sahara/session evidence where applicable;
- exact Firehose programmer validation;
- read-only storage/GPT/device-information proof;
- wrong programmer rejection.

Bounded writes are enabled later only per proven model/operation pair.

### Track E — MediaTek Huawei certification

Start with read-only support:

- BROM/Preloader detection;
- physical-device continuity;
- exact DA validation;
- auth/SLA/DAA state evidence;
- read-only storage/partition/device-information proof;
- wrong DA/model rejection.

Bounded writes are enabled later only per proven model/operation pair.

### Track F — Interrupted-operation/recovery proof

Using an approved controlled test device/operation:

- interrupted bounded stage;
- journal recovery;
- UI restart recovery;
- Gateway restart recovery;
- stale/consumed lease rejection;
- physical-session continuity;
- safe resume/abort behavior;
- no silent widening of write authority.

---

## 6. Progressive Huawei coverage model

The product is designed for **all supported Huaweis**, but support is earned progressively.

Every supported model/variant should converge on:

```text
marketing name
model / regional variant
board
SoC
USB/service modes
direct-route capability
Testpoint reference
loader/programmer/DA manifest
firmware families/regions
supported operations
known hazards
proof level
last verified tool/profile revision
```

Rules:

1. Unknown models remain unsupported.
2. Similar appearance/model naming does not authorize profile reuse.
3. Testpoint references must be owner-approved exact-model records.
4. Loader/programmer/DA identity must be exact and hash-bound.
5. Firmware compatibility must be evidence-based, not filename-based.
6. A newly proven read-only fact improves specialist Xray first.
7. Mature read-only capability may then be promoted to TTG Device X-Ray.
8. Executor/write authority stays in the owning reviewed recipe/adapter and is never promoted into Xray.

Coverage expansion is continuous product improvement; it does not mean the base Huawei application is unfinished.

---

## 7. Production release gate

Production enablement may change only when the applicable evidence exists.

Required release evidence includes:

- final supported-device matrix for the intended release;
- real Windows driver/device servicing proof;
- controlled interrupted-operation recovery proof for enabled write classes;
- no unresolved high-severity regression;
- production Authenticode certificate/signature;
- final release artifact SHA-256/provenance;
- installer/release verification through the approved Builder lane;
- rollback/recovery instructions;
- owner approval.

A release may intentionally ship with a subset of Huawei models/operations. Unsupported combinations must say `Unsupported` or `Need artifact/evidence`; they must never inherit support from another model.

---

## 8. Documentation and learning loop

When physical proof discovers new truth:

1. raw evidence belongs with the owning project/proof storage;
2. specialist read-only understanding is updated first;
3. Inquiry Governor records unexplained outcomes/gaps;
4. Knowledge Workshop challenges new candidates before promotion;
5. proven read-only capability is promoted to TTG Device X-Ray when mature;
6. model/operation support tables are updated only after evidence;
7. reusable build/runtime lessons are added to existing canonical documentation;
8. TTG-progress is updated when current status changes;
9. TTG-deploy-lab is updated when deployment/proof procedure changes;
10. Google Drive recovery gets a short pointer/handoff, not a duplicate of this roadmap.

---

## 9. Future standalone-to-main-tool consolidation

TECHGUYTOOL Huawei remains an independently testable specialist tool while its Huawei capability matures.

Future consolidation into the broader THETECHGUY tool ecosystem must preserve:

- Xray read-only authority;
- specialist capability packs;
- Decision/Governor boundaries;
- bounded executor leases;
- exact model/operation proof state;
- Huawei-specific evidence/provenance;
- the approved Huawei UI/experience where the consolidated product exposes those functions.

Consolidation is not a reason to collapse specialist repositories or erase proof lineage.

It is **not** the current next milestone.

---

## 10. New-chat pickup protocol

Every future session that is asked to continue Huawei work must do this before proposing implementation:

1. fetch live `main` and current open PRs/issues;
2. read `ROADMAP.md`;
3. read `FULL_PLAN.md` for architecture/invariants;
4. read `AGENTS.md` and the containment/shared-tools policy;
5. read `manifests/phase15_ui_closeout.receipt.json`;
6. read the current production/certification receipt/state;
7. read `resources/expected ui/README.md` before UI work;
8. read the relevant model/recipe/profile evidence before device work;
9. check TTG-progress for ecosystem-level current/next truth;
10. if local Windows proof is required, use Oracle MCP → Oracle Live → ATHENA RPC and the shared Builder rather than the unfinished Oracle plugin or GitHub queue as a terminal substitute.

Then classify the requested work as one of:

```text
software regression correction
ATHENA/local verification
external certification
model/operation coverage expansion
Xray knowledge improvement
production release/signing
future consolidation
```

Do not reopen Phases 1–15 simply because a new chat lacks context.

---

## 11. Current next action

Unless newer repository evidence supersedes this roadmap, the next action is:

> **Begin external Huawei certification with whatever representative Huawei hardware is physically available. Prefer the lowest-risk read-only/direct route first (MTP, authorised ADB, normal Fastboot, Recovery or Upgrade Mode as applicable), capture exact device/host evidence, and promote only the exact evidence-backed matrix row.**

Certification evidence procedure:

1. keep raw device/host captures under the repository's ignored `proof/` tree or another approved contained project-proof location;
2. hash the exact subject identity and captured evidence with `tools/record_physical_proof.py`;
3. review the generated packet against the exact model/board/SoC/mode/operation being certified;
4. only after review may the corresponding `manifests/phase15_physical_proof_matrix.json` entry become `PHYSICAL_PASS`;
5. never infer support from a related model or from software/replay evidence;
6. if no Huawei hardware is attached, leave the matrix pending rather than simulating success.

The recorder creates evidence packets only. It does **not** mutate the physical matrix or enable production.

Packaging, CI test signing and production Authenticode remain separate release-artifact/certificate work and may be performed later when an actual release artifact is required. The old P30 is not required.

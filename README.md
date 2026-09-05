# TECHGUYTOOL Huawei

Huawei service and recovery engineering project for **THETECHGUY DIGITAL SOLUTIONS**.

## Start here

Read these in order before changing the project:

1. **[ROADMAP.md](ROADMAP.md)** — current state, next milestone, ATHENA/Builder/Oracle execution route and new-chat pickup rules.
2. **[FULL_PLAN.md](FULL_PLAN.md)** — frozen architecture, invariants, authority boundaries, donor lineage, repair theorem and Phase 1–15 design.
3. **[AGENTS.md](AGENTS.md)** — workspace containment/shared-tools rules.
4. **[manifests/phase15_ui_closeout.receipt.json](manifests/phase15_ui_closeout.receipt.json)** — final software/UI proof authority.
5. **[resources/expected ui/README.md](resources/expected%20ui/README.md)** — approved visual contract.

Chat history is context only. Repository evidence governs implementation.

## Current status

**Phases 1–15 software scope are complete.**

Do not restart Phase 4, Phase 15, or invent a Phase 16 merely because physical certification remains open.

The final approved software/UI closeout is frozen and records:

- source freeze: PASS;
- software proof: PASS;
- Windows candidate: PASS;
- visual QA: PASS;
- source QML startup: PASS;
- packaged QML startup: PASS;
- forced-close/restart: PASS;
- CI test signing: PASS;
- final candidate: `TECHGUYTOOL_Huawei.exe`;
- final recorded candidate SHA-256: `b0709e2d46c793609456877f55fdecc6620382ea55777684cc4b9c5199f14080`.

Production remains disabled until applicable physical certification and production signing are complete.

## Architecture boundary

The frozen system is:

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
Mature read-only capability promotion
```

Xray remains read-only. Executors are lease-bounded and never choose their own target. A successful command is not automatically a successful repair. Model/variant/artifact/firmware support is evidence-backed and fail-closed.

Service-entry families include:

```text
Kirin      → HUAWEI USB COM 1.0 → exact signed loader → Factory/Board-Service Fastboot
Qualcomm   → QDLoader 9008      → exact Firehose programmer → verified service session
MediaTek   → BROM/Preloader     → exact DA → verified service session
```

See `FULL_PLAN.md` for the complete contract.

## Current next milestone

The current practical milestone is **external Huawei hardware certification**, beginning with read-only, screen-independent discovery on whatever representative Huawei hardware is physically available. Owner-machine source/UI proof is already complete; do not reopen it.

Use:

```text
MCP → Oracle Live → workstation RPC → ATHENA terminal
```

The unfinished Oracle plugin is not required. GitHub queue/relay transport is fallback/recovery only and must not be represented as local terminal proof.

The shared Builder on ATHENA is currently located at:

```text
D:\projects\THETECHGUY Software Builder - Installer Test
```

The Builder is a shared build/provisioning layer; it is **not** the Huawei project root. Before local work, discover and declare the contained Huawei checkout/worktree, inventory the live Builder/tool state, then build and prove the current candidate through the Builder lane.

See `ROADMAP.md` for the exact execution gates.

## Historical P10/P30 evidence

P10Revive and the historical P30/VOG work are donor/proof lineage used to improve Kirin Xray, repair sequencing, version/OEMINFO understanding, service-mode preservation and verification logic.

The old P30 handset is **not** a current project dependency or required certification target.

Future certification uses whichever exact supported Huawei devices are actually available and records proof per model/operation pair.

## Current certification tracks

Continue evidence-driven certification without reopening the software phases:

- screen-independent Huawei USB/PnP discovery before direct MTP/ADB/Fastboot/Recovery/Upgrade routing;
- Kirin service-entry and bounded-recipe proof;
- Qualcomm 9008/Firehose read-only proof before model-specific writes;
- MediaTek BROM/Preloader/DA read-only proof before model-specific writes;
- Windows driver/device servicing;
- interrupted-operation/restart/recovery behavior;
- progressive model/variant coverage;
- production Authenticode signing and final release evidence.

Unknown models remain unsupported. Similar-looking models never inherit support.

## Authorities and evidence

- [`ROADMAP.md`](ROADMAP.md)
- [`FULL_PLAN.md`](FULL_PLAN.md)
- [`AGENTS.md`](AGENTS.md)
- [`manifests/phase15_ui_closeout.receipt.json`](manifests/phase15_ui_closeout.receipt.json)
- [`manifests/phase15_windows_release.receipt.json`](manifests/phase15_windows_release.receipt.json)
- [`manifests/source_inventory.json`](manifests/source_inventory.json)
- [`manifests/external_artifacts.json`](manifests/external_artifacts.json)
- [`resources/expected ui/README.md`](resources/expected%20ui/README.md)

## Windows release target

The application target remains:

```text
TECHGUYTOOL_Huawei.exe
```

Firmware, SUPER images, loaders/programmers/DAs where externally governed, customer backups, operation journals, registration data and downloaded artifacts remain outside normal Git source control and are governed by manifests/provenance.

## Recovery authority

- Current GitHub execution roadmap: `ROADMAP.md`
- Frozen GitHub architecture: `FULL_PLAN.md`
- Google Drive plan/recovery mirror: https://docs.google.com/document/d/1q2_Ym9CqzVPAsPcI-0w4JLIQzEWRbWhjjY8CK-5nxGw/edit
- Huawei private source/evidence archive: Google Drive file `1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs`

If a future session is unsure where to continue, it must recover live `main`, read `ROADMAP.md`, then classify the requested work before proposing changes.

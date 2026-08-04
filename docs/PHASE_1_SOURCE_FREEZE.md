# Phase 1 — Source Freeze and External-Artifact Authority

**Status:** IMPLEMENTED — pending Git commit receipt and independent review  
**Plan authority:** `FULL_PLAN.md` Phase 1  
**Prepared:** 2026-08-04

## 1. Evidence recovered before implementation

Repository recovery found that `main` contained the canonical plan plus temporary workspace-import markers, but not the approved application source. The safe UI/source workspace was recovered from GitHub Actions run `30748347340`, artifact `huawei-source-workspace`, artifact ID `8833608382`, with digest:

`sha256:dbbb3b430f3ea595f4c4f01bc18670770059deec2c2700809085333fa6d645bc`

The owner-supplied private archive was recovered independently from Google Drive:

- Drive file ID: `1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs`
- Name: `huawei Revive.zip`
- Size: `434391243` bytes
- SHA-256: `d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4`
- Archive entries: `4448`

Two local copies were byte-identical. No Athena recovery is required.

## 2. Frozen classification

### 2.1 Active public source

The repository checkpoint contains only the source appropriate for immediate public engineering:

- PySide6/QML application shell;
- guarded action registry;
- read-only host discovery and evidence capture;
- action-health ledger;
- deterministic Rust action-manifest audit core;
- tests, QML verification, screenshot proof, and packaging source.

### 2.2 Private/quarantined recovery source

The Drive archive remains private and external. It includes:

- `system/huawei-revive.pyz` with the historical Xray/Revive Python source;
- a live device-bound `flash_vog_l29_c185.py` runner;
- historical plans and operation logs;
- generated VOG-L29 C185 OEMINFO material;
- Kirin loaders and a temporary recovery image;
- extracted recovery files and donor source trees;
- device identifiers and operation-specific evidence.

The archive is authoritative recovery evidence, but it is not production source authority. It mixes read-only diagnosis, artifact construction, loader transport, and write execution in ways that conflict with the frozen architecture. It must be decomposed, not copied wholesale.

### 2.3 External runtime artifacts

Firmware, loaders, recovery images, OEMINFO images, SUPER, backups, and logs remain external. Their custody and expected hashes are recorded in `manifests/external_artifacts.json`.

The owner intentionally omitted the original retail and board firmware packages plus generated SUPER from the transferable archive. They are therefore **external inputs**, not missing source.

## 3. Source-control exclusions

The Phase 1 verifier rejects:

- old `workspace-import`, `final-patch`, transfer-probe, and runtime-import/export debris;
- firmware, loader, recovery, backup, and customer-evidence directories;
- executable/runtime binary extensions outside explicitly approved visual assets;
- source inventory hash mismatches;
- absent plan or archive authority records.

## 4. Privacy and authority correction

The public repository does not preserve live device serials or customer operation logs. Private evidence remains in the Drive archive and is referenced by digest.

The historical package describes itself as read-only, but recovered modules include loader serial writes, OEMINFO image construction, destructive board operation descriptions, and a device-bound full-flash runner. Those capabilities are quarantined until later phases split them into:

```text
read-only specialist Xray
→ deterministic governor
→ lease compiler
→ bounded executor
→ independent Xray verification
```

## 5. Phase 1 exit-gate result

- Active source provenance: **recorded**
- Private source archive provenance: **recorded**
- Included source/proof hashes: **recorded**
- Omitted firmware/SUPER/runtime artifacts: **declared**
- Transfer/import debris in clean checkpoint: **rejected by verifier**
- Athena recovery request: **not required**
- Public/private boundary: **frozen**

The phase is complete only after the clean source checkpoint is committed and `manifests/source_inventory.receipt.json` binds the manifest to the exact Git commit.

## 6. Next authorized phase

Proceed to **Phase 2 — Shared Python/Rust contracts**. Do not activate historical write paths while implementing those contracts.

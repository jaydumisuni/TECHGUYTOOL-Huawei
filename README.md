# TECHGUYTOOL Huawei

Huawei service and recovery engineering project for **THETECHGUY DIGITAL SOLUTIONS**.

## Start here

Read **[FULL_PLAN.md](FULL_PLAN.md)** before changing architecture, routes, Xray boundaries, repair recipes, executors, packaging, or proof requirements.

The repository contains the frozen source checkpoint for the Qt/QML host application, the public/private artifact authority, and the deterministic shared Python/Rust contract core. The historical Huawei Revive archive remains private recovery evidence because it contains device identifiers, operation logs, firmware-derived binaries, loaders, recovery images, and mixed read/write authority that must be decomposed before production use.

## Current phase

### Completed

**Phase 1 — Source freeze and external-artifact authority**

- exact source and GitHub Actions provenance;
- private Revive archive identity and SHA-256;
- manifests for intentionally external firmware, board software, SUPER, loaders, backups, logs, and evidence;
- fail-closed rejection of transfer debris and runtime binaries from public source.

**Phase 2 — Shared Python/Rust contracts**

- 17 versioned contract types;
- deterministic canonical UTF-8 JSON and SHA-256 identity;
- identical Python and Rust validation behavior;
- fail-closed authority, session, expiry, single-use, recipe, and artifact checks;
- automatic promotion forbidden for write targets, offsets, destructive recipes, and expanded authority;
- 17 valid fixtures, 34 invalid mutation fixtures, and one malformed-JSON fixture;
- exact 52-case Python/Rust equivalence proof;
- Rust 1.75 formatting, Clippy with warnings denied, compilation, and tests;
- complete Python regression and source-freeze verification.

Phase 2 proof receipt: [`manifests/source_inventory.receipt.json`](manifests/source_inventory.receipt.json)

### Next authorized phase

**Phase 3 — TTG Device Gateway**

The next implementation must build the persistent, device-inert Gateway control plane around the frozen Phase 2 contracts:

- physical-device and operation session registries;
- typed event bus;
- plugin/provider lifecycle;
- ordered policy hooks;
- SQLite durable state and evidence journal;
- worker supervision and watchdogs;
- crash recovery and UI reconnection;
- diagnostics and capability allowlists.

Phase 3 does not authorize device-changing executors.

## Authorities and evidence

- [`FULL_PLAN.md`](FULL_PLAN.md)
- [`docs/PHASE_1_SOURCE_FREEZE.md`](docs/PHASE_1_SOURCE_FREEZE.md)
- [`docs/LEGACY_AUTHORITY_REVIEW.md`](docs/LEGACY_AUTHORITY_REVIEW.md)
- [`docs/PHASE_2_SHARED_CONTRACTS.md`](docs/PHASE_2_SHARED_CONTRACTS.md)
- [`contracts/registry.json`](contracts/registry.json)
- [`manifests/source_inventory.json`](manifests/source_inventory.json)
- [`manifests/private_source_archive.json`](manifests/private_source_archive.json)
- [`manifests/external_artifacts.json`](manifests/external_artifacts.json)

## Active safety boundary

Xray remains strictly read-only. The active source may inspect, identify, correlate, diagnose, recommend, predict, and verify. It may not flash, erase, unlock, relock, reboot, upload a destructive service loader, write OEMINFO, or modify a device partition.

`execution_lease` is currently a validated contract only. No production executor consumes it yet.

Historical code or evidence that can modify a device remains private recovery input until it is decomposed into a reviewed bounded executor governed by a versioned lease.

## Contract proof

```powershell
python -m pytest tests\test_shared_contracts.py -q
cargo fmt --manifest-path rust\contracts_core\Cargo.toml -- --check
cargo clippy --manifest-path rust\contracts_core\Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust\contracts_core\Cargo.toml --all-targets
cargo build --manifest-path rust\contracts_core\Cargo.toml --bin ttg-contracts
python tools\prove_contract_equivalence.py --rust-bin rust\contracts_core\target\debug\ttg-contracts.exe
python tools\build_source_inventory.py
python -m pytest -q
python tools\verify_source_freeze.py --json
```

## Windows one-file target

```powershell
.\build_windows.ps1
```

The intended release filename is `TECHGUYTOOL_Huawei.exe`. Firmware, loaders, recovery images, backups, logs, registration data, and downloaded artifacts remain outside the executable and outside normal Git source control.

## Recovery authority

- GitHub plan: `FULL_PLAN.md`
- Google Drive plan mirror: https://docs.google.com/document/d/1q2_Ym9CqzVPAsPcI-0w4JLIQzEWRbWhjjY8CK-5nxGw/edit
- Huawei private source archive: Google Drive file `1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs`

Chat history is context only. Repository evidence and the frozen plan govern implementation.

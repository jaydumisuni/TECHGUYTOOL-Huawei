# TECHGUYTOOL Huawei

Huawei service and recovery engineering project for **THETECHGUY DIGITAL SOLUTIONS**.

## Start here

Read **[FULL_PLAN.md](FULL_PLAN.md)** before changing architecture, routes, Xray boundaries, repair recipes, executors, packaging, or proof requirements.

The repository contains the frozen Qt/QML host checkpoint, public/private artifact authority, deterministic shared Python/Rust contracts, and the persistent device-inert TTG Device Gateway. The historical Huawei Revive archive remains private recovery evidence because it contains device identifiers, operation logs, firmware-derived binaries, loaders, recovery images, and mixed read/write authority that must be decomposed before production use.

## Completed phases

### Phase 1 — Source freeze and external-artifact authority

- exact source and GitHub Actions provenance;
- private Revive archive identity and SHA-256;
- manifests for intentionally external firmware, board software, SUPER, loaders, backups, logs, and evidence;
- fail-closed rejection of transfer debris and runtime binaries from public source.

### Phase 2 — Shared Python/Rust contracts

- 17 versioned contract types;
- deterministic canonical UTF-8 JSON and SHA-256 identity;
- identical Python and Rust validation behavior;
- fail-closed authority, session, expiry, single-use, recipe, artifact, and validation-context checks;
- automatic promotion forbidden for write targets, offsets, destructive recipes, and expanded authority;
- 17 valid fixtures, 34 invalid mutations, 3 review-edge cases, one malformed-JSON case, and two context cases;
- exact 57-case Python/Rust proof;
- Rust 1.75 formatting, Clippy with warnings denied, compilation, and tests.

Phase 2 receipt: [`manifests/source_inventory.receipt.json`](manifests/source_inventory.receipt.json)

### Phase 3 — TTG Device Gateway

- persistent physical-device and operation sessions;
- SQLite schema version 1;
- typed event bus and append-only hash-chained journal;
- provider manifests and contract-authority checks;
- ordered operation-stage policy;
- Phase 2 contract validation at Gateway ingress;
- fail-closed capability allowlists;
- worker heartbeat and watchdog state;
- crash recovery and explicit operation resume;
- loopback-only UTF-8 JSON-lines protocol;
- reconnect-safe Python UI client;
- `doctor`, snapshots, and journal verification;
- no device-write, loader, flash, partition, OEMINFO, or reboot surface.

Phase 3 authority: [`docs/PHASE_3_DEVICE_GATEWAY.md`](docs/PHASE_3_DEVICE_GATEWAY.md)  
Phase 3 receipt: [`manifests/phase3_gateway.receipt.json`](manifests/phase3_gateway.receipt.json)

## Next authorized phase

**Phase 4 — Harden Kirin Xray**

The next implementation must build the complete read-only Huawei evidence lane and replay the P10/P30 evidence without adding write authority.

## Authorities and evidence

- [`FULL_PLAN.md`](FULL_PLAN.md)
- [`docs/PHASE_1_SOURCE_FREEZE.md`](docs/PHASE_1_SOURCE_FREEZE.md)
- [`docs/LEGACY_AUTHORITY_REVIEW.md`](docs/LEGACY_AUTHORITY_REVIEW.md)
- [`docs/PHASE_2_SHARED_CONTRACTS.md`](docs/PHASE_2_SHARED_CONTRACTS.md)
- [`docs/PHASE_3_DEVICE_GATEWAY.md`](docs/PHASE_3_DEVICE_GATEWAY.md)
- [`contracts/registry.json`](contracts/registry.json)
- [`manifests/source_inventory.json`](manifests/source_inventory.json)
- [`manifests/private_source_archive.json`](manifests/private_source_archive.json)
- [`manifests/external_artifacts.json`](manifests/external_artifacts.json)

## Active safety boundary

Xray remains strictly read-only. The Gateway has `device_authority = none`. The active source may inspect, identify, correlate, diagnose, recommend, predict, coordinate, journal, and verify. It may not flash, erase, unlock, relock, reboot, upload a destructive service loader, write OEMINFO, or modify a device partition.

`execution_lease` remains a validated contract only. No production executor consumes it yet.

Historical code or evidence that can modify a device remains private recovery input until it is decomposed into a reviewed bounded executor governed by a versioned lease.

## Phase 3 proof

```powershell
cargo generate-lockfile --manifest-path rust\device_gateway\Cargo.toml
cargo fmt --manifest-path rust\device_gateway\Cargo.toml -- --check
cargo clippy --locked --manifest-path rust\device_gateway\Cargo.toml --all-targets -- -D warnings
cargo test --locked --manifest-path rust\device_gateway\Cargo.toml --all-targets
cargo build --locked --manifest-path rust\device_gateway\Cargo.toml --bin ttg-device-gateway
python -m pytest tests\test_gateway_client.py -q
python tools\prove_gateway_reconnect.py --gateway-bin rust\device_gateway\target\debug\ttg-device-gateway.exe
python tools\build_source_inventory.py
python -m pytest -q
python tools\verify_source_freeze.py --json
python tools\build_phase2_receipt.py --verify
python tools\build_phase3_receipt.py --verify
```

## Windows one-file target

```powershell
.\build_windows.ps1
```

The intended release filename is `TECHGUYTOOL_Huawei.exe`. Firmware, loaders, recovery images, backups, logs, registration data, runtime Gateway databases, and downloaded artifacts remain outside the executable and outside normal Git source control.

## Recovery authority

- GitHub plan: `FULL_PLAN.md`
- Google Drive plan mirror: https://docs.google.com/document/d/1q2_Ym9CqzVPAsPcI-0w4JLIQzEWRbWhjjY8CK-5nxGw/edit
- Huawei private source archive: Google Drive file `1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs`

Chat history is context only. Repository evidence and the frozen plan govern implementation.

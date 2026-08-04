# TECHGUYTOOL Huawei

Huawei service and recovery engineering project for **THETECHGUY DIGITAL SOLUTIONS**.

## Start here

Read **[FULL_PLAN.md](FULL_PLAN.md)** before changing architecture, routes, Xray boundaries, repair recipes, executors, packaging, or proof requirements.

The repository now contains the recovered **safe active source checkpoint** for the approved Qt/QML interface and read-only host evidence shell. The historical Huawei Revive archive remains an external private recovery source because it contains device identifiers, customer/operation evidence, firmware-derived binaries, loaders, recovery images, and mixed read/write authority that must not be imported into public production source unchanged.

## Current phase

**Phase 1 — Source freeze and external-artifact manifests: implemented.**

The source freeze records:

- exact GitHub and GitHub Actions provenance for the active UI workspace;
- exact Google Drive archive identity, size, and SHA-256;
- key private artifact hashes without publishing the binaries;
- intentionally omitted retail firmware, board firmware, SUPER, backups, logs, and customer evidence;
- the authority gap between legacy mixed-purpose Revive code and the frozen read-only Xray boundary;
- deterministic checks that reject transfer debris and runtime binaries from source control.

See:

- [`docs/PHASE_1_SOURCE_FREEZE.md`](docs/PHASE_1_SOURCE_FREEZE.md)
- [`docs/LEGACY_AUTHORITY_REVIEW.md`](docs/LEGACY_AUTHORITY_REVIEW.md)
- [`manifests/source_inventory.json`](manifests/source_inventory.json)
- [`manifests/private_source_archive.json`](manifests/private_source_archive.json)
- [`manifests/external_artifacts.json`](manifests/external_artifacts.json)

## Active source boundary

The active source currently provides:

- the approved cross-platform PySide6/QML shell;
- read-only ADB/Fastboot discovery with exactly-one-device gating;
- hashed physical-session/evidence records;
- action health and guarded action contracts;
- a deterministic Rust manifest auditor;
- QML construction and screenshot proof;
- Windows one-file build plumbing for `TECHGUYTOOL_Huawei.exe`.

It does **not** yet claim production repair adapters, a completed Gateway, shared Python/Rust authority contracts, full Kirin Xray integration, or physical VOG-L29 end-to-end proof. Those belong to the subsequent plan phases.

## Safety boundary

Xray remains read-only. The active application source may inspect, identify, correlate, diagnose, recommend, and verify. It may not flash, erase, unlock, relock, reboot, upload a service loader, write OEMINFO, or modify a device partition.

Historical code or evidence that can perform those operations is private recovery input only until it is decomposed into reviewed bounded executors governed by versioned leases.

## Development proof

```powershell
python -m pip install -e ".[test]"
python tools\generate_qrc.py
python tools\verify_source_freeze.py
python -m pytest
python tools\review_20_for_2.py --strict
python tools\smoke_qml.py
```

## Windows one-file build

```powershell
.\build_windows.ps1
```

The intended release filename is `TECHGUYTOOL_Huawei.exe`. Firmware, loaders, recovery images, backups, logs, registration data, and downloaded artifacts remain outside the executable and outside normal Git source control.

## Recovery authority

- GitHub plan: `FULL_PLAN.md`
- Google Drive plan mirror: https://docs.google.com/document/d/1q2_Ym9CqzVPAsPcI-0w4JLIQzEWRbWhjjY8CK-5nxGw/edit
- Huawei private source archive: Google Drive file `1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs`

Chat history is context only. Repository evidence and the frozen plan govern implementation.

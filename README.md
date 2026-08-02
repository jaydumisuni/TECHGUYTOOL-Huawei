# TECHGUY TOOL — HUAWEI

**Service & Recovery Edition** by **THETECHGUY DIGITAL SOLUTIONS**.

This repository is the cross-platform Qt Quick source for the Huawei service interface approved in the six visual references. The Windows release target is a single signed executable named `TECHGUY_TOOL_Huawei.exe`. The same QML and engine interface can produce platform-specific macOS and Linux packages.

## Current milestone

The first milestone establishes the complete UI shell and the safe engine boundary:

- 1586 × 992 frameless glass interface matching the approved layout proportions;
- Service Center, Firmware Flash, placeholder module pages, live operation log and footer state;
- Settings, Fix Drivers, Register Device, About and Fastboot Terminal interfaces;
- model/chipset selector contract and starter Huawei/Kirin profile database;
- ADB/Fastboot read-only discovery with exactly-one-device ambiguity protection;
- hashed physical-session identity and SHA-256 evidence envelopes;
- action manifest, per-action runtime health ledger and UI-binding heartbeat;
- optional Rust action-manifest auditor with Python fallback;
- two governed waves of twenty deterministic checks—**SRG 20-for-2**;
- Qt resource compilation and `pyside6-deploy`/Nuitka one-file release contract.

## Safety and proof boundary

The repository does **not** implement lock bypasses, arbitrary fastboot commands or unverified partition writes. FRP, account, bootloader, Verlist, OEMINFO, flashing, board and restore actions are present in the interface and action registry but remain explicitly `GUARDED` until an approved adapter supplies:

1. ownership/authorization evidence;
2. exact device and firmware compatibility;
3. backup and restore proof;
4. deterministic preflight and post-write verification.

The current engine can safely identify one ADB/Fastboot device, collect read-only evidence, reject missing or ambiguous devices, validate a selected firmware file exists and is non-empty, and report missing dependencies without fabricating success.

## Architecture borrowed and adapted

The implementation is native to this repository; it does not depend on the other projects at runtime.

- **Kirin/Xray concepts:** fixed shell-free provider commands, stable physical sessions, raw evidence envelopes, SHA-256 custody and read-first authority.
- **MIBU concepts:** bundled-tool preference, exact one-device gating, compact desktop workflow, release composition checks and fail-closed packaging.
- **Sergeant concepts:** evidence before claims, deterministic action contracts, challenger checks and two 20-check review waves.

## Development

```powershell
python -m pip install -e ".[test]"
python tools\generate_qrc.py
python -m pytest
python tools\review_20_for_2.py --strict
python main.py
```

PySide6 is required to launch the QML application. The static tests and 20-for-2 review do not require a connected phone.

## Actual QML render proof

```powershell
python tools\smoke_qml.py
```

The command loads the real `qml/Main.qml`, creates the application window, captures it and writes `proof/qml-main.png`. CI runs the same proof under Xvfb and uploads the image artifact.

## Windows one-file build

```powershell
.\build_windows.ps1
```

The release script:

1. installs the declared build/test dependencies;
2. compiles the Rust health core;
3. regenerates and compiles Qt resources;
4. runs tests and the strict 40-check review;
5. invokes `pyside6-deploy` in Nuitka `onefile` mode;
6. requires `TECHGUY_TOOL_Huawei.exe`;
7. signs it when `TECHGUY_SIGNING_CERT_THUMBPRINT` is supplied;
8. writes `SHA256SUMS.txt`.

Mutable files are not compiled into the executable. Logs, evidence, backups, registration data, user settings and downloaded firmware are stored in the platform application-data location. Firmware packages and backups remain external because they are mutable and can be many gigabytes.

## Repository map

```text
assets/brand/              Approved visual assets derived from the supplied references
data/                      Action manifest and starter device profiles
qml/                       Main window, components, pages and dialogs
techguy_huawei/            Python bridge, read-only engine, evidence and health core
rust/health_core/          Deterministic action-manifest auditor
tests/                     Unit and source-contract proof
tools/                     QRC generation, QML smoke proof and SRG 20-for-2 review
build_windows.ps1          Verified one-file Windows release pipeline
pysidedeploy.spec          Qt/Nuitka deployment contract
```

## Physical proof still required

Source review and CI can prove syntax, action wiring, state transitions, guardrails, QML construction, screenshot generation and package composition. A Windows servicing machine and owned Huawei test device are still required to prove USB drivers, local ADB/Fastboot binaries, device mode transitions, firmware parsing against real packages, code signing and future approved write adapters.

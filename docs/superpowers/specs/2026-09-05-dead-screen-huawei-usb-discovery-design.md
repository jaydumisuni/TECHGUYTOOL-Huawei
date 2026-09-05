# Dead-Screen Huawei USB Discovery Design

**Status:** Owner-approved design  
**Date:** 2026-09-05  
**Repository:** `jaydumisuni/TECHGUYTOOL-Huawei`

## Problem

A physically connected Huawei with a dead screen is currently visible to Windows as `VID_12D1:PID_107E` using the generic USB mass-storage class and a Linux File-CD Gadget child. The existing `DeviceEngine.probe()` only understands ADB and Fastboot, so it can miss this Huawei while simultaneously misidentifying an unrelated Android ADB device as the service target.

The product is a recovery tool. It must not require touch input or a working display merely to identify a connected Huawei and determine the next safe recovery route.

## Goals

1. Add read-only Windows Huawei USB discovery that does not require a working screen.
2. Classify observable Huawei endpoint states without inferring an exact model from a shared VID/PID.
3. Bind observations to one physical device using USB serial/container continuity and a SHA-256 fingerprint.
4. Keep unrelated Android devices, including the currently attached Redmi, outside Huawei identity.
5. Feed the normalized observation into the existing TTG Device Gateway endpoint contract.
6. Let `DeviceEngine.probe()` report a truthful connected Huawei in storage-only/pre-service state instead of saying no Huawei is present.
7. Record the connected dead-screen handset as physical evidence for the discovery capability without committing its raw serial.

## Non-goals

- No flashing, partition access, loader transfer, driver replacement, USB control transfer, vendor command, or mode-forcing.
- No automatic Testpoint action.
- No claim that `12D1:107E` identifies a specific Huawei model.
- No automatic promotion of MTP, ADB, Fastboot, Recovery, Upgrade Mode, or service-write support.
- No production enablement or packaging change.

## Architecture

### Pure discovery model

Create `techguy_huawei/usb_discovery.py`. It owns normalized USB observations, Huawei grouping, state classification, identity continuity, and safe route recommendations. It contains no subprocess calls and is platform-independent.

Normalized observations contain instance/class/friendly/device/bus/manufacturer descriptors, hardware/compatible IDs, container ID, and parent instance ID.

Huawei candidates require USB VID `12D1` or an explicit Huawei service descriptor. Candidates are grouped by physical identity. The preferred continuity material is vendor ID + USB serial + container ID; the public fingerprint is SHA-256 over canonical JSON. Raw serial values remain local evidence and are never serialized in the public report.

### State classifier

The fail-closed state set is:

```text
normal_android_charge_only
mtp
adb
normal_fastboot
recovery
upgrade_mode
huawei_usb_com_1_0
unknown_huawei
multiple_huawei_devices
```

Classification uses actual interface descriptors/classes, never PID alone. `12D1:107E` with only storage/CD-ROM children is `normal_android_charge_only`. The same VID/PID becomes `upgrade_mode` only when PCUI/DBAdapter-style service interfaces are actually observed.

Precedence is explicit service interface -> Upgrade Mode -> Fastboot -> Recovery -> ADB -> MTP -> storage-only -> unknown.

### Dead-screen route recommendation

Each discovery result carries a read-only route decision:

- storage-only/pre-service -> direct route unavailable; exact identity/service entry still required; no screen action required by the software contract;
- MTP -> MTP candidate only when a Huawei WPD/MTP endpoint exists;
- ADB -> ADB candidate, with authorization checked separately;
- normal Fastboot -> normal Fastboot candidate;
- Recovery -> Recovery detected;
- Upgrade Mode -> recipe eligibility still required;
- HUAWEI USB COM 1.0 -> Kirin service entry detected, but exact model/loader authority still required.

Every result keeps `device_modification="none"` and `write_authority="none"`.

### Windows collector

Create `techguy_huawei/windows_usb.py`. It runs one fixed PowerShell argv command with `shell=False` to enumerate present PnP devices and selected `DEVPKEY_Device_*` properties, then normalizes that JSON into the pure discovery model. No new Python dependency is introduced.

Create `tools/discover_huawei_usb.py` as the operator/proof entry point. It prints canonical JSON and may write only under the ignored repository `proof/` root.

### DeviceEngine integration

`DeviceEngine.probe()` performs Windows Huawei USB discovery before generic ADB/Fastboot identity acceptance.

1. Exactly one physical Huawei observation becomes the Huawei identity anchor.
2. Storage-only/pre-service Huawei is reported connected/read-only with identity pending.
3. Unrelated ADB devices must never become Huawei merely because `adb devices` reports them.
4. Multiple Huawei devices fail closed as guarded ambiguity.
5. Existing non-Windows behavior stays unchanged unless Huawei evidence is explicit.

### Gateway integration

Reuse the existing Gateway API:

```text
open_physical_session(fingerprint_sha256)
record_endpoint(session_id, endpoint_key, mode, transport, payload)
```

The Gateway payload contains only public discovery fields: state, VID/PID, fingerprint, interfaces, route decision, and authority flags. Raw serial is excluded. Gateway publication is additive; local discovery still succeeds when the Gateway daemon is unavailable.

### Physical certification

Add matrix row `dead_screen_normal_android_charge_only_discovery`. It certifies only screen-independent detection/classification of a Huawei in a pre-service/storage-only state. It does not certify model identity, MTP, ADB, Fastboot, Recovery, Upgrade Mode, Testpoint, loaders, firmware, or repair operations.

Live handset captures stay under ignored `proof/`. `tools/record_physical_proof.py` hashes raw subject identity and evidence; raw serial is not committed.

## Error handling and safety

- Missing PowerShell/PnP access -> `USB_DISCOVERY_UNAVAILABLE`.
- Malformed collector JSON -> `USB_DISCOVERY_INVALID`.
- No Huawei -> normal no-device result.
- Multiple Huawei devices -> guarded ambiguity.
- Huawei plus unrelated Android -> Huawei remains anchored to Huawei PnP identity.
- Shared/unknown VID/PID -> evidence-limited state, no model inference.
- All subprocess execution uses fixed argv arrays and `shell=False`.

## Testing

1. Pure state fixtures for storage-only, MTP, ADB, Fastboot, Recovery, Upgrade Mode, USB COM 1.0, unknown, and multiple-device ambiguity.
2. Regression fixture with one Huawei storage-only device plus one Redmi ADB device.
3. Deterministic fingerprint/privacy tests.
4. Windows collector tests with injected subprocess results.
5. DeviceEngine tests proving storage-only Huawei is connected/read-only and unrelated ADB is not selected.
6. Gateway payload tests proving raw serial omission and zero write authority.
7. Live ATHENA proof against the connected dead-screen Huawei.
8. Full pytest, source-freeze verification, strict 20-for-2 review, and GitHub source/UI CI.

## Acceptance criteria

- The connected `12D1:107E` handset is detected without screen interaction and classified `normal_android_charge_only` when only storage/CD-ROM interfaces exist.
- The simultaneously attached Redmi ADB device is not identified as Huawei.
- The public report has a stable physical fingerprint and no raw serial/write authority.
- The existing Gateway can record the endpoint without raw serial.
- The live evidence packet validates and only the new discovery matrix row may be promoted from its physical evidence.
- No existing software/UI proof regresses.

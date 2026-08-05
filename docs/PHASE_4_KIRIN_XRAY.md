# Phase 4 — Harden Kirin Xray

Status: IMPLEMENTATION IN PROGRESS  
Authority: `FULL_PLAN.md`  
Branch: `phase4/harden-kirin-xray`

## Purpose

Phase 4 builds the complete deterministic read-only Huawei evidence lane around the frozen Phase 2 contracts and the persistent Phase 3 TTG Device Gateway.

The exit condition is narrow:

> Kirin Xray explains the original P30 main-version failure and premature mode-release hazard without write access.

This phase does not implement or authorize loader transfer, OEMINFO modification, partition writes, flashing, reboot, unlock, relock, packaging, drivers or physical repair.

## Recovered authority

Specialist donor:

```text
Repository: jaydumisuni/kirin
Commit: d26152d38c197ba0bf98f41a66bed7ceb0575ce1
Version: 0.2.0
```

Private recovery authority:

```text
Drive file ID: 1qH4K0m1lX_3o0XLvCkJMXsDajOkfu2cs
Archive SHA-256: d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4
Raw publication allowed: false
```

Exact reviewed replay-source identities are frozen in:

```text
manifests/kirin_xray_sources.json
```

Raw private evidence is not copied into this repository. Public replay fixtures retain only reviewed classifications, paths, SHA-256 identities and redacted deterministic conclusions.

## Provider authority

Kirin Xray registers with the Gateway as:

```json
{
  "component_id": "kirin.xray",
  "version": "0.2.0",
  "device_access": "read_only",
  "contract_authorities": [
    "diagnosis",
    "observation",
    "verification"
  ],
  "capabilities": [
    "contract.publish",
    "evidence.read"
  ]
}
```

The provider may publish only:

- `physical_device_session`;
- `endpoint_observation`;
- `device_evidence`;
- `device_twin`.

Every emitted payload fixes `write_allowed` to `false`.

## Replay adapter

Implementation:

```text
techguy_huawei/kirin_xray.py
```

The adapter:

- rejects unknown and missing replay members;
- rejects malformed donor identities and source SHA-256 values;
- rejects stale or invented capture-time claims;
- rejects invalid source references;
- rejects capabilities containing write, flash, erase, loader, reboot, unlock or relock authority;
- derives deterministic UUIDv5 session and contract identities;
- hashes canonical Phase 2 JSON deterministically;
- validates every rendered contract against the frozen Phase 2 registry;
- binds contracts to the runtime Gateway physical session before publication;
- records endpoint observations through the Gateway;
- preserves `device_authority = none` and `xray_authority = read_only`.

Replay timestamps are deterministic validation coordinates, not claimed historical capture times. Every fixture declares:

```text
basis = deterministic_replay_not_capture_time
```

## P10 replay

Fixture:

```text
replay/kirin/p10_golden_workflow.json
```

The replay records the recovered theorem:

```text
retain service environment
→ restore complete model-correct OEMINFO version identity
→ continue target firmware
→ restore stock recovery/Fastboot only at finalization
```

It also records that the named small metadata images were absent from the studied package. Their names therefore do not prove standalone writable partitions.

## P30 replay

Fixture:

```text
replay/kirin/p30_main_version_mode_hazard.json
```

The replay explains:

- `VERSION` was valid and accepted;
- `MAIN VERSION` remained missing;
- the missing state belonged to OEMINFO version identity;
- no standalone writable verlist partition was proved;
- vendor/country evidence was contradictory while OEMINFO state was incomplete;
- `VBMETA_HW_PRODUCT` was required;
- matching CUST/PRELOAD package metadata existed;
- the unresolved issue was the service/tool path, not missing package files;
- restoring stock Fastboot or rebooting too early could remove the service capability required to finish recovery.

The replay emits no repair recipe and no execution or governance contract.

## Proof requirements

Source tests must prove:

- exact donor and private-source authority;
- deterministic replay bytes and SHA-256 identities;
- Phase 2 validation of every emitted contract;
- explicit P10 theorem and P30 failure/hazard findings;
- fail-closed malformed, stale, invalid-reference and forbidden-capability handling;
- runtime Gateway session binding;
- read-only provider registration;
- absence of write authority.

Hosted proof must additionally build the real Rust Gateway and prove:

- both replays publish through the actual loopback protocol;
- accepted contracts are limited to the four approved read-only types;
- the journal verifies;
- provider and physical sessions survive Gateway restart;
- the final snapshot remains `device_authority = none` and `xray_authority = read_only`.

Proof entry point:

```text
python tools/prove_kirin_xray_replay.py \
  --gateway-bin rust/device_gateway/target/debug/ttg-device-gateway
```

## Truth boundary

Until hosted proof and owner verification are frozen, Phase 4 remains in progress.

Not proved by this implementation:

- raw private P10/P30 evidence contents in public source;
- live Huawei USB discovery on physical hardware;
- live P30 provider operation against the owner device;
- service-loader compatibility;
- OEMINFO construction or modification;
- any executor, mode lease or execution lease;
- physical VOG-L29 recovery or branding normalization.

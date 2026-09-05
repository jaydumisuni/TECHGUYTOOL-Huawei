# Phase 3 — TTG Device Gateway

Status: persistent control-plane authority with a later read-only live-USB discovery extension.

## Purpose

The TTG Device Gateway is the always-running Rust control plane between the Qt/QML client and future specialist providers, governors, and bounded workers.

The UI is a client. Closing or restarting the UI must not discard:

- physical-device identity;
- endpoint observations;
- operation identity;
- current operation stage;
- provider registration;
- worker state;
- evidence-journal history.

Phase 3 consumes the frozen Phase 2 contracts. It does not activate a production executor.

## Implemented control-plane surfaces

The `techguy-device-gateway` crate provides:

- SQLite schema version 1;
- physical-device session registry;
- endpoint-observation registry;
- operation-session registry;
- ordered operation-stage policy;
- typed gateway events;
- append-only SHA-256 hash-chained journal;
- provider manifests and contract-authority declarations;
- fail-closed capability allowlists;
- Phase 2 contract validation at ingress;
- worker registration, heartbeat, deadline, and timeout state;
- process-start recovery markers;
- `doctor` diagnostics;
- deterministic snapshots;
- a loopback-only UTF-8 JSON-lines protocol;
- a reconnect-safe Python UI client.

## Persistent state

The Gateway owns one SQLite file. Runtime databases belong under ignored mutable runtime storage and never in Git.

Tables:

- `gateway_meta`
- `physical_sessions`
- `endpoint_observations`
- `operation_sessions`
- `providers`
- `workers`
- `journal_events`

Every startup validates schema version 1 and the complete journal chain. Active physical sessions retain their identity. Active operations retain their stage and enter `recovering` until a client explicitly resumes them. A corrupt journal blocks normal Gateway startup while the read-only `doctor` path remains available.

## Operation stages

Phase 3 defines control-plane stages only:

```text
requested
→ evidence_collection
→ decision_pending
→ authorization_pending
→ verification_pending
→ completed
```

Deterministic side exits:

```text
blocked
failed
cancelled
```

No Phase 3 stage performs a device-changing command. `authorization_pending` means only that a future governor may evaluate authority; it does not grant authority.

## Provider and capability policy

A provider manifest declares:

- stable component ID;
- ASCII semantic version;
- `none` or `read_only` device access;
- contract authorities;
- sorted, unique capabilities.

Phase 3 allowlisted capabilities:

- `contract.publish`
- `diagnostics.read`
- `evidence.read`
- `journal.append`
- `operation.coordinate`
- `session.coordinate`
- `worker.heartbeat`

Device-changing capabilities are rejected, including flash, erase, loader transfer, partition write, reboot, relock, unlock, and OEMINFO write.

A contract authority does not become a device capability. The Gateway validates the Phase 2 contract, checks producer identity, checks provider authority, checks physical-session existence when supplied, journals acceptance, and still retains `device_authority = none`.

## Journal

Every event records:

- monotonic sequence;
- event UUID;
- typed event kind;
- producer;
- physical-session and operation references;
- UTC timestamp;
- JSON payload;
- previous event hash;
- event hash.

The event hash is the Phase 2 canonical SHA-256 of the event core. `doctor` fails if any payload, previous hash, or event hash is altered.

## Local protocol

The binary listens only on loopback.

```text
127.0.0.1:49321
```

Transport is one UTF-8 JSON request and response per line. Requests carry a unique `request_id`. Responses repeat that ID and return either a result or a stable error code.

Supported commands include health, doctor, snapshot, physical-session operations, endpoint recording, operation transitions, provider registration, contract ingress, worker heartbeat/watchdog operations, journal listing/verification, and local shutdown.

The protocol exposes no shell command, arbitrary process execution, device command, partition target, loader path, firmware path, or reboot request.

## Proof

The Rust suite proves:

- physical identity and operation stage survive Gateway restart;
- recovered operations retain their exact stage;
- provider and worker capability policy rejects device-write authority;
- Phase 2 contract ingress is validated and producer/authority bound;
- worker deadlines produce deterministic timeout state;
- journal tampering is detected and blocks normal startup;
- the source has no device-execution command surface;
- separate loopback clients reconnect to the same operation.

The Python suite proves UTF-8 protocol handling, request correlation, structured errors, and loopback-only configuration.

`tools/prove_gateway_reconnect.py` launches the real binary, opens a physical session and operation, reconnects with a new UI client, restarts the Gateway process with the same SQLite database, resumes the recovered operation, verifies the journal, and proves that a non-allowlisted capability is rejected.

## Exit gate

Phase 3 is complete only when hosted proof confirms:

```text
UI client reconnect preserves physical-device identity and operation stage
Gateway process restart preserves physical-device identity and operation stage
recovered operations are explicit and resumable
journal chain verifies
non-allowlisted device capability is rejected
device_authority remains none
xray_authority remains read_only
```

## Explicit exclusions

### Later read-only USB discovery extension

Physical certification on a dead-screen Huawei exposed a gap between the persistent Gateway contract and Windows device discovery. The later extension may enumerate present Windows PnP/USB metadata, classify Huawei interface states, derive a privacy-preserving physical fingerprint, and record the resulting endpoint through the existing `open_physical_session` / `record_endpoint` contract.

This extension is screen-independent and read-only. It does not send vendor USB commands, change drivers, force modes, transfer loaders, read partitions, infer an exact model from a shared VID/PID, or widen write authority. A storage-only `VID_12D1:PID_107E` observation is therefore `storage_only_pre_service`, not MTP or Upgrade Mode unless the corresponding interfaces are actually observed.

Phase 3 does not prove or authorize:

- active MTP, ADB, Fastboot, HUAWEI USB COM 1.0, or Testpoint protocol communication (the later extension may classify these interfaces read-only from Windows PnP evidence);
- loader/programmer/DA transfer;
- OEMINFO construction or write;
- partition read or write;
- flashing, erase, unlock, relock, or reboot;
- mode or execution lease enforcement around a physical device;
- Windows service installation;
- Windows one-file packaging or signing;
- physical VOG-L29 repair.

Those remain later phases under `FULL_PLAN.md`.

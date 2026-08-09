# Phase 7 — Bounded Executor Framework

## Purpose

Phase 7 introduces the first execution framework, but not a Huawei device write adapter. It consumes Phase 6 execution leases internally, validates the exact stage request, then invokes only a registered adapter whose ID and version match the lease. The framework returns raw execution evidence and verifies mandatory backup/readback conditions before reporting a stage as verified.

## Authority flow

```text
Xray evidence (read-only)
        ↓
Decision Corps / Governor
        ↓
Mode + execution leases
        ↓
BoundedExecutor owns LeaseGuard
        ↓
Registered bounded adapter
        ↓
Raw result / backup / readback evidence
        ↓
Xray verification in later phases
```

The public execution API does **not** accept an `ExecutionPermit` from callers. It accepts the original frozen execution-lease contract plus the exact execution context and stage request. The executor itself claims and consumes the lease through its private `LeaseGuard` before calling an adapter. A caller therefore cannot bypass lease validation by handing the executor a fabricated permit.

## Request binding

Before a lease is consumed, the executor requires exact equality for:

- physical-device session;
- stage ID;
- target partition;
- adapter ID;
- adapter version;
- current device/service mode;
- range-manifest SHA-256;
- reboot request.

It also validates:

- payload SHA-256;
- payload hash is one of the lease-authorized artifact hashes;
- payload byte count equals the bounded lease write count;
- adapter identity exists in the registered adapter map.

## Post-adapter verification

After the adapter returns, the executor requires:

- reported bytes written exactly equal the lease-bound byte count;
- mandatory backup hash when the operation requires backup;
- mandatory readback hash when the operation requires readback;
- exact readback hash equality with the payload when requested;
- cancellation did not occur during adapter execution.

An adapter success code by itself never proves the stage.

## Cancellation behavior

Cancellation is checked:

1. before lease claim — no authority consumed;
2. after lease claim — authority is consumed but the adapter is not called;
3. after adapter return — stage is rejected if cancellation occurred during the adapter.

Once an execution lease has been claimed, it is intentionally never reusable. This is fail-closed: an interrupted stage must be diagnosed and explicitly replanned rather than silently replaying old authority.

## Phase 7 adapters

Phase 7 proof uses an in-memory test adapter only. No USB, serial, ADB, Fastboot, loader, OEMINFO, partition or flashing backend is registered in production by this phase.

The real Kirin adapters are introduced only after the P10 golden workflow theorem and VOG-L29 C185 recipe are encoded and bounded by the same contracts.

## SRG 20-for-2

Phase 7 must pass two independent 20-check SRG review waves. Build output is removed before the source-only SRG pass so compiler cache files cannot be mistaken for bundled firmware.

## Exit gate

Phase 7 is complete only when proof demonstrates:

- exact authorized request executes once;
- reused lease fails;
- unregistered adapter fails before lease claim;
- wrong session, stage, partition, adapter, version, mode, range or reboot request fail;
- payload hash, artifact authority and size fail closed;
- missing backup/readback fail;
- readback mismatch fails;
- adapter write-count mismatch fails;
- cancellation before and during execution fails closed;
- duplicate adapter identity is rejected;
- complete Phase 2–6 regressions remain green;
- SRG result is 40/40;
- no device transport exists in the Phase 7 executor source.

## Truth boundary

Phase 7 proves the deterministic bounded executor framework. It does **not** prove a physical device write, Huawei USB loader transfer, OEMINFO write, partition flash, reboot, driver install, Windows packaging, code signing, or physical repair certification.

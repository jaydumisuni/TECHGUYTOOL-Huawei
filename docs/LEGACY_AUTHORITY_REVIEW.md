# Legacy Huawei Revive Authority Review

**Review type:** static source-boundary recovery  
**Source:** private `huawei Revive.zip` archive  
**Archive SHA-256:** `d98d44364387431f86d4bad2e725bb5e6612f32a1f1884436a4285872c87efc4`

## Finding

The historical Revive package is valuable and authoritative evidence, but it is a **mixed-authority recovery workspace**, not a production architecture that can be imported unchanged.

## Recovered capability groups

### Read-only evidence capability

The packaged Xray source contains provider discovery, physical-session correlation, evidence envelopes, deterministic review, firmware/package parsing, simulation, and explicit statements that Xray cannot authorize writes.

### Artifact construction and planning capability

The same package also contains OEMINFO image construction, UPDATE.APP extraction, board XML operation parsing, service-environment planning, recovery-image construction, and workflow generation.

### Active transport/write capability

Recovered modules and scripts include:

- serial writes used to transfer Kirin loader frames;
- loader-stage selection for service Fastboot;
- a VOG-L29 full-flash runner issuing `fastboot ... flash` operations;
- a hard-coded physical device serial and target profile;
- operation plans containing flash, erase, OEMINFO, reboot, and finalization stages.

## Required correction

The historical `xray` namespace may not become production Xray as-is. Later phases must separate it into at least:

1. **Kirin Xray provider pack** — read-only observations, parsers, diagnosis, contradiction rules, prediction, and verification.
2. **Artifact laboratory** — offline builders and validators that never contact a device.
3. **Recipe compiler** — deterministic translation from certified evidence plus an approved recipe into a bounded execution lease.
4. **Rust executor adapters** — device-facing transport/write workers that cannot exceed the lease.
5. **Inquiry records** — prediction/result/post-evidence comparisons and governed learning candidates.

## Frozen rule

No loader transfer, OEMINFO construction, flash operation, device-bound serial, or historical live log is promoted merely because it worked once. Promotion requires typed contracts, exact artifact provenance, model/board compatibility, privacy review, replay proof, hardware proof, and independent verification.

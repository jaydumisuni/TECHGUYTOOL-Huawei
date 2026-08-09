# Phase 9 — VOG-L29 C185 Production Recipe

Phase 9 freezes the first complete **software recipe** for the VOG/P30 Pro recovery lane. It converts the proven P30 evidence, Phase 8 golden theorem, Phase 5 governor, Phase 6 leases, and Phase 7 bounded executor into one deterministic VOG-L29/C185 plan.

## Target

```text
source service state: VOG-AL00 or VOG-L29 board-service profile
target:               VOG-L29
region:               C185
SoC:                  Kirin 980
vendor/country:       hw / meafnaf
reference family:     VOGUE-L29D 10.0.0.186(C185E8R5P1)
```

The reference build family is evidence, not permission to substitute a different package. Every real run must bind the exact selected Base, CUST, PRELOAD, service-loader, recovery, rollback, backup and range-manifest hashes.

## Frozen workflow

```text
certify physical session
→ preserve Board-Service Fastboot
→ verify OEMINFO backup and rollback authority
→ derive VOG-L29/C185 identity from exact firmware
→ compile reviewed OEMINFO identity patch
→ bounded OEMINFO identity stage
→ read back and verify main-version/identity
→ continue validated Base/CUST/PRELOAD
→ derive SUPER sparse plan from the exact artifact
→ bounded SUPER continuation
→ verify target boot environment
→ restore target stock recovery
→ restore target stock Fastboot
→ release service-mode lease
→ intentional reboot
→ verify normal boot
→ normalize only proven incorrect branding fields
→ final Xray device twin
```

No SUPER chunk count is hard-coded. No OEMINFO record offset is published as generic authority. Exact range authority is supplied at runtime by reviewed SHA-256 manifests and is enforced by the Phase 6/7 Rust boundary.

## Required preflight evidence

The compiler refuses to produce a simulation/operation plan without:

- one UUID-pinned physical session;
- certified device continuity;
- VOG-L29 / Kirin 980 / C185 target evidence;
- verified board identity evidence hash;
- Xray and storage-inventory hashes;
- certified `board_service_fastboot`;
- a no-reboot mode lease;
- exact target package-manifest hash;
- verified Base/CUST/PRELOAD relationship;
- resolved compatible anti-rollback state;
- exact required artifact hashes and provenance hashes;
- exact per-stage range-manifest hashes.

Unknown, stale, mismatched, malformed, extra, or missing authority fails closed.

## OEMINFO boundary

The recipe records the verified VOG layout requirement:

```text
total: 96 MiB
copy A: 48 MiB
copy B: 48 MiB
```

It requires backup and readback, derives target identity from the selected target firmware, and preserves device-specific board records. It deliberately does **not** hard-code generic OEMINFO record offsets.

## Finalization boundary

Stock recovery/Fastboot restoration and service-mode release require all of:

- `target_identity_verified`
- `remaining_firmware_completed`
- `target_boot_environment_ready`

The reboot stage is unreachable before service-mode release.

Branding normalization is separate from core recovery. A booting/version-restored phone may still report:

```text
BRANDING_NORMALIZATION_REQUIRED
```

instead of falsely reporting `FULL_REPAIR_CONFIRMED`.

## Physical-certification boundary

The public repository can prove the recipe compiler, historical replay, artifact/range binding, stage ordering and fail-closed policy. It cannot manufacture a real VOG hardware certification.

Therefore Phase 9 software authority remains:

```text
software_recipe = FROZEN after CI
simulation = REQUIRED/PASS before freeze
historical_replay = REQUIRED/PASS before freeze
physical_vog = HARDWARE_PENDING
production_enabled = false
device_authority = none
```

A future physical proof must supply real device evidence, exact artifact hashes, executor journal/readback, final Xray twin and branding result. Until then no software test may flip `production_enabled`.

## Exit accounting

Software-completable exit gate:

- deterministic VOG-L29/C185 recipe validates;
- P30 historical replay supports its causal ordering;
- artifact/range authority is exact-hash bound;
- donor VTR/C432 data is rejected;
- premature service release is impossible;
- simulation and adversarial tests pass;
- SRG 20-for-2 passes both waves (40/40);
- historical Phase 2–8 regressions remain green;
- source inventory and Phase 9 software receipt are frozen.

Hardware exit gate remains separately visible as `HARDWARE_PENDING` until a physical VOG run passes end to end.

# Phase 11 — Xray Knowledge Workshop

Phase 11 gives read-only Xray understanding a governed improvement lifecycle without increasing device-write authority.

## Lifecycle

```text
quarantined
→ replay_supported
→ hardware_supported
→ specialist_approved
→ ttg_promoted
```

`rejected` is terminal and may occur before promotion.

## Inputs

The Workshop accepts only valid frozen Phase 2 `learning_proposal` contracts. Proposals must enter as `quarantined` and preserve their gap ID, proposal contract ID and original replay fixture hashes.

## Read-only change classes

- `read_only_parser`
- `diagnostic_rule`
- `verification_requirement`

Rules:

- read-only parser: replay + regression + challenge can establish replay support; specialist approval is still required before a Phase 13 promotion candidate is emitted;
- diagnostic rule: replay + regression + challenge + specialist canary + external hardware proof are required before specialist approval;
- verification requirement: replay + regression + challenge + external hardware proof are required before specialist approval.

A validator test may exercise the hardware-proof field using synthetic hashes, but that does **not** create real hardware certification. Real `hardware_supported` evidence must come from an independent physical proof record.

## Permanently dangerous classes

- `write_target`
- `write_offset`
- `destructive_recipe`
- `expanded_authority`

These never leave quarantine through the read-only Workshop and never receive automatic promotion.

## Evidence custody

Every transition retains or adds exact hashes for:

- origin replay fixtures;
- replay/challenge fixtures;
- regression result;
- challenge result;
- canary result where applicable;
- hardware proof where applicable;
- specialist approval;
- final Phase 13 promotion receipt;
- explicit limitations.

Dropping original replay evidence or changing proposal/gap identity fails closed.

## Promotion boundary

Phase 11 can emit a `SPECIALIST_APPROVED_PENDING_PHASE13` read-only promotion candidate. It does not write to TTG Device X-Ray itself. Phase 13 owns that promotion and its receipt.

## Authority

```text
authority = read_only_learning
execution_authority = none
device_authority = none
```

The Workshop cannot invoke a loader, write a partition, generate an execution lease, reboot a phone, or install arbitrary code.

## Exit gate

- quarantine is mandatory;
- replay/regression/challenge evidence is hash-bound;
- diagnostic-rule canary requirements are enforced;
- hardware-proof requirements are explicit and not fabricated by software tests;
- dangerous change classes never auto-promote;
- read-only specialist-approved candidates contain no execution authority;
- deterministic/adversarial tests pass;
- SRG 20-for-2 passes 40/40;
- historical regressions remain green;
- source inventory and Phase 11 software receipt are frozen.

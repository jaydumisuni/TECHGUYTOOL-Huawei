# Phase 10 — Inquiry Governor

Phase 10 turns unexplained repair outcomes into deterministic evidence work instead of generic retries.

## Purpose

The Inquiry Governor compares three authorities:

```text
Xray prediction
vs
Executor raw result/readback
vs
post-operation Xray evidence
```

A successful executor stage is not automatically a successful repair. If the executor reports success/readback but the predicted device state does not appear, the system creates a structured `KnowledgeGap`, requests only registered read-only probes, and creates a quarantined learning proposal.

The original P30 main-version investigation is the reference failure shape:

```text
prediction: main version should be restored
executor: stage accepted + readback available
post-Xray: main version still missing
```

The deterministic result is:

```text
EXPECTED_RESULT_NOT_OBSERVED
→ structured knowledge gap
→ read-only version/identity probes
→ quarantined learning candidate
→ no generic retry
```

## Inquiry Corps

Eight officers evaluate one immutable input snapshot in fixed order:

1. Prediction Auditor
2. Evidence Completeness Officer
3. Contradiction Officer
4. Probe Planner
5. Hypothesis Officer
6. Challenger
7. Learning Judge
8. Inquiry Governor

The officers do not vote to expand authority. They classify evidence and route unresolved understanding to quarantine.

## Registered probes

The canonical Phase 10 registry is `manifests/inquiry_probe_registry.json`.

Only registered Xray/observation probes with `write_allowed=false` may be requested. The Inquiry Governor cannot request:

- loader transfer;
- arbitrary shell execution;
- partition writes;
- firmware flashing;
- reboot;
- unlock/relock;
- OEMINFO construction;
- executor authority.

Unknown probe IDs fail closed.

## Knowledge gaps

Phase 10 emits frozen Phase 2 `knowledge_gap` contracts with one of the approved primary codes:

- `EXPECTED_RESULT_NOT_OBSERVED`
- `REQUIRED_EVIDENCE_MISSING`
- `XRAY_EXPLANATION_INCOMPLETE`
- `ADDITIONAL_READ_ONLY_PROBE_REQUIRED`

The gap starts at lifecycle state `questioned` and references the prediction, executor result, verification result, physical session and requested read-only probes.

## Learning candidates

An unexplained outcome may produce a Phase 2 `learning_proposal` only as:

```text
status = quarantined
auto_promotion_allowed = false
```

Phase 10 does not promote anything. Phase 11 owns replay/challenge/canary/hardware/promotion lifecycle.

## Fail-closed result classes

```text
VERIFIED
    predicted state and verification agree

STOP_EXECUTOR_RESULT
    executor itself did not produce the predicted outcome; stop instead of inventing a knowledge lesson

KNOWLEDGE_GAP
    executor/readback and post-Xray evidence do not support the expected causal explanation
```

`generic_retry_allowed` is always false.

## Authority boundary

```text
probe_authority = registered_read_only_only
learning_authority = quarantine_only
execution_authority = none
device_authority = none
touches_device = false
```

Phase 10 consumes evidence and contracts. It never directly invokes the device, Gateway transport or bounded executor.

## Exit gate

Phase 10 is software-complete when:

- the P30 accepted/readback-but-main-version-missing scenario becomes a structured knowledge gap;
- missing evidence and contradictory evidence are distinguished;
- explained executor failure stops without creating fake learning;
- every requested probe is registered and read-only;
- learning candidates remain quarantined with no auto-promotion;
- successful predictions do not create false gaps;
- deterministic/adversarial tests pass;
- SRG 20-for-2 passes both waves (40/40);
- Phase 2–9 regressions remain green;
- source inventory and Phase 10 receipt are frozen.

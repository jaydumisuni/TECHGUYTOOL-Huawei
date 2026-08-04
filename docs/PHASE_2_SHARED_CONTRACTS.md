# Phase 2 — Shared Python/Rust Contracts

**Status:** FROZEN — EXIT GATE SATISFIED  
**Authority:** `FULL_PLAN.md`, Phase 2  
**Device authority:** none; this phase is device-inert  
**Frozen branch:** `phase2/shared-contracts`

## Purpose

Phase 2 freezes the versioned data contracts used by Xray, the future TTG Device Gateway, deterministic governors, bounded executors, verification, recovery, and governed learning.

The same contract document receives the same validity verdict, canonical JSON, SHA-256 identity, and safety error codes in Python and Rust.

## Frozen contract types

1. `physical_device_session`
2. `endpoint_observation`
3. `device_evidence`
4. `device_twin`
5. `operation_request`
6. `repair_recipe`
7. `recipe_candidate`
8. `decision_verdict`
9. `mode_lease`
10. `execution_lease`
11. `executor_result`
12. `verification_result`
13. `knowledge_gap`
14. `learning_proposal`
15. `capability_pack`
16. `artifact_manifest`
17. `recovery_plan`

## Canonicalization

Canonical JSON is UTF-8 JSON with:

- object keys sorted lexicographically;
- no insignificant whitespace;
- array order preserved;
- integers only; floating-point values are rejected;
- Unicode preserved consistently by both implementations.

The contract SHA-256 is calculated over the canonical UTF-8 bytes.

## Fail-closed checks

The validators reject:

- malformed or non-object JSON;
- missing and unknown fields;
- unknown contract types;
- unsupported schema versions;
- invalid UUID, SHA-256, timestamp, semantic-version, and pattern values;
- unsorted or duplicate authority arrays;
- authority, physical-session, expiry, and single-use mismatches;
- future creation, invalid expiry, stale contracts, and invalid consumption state;
- context mismatches for contract type, authority, physical session, recipe, and artifacts;
- timestamp-order violations;
- automatic promotion of write targets, offsets, destructive recipes, or expanded authority.

## Frozen proof corpus

- 17 valid canonical fixtures, one for each contract type;
- 34 invalid mutation fixtures;
- one malformed-JSON fixture;
- six Python contract tests;
- three Rust integration tests covering the complete fixture corpus;
- exact cross-language validity, canonical JSON, error-code, and SHA-256 proof across 52 cases;
- complete non-Qt Python regression;
- Rust formatting and Clippy gates;
- dependency lockfile generated and inventory-bound under Rust 1.75.0.

## Proof result

Hosted workflow `Phase 2 Shared Contracts` completed successfully after the following corrections were proven:

1. Rust sources were formatted deterministically.
2. Dependencies were pinned to Rust-1.75-compatible versions.
3. The equivalence runner was made independent of the caller's Python import path.
4. Source inventory generation was moved before the complete regression suite.
5. The generated Cargo lockfile was registered as intended source before inventory validation.
6. The proof receipt was generated only after all proof gates passed.

Frozen receipt: [`../manifests/source_inventory.receipt.json`](../manifests/source_inventory.receipt.json)

## Safety boundary

This phase does not:

- inspect a live device;
- transfer a loader;
- flash, erase, unlock, relock, or reboot;
- write OEMINFO or any partition;
- activate a repair recipe;
- expand Xray beyond read-only authority.

`execution_lease` is only a validated contract shape in this phase. No executor consumes it yet.

## Exit gate result

- Python valid fixtures: **17/17 PASS**
- Python invalid fixtures: **34/34 PASS**
- malformed JSON fixture: **1/1 PASS**
- Rust valid fixtures: **17/17 PASS**
- Rust invalid fixtures: **34/34 PASS**
- exact Python/Rust canonical JSON equivalence: **PASS**
- exact Python/Rust SHA-256 equivalence: **PASS**
- exact Python/Rust error-code equivalence: **PASS**
- `cargo fmt --check`: **PASS**
- `cargo clippy --all-targets -- -D warnings`: **PASS**
- `cargo test`: **PASS**
- complete Python regression: **PASS**
- source-freeze verification after inventory regeneration: **PASS**

Phase 2 authorizes Phase 3 Gateway work. It does not authorize physical device execution.

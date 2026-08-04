# Phase 2 — Shared Python/Rust Contracts

**Status:** implementation candidate  
**Authority:** `FULL_PLAN.md`, Phase 2  
**Device authority:** none; this phase is device-inert

## Purpose

Phase 2 freezes the versioned data contracts used by Xray, the future TTG Device Gateway, deterministic governors, bounded executors, verification, recovery, and governed learning.

The same contract document must receive the same validity verdict, canonical JSON, SHA-256 identity, and safety error codes in Python and Rust.

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

## Proof corpus

The branch contains:

- 17 valid canonical fixtures, one for each contract type;
- 34 invalid mutation fixtures;
- one malformed-JSON fixture;
- Python fixture tests;
- Rust fixture tests;
- exact cross-language canonical and SHA-256 equivalence proof;
- Rust formatting and Clippy gates.

## Safety boundary

This phase does not:

- inspect a live device;
- transfer a loader;
- flash, erase, unlock, relock, or reboot;
- write OEMINFO or any partition;
- activate a repair recipe;
- expand Xray beyond read-only authority.

`execution_lease` is only a validated contract shape in this phase. No executor consumes it yet.

## Exit gate

Phase 2 may merge only when hosted proof confirms:

- Python valid fixtures: 17/17;
- Python invalid fixtures: 34/34 plus malformed JSON;
- Rust valid fixtures: 17/17;
- Rust invalid fixtures: 34/34 plus malformed JSON;
- exact Python/Rust canonical JSON equivalence: PASS;
- exact Python/Rust SHA-256 equivalence: PASS;
- `cargo fmt --check`: PASS;
- `cargo clippy --all-targets -- -D warnings`: PASS;
- `cargo test`: PASS;
- Phase 1 source-freeze verification remains coherent after inventory regeneration.

Passing this phase authorizes Phase 3 Gateway work. It does not authorize physical device execution.

# TECHGUYTOOL Huawei Shared Contracts

`registry.json` is the single schema authority for the Python and Rust contract engines.

## Files

- `registry.json` — all envelope and payload definitions.
- `fixtures/valid_contracts.json` — one valid canonical example per contract type.
- `fixtures/invalid_contracts.json` — deterministic mutation cases and stable expected error codes.

## Rules

- Keep this layer device-inert.
- Never add execution code, firmware, loaders, customer identifiers, or operation logs.
- Do not change a schema without updating both engines, both fixture bundles, Phase 2 documentation, and hosted cross-language proof.
- Unknown fields and unsupported versions fail closed.
- `execution_lease` is the only single-use contract in version 1.
- Capability packs never include execution.
- Destructive knowledge never gains automatic promotion authority.

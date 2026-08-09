# Phase 13 — TTG Device X-Ray Promotion

## Objective

Promote the frozen Huawei/Kirin read-only diagnostic capability into the consolidated `jaydumisuni/TTG-Device-X-Ray` repository without moving Kirin executor code or expanding device authority.

## Frozen source

The promoted source is Phase 12 merge:

`93a8bd705bd9e8d8bade40f0e15181644211812e`

The Kirin capability-set manifest is:

`packs/kirin/manifest.json`

with SHA-256:

`3859e0e71495a4847c8698714494b5ce94264d12d6d8eaa663d4d56c45b8fc9f`

Its maturity remains `replay_supported` and `includes_execution=false`.

## Independent target proof

TTG Device X-Ray PR #24 reviewed head:

`359db4522f185c8e0430e4c2a4c5a06281f52e25`

was tested by target-repository CI run:

`31339256277`

The complete target gate passed:

- profile validation;
- replay fixture validation;
- read-only command enforcement;
- public privacy enforcement;
- Python 3.10, 3.11, 3.12, 3.13 and 3.14 tests;
- Windows smoke tests and CLI doctor;
- Python package build/metadata checks;
- standalone Qt Windows EXE build and validation;
- final CI Gate.

The promoted target was merged at:

`34feb55ab937fa865726cbb22c44b09b52084114`

## Exit-gate result

The target repository now independently evaluates the frozen VOG replay and explains all four required conclusions from its native promoted capability:

1. the accepted VERSION write did not restore MAIN VERSION and the replay evidence points to OEMINFO version identity rather than a proven writable standalone verlist partition;
2. Board-Service Fastboot must remain preserved while the unresolved repair still needs it;
3. stock Fastboot restoration is finalization-only after release conditions;
4. residual branding mismatch after core boot recovery is a separate normalization stage.

The evaluator is evidence-conditioned and does not force the historical OEMINFO explanation when counter-evidence is supplied.

## Authority boundary

Phase 13 grants no new write or execution authority.

The TTG Device X-Ray promoted profile exposes:

- `write_allowed=false`;
- no adapter contracts;
- `repair_profile_ready=false`;
- `execution_authority=none`;
- replay-supported diagnostic maturity only.

Physical VOG repair certification remains `HARDWARE_PENDING` and is not implied by this software promotion.

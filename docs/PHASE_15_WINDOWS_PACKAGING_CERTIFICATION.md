# Phase 15 — Windows packaging and certification

## Objective

Build the final Windows release-candidate path for `TECHGUYTOOL_Huawei.exe`, prove it on a clean hosted Windows runner, and record the remaining external certification boundary without inventing hardware results.

## Existing release path retained

The repository already used `build_windows.ps1` and `pysidedeploy.spec` as the canonical Windows release path. Phase 15 hardens that path instead of creating a second builder.

The release path requires:

- Python 3.11+;
- PySide6 and QML resources;
- the Rust health core;
- the complete Python test suite;
- strict SRG 20-for-2 review;
- one-file `pyside6-deploy`/Nuitka packaging;
- exact output name `TECHGUYTOOL_Huawei.exe`;
- Authenticode for production signing;
- SHA-256 checksum output.

## Signing modes

Production signing remains strict:

- a real production certificate is never committed to this repository;
- the canonical build uses Authenticode and timestamping when the production certificate is present;
- absence of a production certificate means the binary is not production-release eligible.

GitHub Actions may use a short-lived self-signed **CI test certificate** solely to prove that the exact executable can be signed, exposes the expected signer identity, and carries the expected Authenticode structure. The temporary PFX password is generated cryptographically at runtime, masked before it is exported to later workflow steps, and is never committed. CI does not add the self-signed certificate to the Windows trust store. CI test signing is blocked outside GitHub Actions and is never represented as production signing or production trust.

## Windows CI proof

The Phase 15 Windows workflow runs on `windows-latest` and proves:

1. a fresh Windows runner exposes PnP and driver-management tooling;
2. Python/Rust dependencies install from the frozen source;
3. a temporary CI-only code-signing certificate and randomized masked PFX password are created for the job without trust-store mutation;
4. the canonical builder creates the one-file executable;
5. the resulting executable exposes the expected CI-only Authenticode signer and signing provenance;
6. the emitted SHA-256 checksum matches the executable;
7. the one-file binary starts, is forcibly terminated, and starts again, exercising runtime extraction and restart-after-abnormal-close behavior;
8. release provenance records the distinction between CI test signing and production signing.

## Physical proof matrix

The physical proof matrix is not transformed into software success.

Every minimum item from the frozen plan is represented in `manifests/phase15_physical_proof_matrix.json`. The only accepted completion token for a physical requirement is `PHYSICAL_PASS`. No entry is currently assigned that token because this repository/CI session does not possess the required real devices or servicing-machine driver evidence.

Therefore:

- software release engineering may be frozen and proven;
- the Windows release candidate may be built and CI-signed;
- production release remains `EXTERNAL_CERTIFICATION_PENDING`;
- `production_enabled` remains `false`;
- VOG, Qualcomm and MediaTek physical certification remain pending.

## Physical evidence recorder

Physical certification evidence is recorded with `tools/record_physical_proof.py`. The recorder is deliberately read-only with respect to project authority:

- it accepts one existing physical-matrix entry id;
- it hashes a subject-identity JSON object but does **not** embed the raw subject values in the output packet;
- it hashes every captured evidence file and records only filename, size and SHA-256;
- `evidence_sha256` is the SHA-256 of canonical evidence material binding the matrix entry id, verifier, UTC verification time, subject hash, evidence references and captured-file hashes;
- it requires at least one retained evidence reference and verifier identity;
- it validates the generated six-field evidence record against the existing Phase 15 matrix contract;
- output is restricted to the repository's ignored `proof/` tree;
- it never edits `phase15_physical_proof_matrix.json` and never promotes an entry to `PHYSICAL_PASS`.

Example:

```powershell
python tools/record_physical_proof.py `
  --entry-id mtp_direct_route `
  --subject-json proof/physical/vtr-l29/subject.json `
  --evidence-file proof/physical/vtr-l29/pnp.txt `
  --evidence-ref artifact://athena/vtr-l29/pnp.txt `
  --verifier "THETECHGUY physical certification" `
  --output proof/physical/vtr-l29/mtp-direct-route.packet.json
```

The subject JSON may contain exact serial/board identity required to bind the physical subject; those raw values remain outside the packet. The packet carries only `subject_identity_hash`. Raw captures remain external proof material and must not be committed as source.

A matrix update is a separate reviewed action after the packet and referenced raw evidence have been checked.

## Final truth boundary

A green Phase 15 software receipt means the source, packaging path, Windows CI build, restart behavior, checksum policy and signing mechanism are proven.

It does **not** mean the frozen plan's physical proof matrix has passed. Shipping as a production-certified servicing tool requires the outstanding real-hardware and production-certificate evidence to be attached later.

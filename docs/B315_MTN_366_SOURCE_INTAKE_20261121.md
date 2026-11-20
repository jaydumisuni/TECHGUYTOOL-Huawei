# Huawei B315s-22 MTN `.366` — Exact-Version Archive Intake (2026-11-21)

## Authority and target

This document records the current **source-acquisition result**, not authorization to flash. Owner-observed router: Huawei B315s-22, hardware `WL3B310FM01`, installed `21.333.01.00.366`, WebUI `17.100.09.00.03`; confirmed on wired live read-only WebUI through ATHENA at `192.168.8.1`. Physical router write count: **zero**.

## New exact-version source (confirmed archive, encrypted payload)

- Publisher: Datamax LTD, [original 2018 B315 tutorial](https://www.youtube.com/watch?v=PmGKLAl2hkc); description explicitly labels this link `21.333.01.00.366`
- [Google Drive source archive](https://drive.google.com/file/d/1ejs-Hf1YdILfbH4tkce0VYyn6cNWQx5R/view)
- Drive title: `B315s-22_update_Datamax3.rar`; RAR5; 36,961,181 bytes
- **RAR SHA-256:** `dcd9f8b1585ffc23f8434514aef35a1ae10668f320e68bad6fe1f50c85ada32f`
- Independently downloaded twice (Drive connector and direct public Drive via KRATOS), SHA matched
- RAR member listing: `B315s-22_update_21.333.01.00.366.bin`, 71,914,276 uncompressed bytes, listed CRC32 `d579fafb`
- **Member is password-encrypted.** The firmware's actual bytes, embedded version/board metadata, and cryptographic signature have **NOT** been examined. The listed CRC cannot be treated as an independently verified checksum until successful decryption.

Other Datamax archives do **not** establish exact-version eligibility: Datamax2 lists the older `21.316.01.01.366` and is likewise encrypted. The `21.333.01.03.1096` DiNiS donor is a different operator branch.

## Files and tests (KRATOS only)

Project root: `/home/kratos/projects/TECHGUYTOOL-Huawei/.workspace/research/b315s22-own-firmware-20261120/`

- Private project-contained archive: `evidence/sources/B315s-22_update_Datamax3_LOCKED_UNVERIFIED.rar`
- Archive verifier: `scripts/verify_b315_datamax_source.py`
- Source record: `evidence/B315_DATAMAX_EXACT_ARCHIVE_2026-11-21.json`
- Pre-flash result: `evidence/B315_DATAMAX_PREFLASH_GATE_2026-11-21.json`
- Test: `tests/test_b315_datamax_source.py` — 4/4 PASS; broader B315 suite 71/71 PASS
- Existing exact package extractor: `scripts/recover_exact_b315_verifier.py`, 5/5 prior tests; verifies firmware section layout/CRC, **not** full cryptographic signing
- Recovery checkpoint: `docs/RECOVERY_2026-11-20.md`

All candidate images currently fail the flash-readiness gate. Source archive acceptance is **not** firmware acceptance.

## USB recovery information (unqualified)

A B315-family archive on ATHENA includes `usblsafe_b315s.bin` (6,144,865 bytes, SHA-256 `a794ea4ff0dcb5c9a5fe335a80b41d6a3d4174fd0a3a2b684640e886b6ba8f60`). Its strings mention `HI6921_V711_CPE`. Static `balong-signcheck.py` did not find a recognizable Secuboot signature for the first loader image; this is **not** proof of safe boot, eFuse match, compatible flash/NV layout, or recovery on hardware `WL3B310FM01`. ATHENA presently sees no Huawei USB VID `12D1` service device. No loader was executed or physical flash attempted.

## Exact path to hardware qualification

1. Acquire the publisher-provided archive password through a legitimate channel and decrypt the RAR locally; do not store the password in repository, evidence, chat, process arguments, or logs.
2. Freeze SHA-256 of extracted BIN; parse and independently verify all 11 section headers, model/version/C-version fields and CRCs; inspect vendor-signature authenticity using a verified signing checker.
3. Establish actual installed MTN firmware's acceptance rules and authorization for the proposed package; do not rely on its filename, matching public-key hash, or a simulation result.
4. Qualify board-specific NV backups, full readback and a tested recovery/rollback path. Power and LAN conditions must be stable.
5. Only when these gates are proven should a physical firmware update be attempted. Preserve the existing, working MTN firmware until then.

**Current engineering disposition:** exact-version-labelled encrypted source **ACQUIRED**; decrypted package **NOT ACQUIRED**; recovery path and package acceptance **NOT PROVEN**; physical flash **NOT EXECUTED**.

Third-party archive bytes are excluded from GitHub. This documentation exists to prevent future sessions from repeating searches or misidentifying a donor image as an authorized MTN update.

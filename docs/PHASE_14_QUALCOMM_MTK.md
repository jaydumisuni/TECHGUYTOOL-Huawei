# Phase 14 — Qualcomm and MediaTek expansion

## Objective

Add deterministic, read-only Qualcomm and MediaTek service-lane proof without expanding device-modification authority.

Phase 14 is intentionally split by **model/operation pair**. A transport family is not considered globally proven because one replay succeeds.

## Recovered baseline

TTG Device X-Ray already provides a read-only Qualcomm EDL probe that recognizes the `05C6:9008` endpoint and explicitly records that no programmer has been loaded by the probe. Its reusable service-mode helper contract separates USB observation from protocol-specific read-only evidence.

The Huawei project already has proven MTK META transport evidence from earlier development, including MediaTek VID `0E8D` and Preloader PID `2000`. Phase 14 does not convert that earlier evidence into a new BROM hardware certification.

## Qualcomm reference pair

Profile:

`qcom.reference.9008-gpt-observation.v1`

Operation:

`read_only_gpt_inventory`

Software proof requires:

- exact `05C6:9008` EDL replay endpoint;
- Sahara observation state `HELLO_RESPONSE`;
- exact SHA-256 identity of the reference Firehose artifact metadata;
- target-family and storage binding metadata;
- read-only storage facts;
- a non-empty, structurally valid GPT inventory;
- exact replay evidence hash.

The artifact identity is a **fixture hash**, not certification of a real Firehose binary. Phase 14 does not use the artifact on a device.

## MediaTek reference pair

Profile:

`mtk.reference.brom-partition-observation.v1`

Operation:

`read_only_partition_inventory`

Software proof requires:

- MediaTek VID `0E8D`;
- a replay mode explicitly classified as BootROM or Preloader;
- the reference fixture discriminator for BootROM and the already-established `2000` Preloader PID;
- an explicit security-state classification from the bounded enum;
- exact SHA-256 identity of the reference Download Agent metadata;
- target-family and storage binding metadata;
- read-only storage facts;
- a non-empty, structurally valid partition inventory;
- exact replay evidence hash.

The BootROM PID is deliberately labelled a **fixture discriminator**. It is not promoted to physical hardware truth by this phase.

## Proof levels

Both model/operation pairs finish Phase 14 at:

`replay_supported`

Both remain:

`hardware_certification = HARDWARE_PENDING`

`production_enabled = false`

Device-changing operations remain outside the Phase 14 software proof. A later physical lab run may add stronger evidence without rewriting this historical receipt.

## Exit-gate interpretation

The Phase 14 exit gate is satisfied for the software layer because each declared model/operation pair has an explicit independent proof level, exact inputs, adversarial rejection tests and a hard truth boundary.

It does **not** satisfy the final physical proof matrix entries for Qualcomm 9008 or MediaTek BROM/Preloader. Those stay pending until real hardware evidence exists.


## 2026-11-25 CAZ-AL10 physical recovery evidence

Scoped physical route: CAZ-AL10 / MSM8953 / all-cn / 64 GB eMMC, reported B387 before repair. B077 factory package (Cannes-AL10 M001077) followed by B175 stock OS plus all/cn userdata. Board: 150 acknowledged program entries, 13 patches, 41 backup regions (529311232 bytes), six excluded unique partitions. Boot/recovery and both GPT copies verified within the recorded readback scope; full partition readback not performed. OEMINFO, modemst1 and persist changed after boot despite exclusion. Stock: eight partition operations acknowledged; factory boot chain and GPT retained. Owner observed Android launcher, MTN Zambia and 4G indication. No throughput/call proof or exact final build verification. Earlier mixed-version/no-network explanation is owner experience, not independently established original partition evidence.

Shared Sleeper knowledge record: huawei.caz-al10.msm8953.board-stock-recovery-20261125, canonical commit 3eaab1ed284e62e42779fe581291da230562d4ea. Physical receipt hashes in shared record. Local Huawei evidence: KRATOS project .workspace/research/cannes-board-20261125/physical-proof. Do not commit unique partition backups, firmware binaries or device identifiers.

ATHENA implementation: caz_al10_recovery.py, caz_al10_board_runtime.py, qualcomm_board.py. Actual ATHENA dirty worktree has three surgical integration edits saved as docs/CAZ_AL10_ATHENA_INTEGRATION.patch (zero-context patch against pre-existing ATHENA working files only; NOT against the old committed UI baseline). Preserve/reconcile the broader owner working tree; this branch includes the independently testable core and existing firmware_flash dependency, not a whole product release. Native Windows QDL v2.9.1 official release archive SHA256 5fdc8adffe46cc4a9f37dbbe91a8c91d0cc26befb3fe67f9609046a254a471d6; pinned exe/DLL digests in runtime module. QUD driver backend; skip-reset continuity and staged readback before reset are new software paths and require physical Windows qualification. No driver replacement. Native binary staged project-locally, not redistributed in Git.

UI usage: select exact CAZ-AL10, Board Firmware, extracted rawprogram_unsparse.xml, verify then confirm. After verified board reset and Android boot, enter Fastboot, select Repair and B175 dload/UPDATE.APP with regional sibling all/cn/update_data_all_cn.app. Confirm eight writes, then reboot/verify network. Both C: and D: have insufficient free space for largest stock image plus margin on current ATHENA; use a project-owned staging volume (TTG_HUAWEI_STAGING_DIR). Source firmware stays on KRATOS. Not general downgrade or arbitrary model certification; physical Windows end-to-end test and release packaging remain pending.

Recovered-evidence replay correction: before board programming, the primary GPT had 61 entries (B387 layout) while the CRC-valid backup GPT had 54 entries (same geometry as B077/B175). Both copies were valid but geometrically inconsistent. The exact two known layouts are accepted for this recovery profile, not arbitrary GPT corruption. Post-board both copies agree at 54. This supports the mixed-layout diagnosis but does not alone identify the original network failure cause.

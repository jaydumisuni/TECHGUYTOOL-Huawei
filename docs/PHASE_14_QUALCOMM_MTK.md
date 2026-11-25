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

## Package-driven generalization and Kirin detection (2026-11-25)

The shared qdl_runtime.py and fastboot_identity.py modules are not tied to a model. qualcomm_package.py discovers a Firehose programmer, storage family, selected rawprogram group, optional matching patch and referenced images from technician-supplied files. It provides a model-independent existing-layout programming adapter: live chipset report and primary/backup GPT reconciliation, target range validation, scoped backup, QDL acknowledgment checks and streaming raw/sparse readback. Existing-layout mode excludes GPT writes/patches and device-unique/user-data regions; it is not a general repartitioner. Reference CAZ-AL10 reconstruction remains selected by the known rawprogram digest. Other package formats (ambiguous loaders, unspecified storage family, non-ELF programmer formats, different GPT layout, multiple alternative XML groups) require explicit supported routing rather than guessing. Multi-group orchestration, new-model physical qualification and release remain open. No firmware copied to ATHENA or Git; only package metadata, hashes and engine code. Backup/readback capacity is relevant only when actually servicing a device. Windows EDL backend has not been physically qualified.

Kirin: remove the VOG/Kirin980-only restriction from generic device identity and Verlist, accept legacy concatenated build and lock-state forms, normalize hisi/kirin aliases and shared sparse ACKs. Retain exact historical VOG board conversion as a scoped special case. Archive and non-VOG Download.xml inspection are now recognized rather than rejected by model name. Kirin loader inventory records 56 existing owner-held KTL containers in 18 families with byte lengths and SHA-256; candidate resolver exposes actual available family or explicit ambiguity (620/620c, 65x A/B, 710/710a) without substituting a loader. KTL inventory does not qualify loader transmission or bootloader unlocking, and no native new Kirin service-entry implementation is claimed.

ATHENA working-tree UI and dispatch edits are represented in docs/PACKAGE_DRIVEN_ATHENA_INTEGRATION.patch, a zero-context incremental patch against the immediately preceding ATHENA source, not a replacement of the owner's existing dirty tree. Exact current hashes in docs/PACKAGE_DRIVEN_ATHENA_SOURCE_HASHES.json. Existing local files preserved via .workspace/evidence/package-driven-20261125/before. 49 focused tests including synthetic eMMC/UFS geometry, generic mocked QDL preflight/backup/program/readback, old Fastboot identities, prior board/stock regressions and six-page selector interaction passed on ATHENA. No phone I/O.

## Read Device / multi-group increment

ATHENA now invokes canonical TTG-Device-X-Ray scan --deep from Read Device, with exact serial or unique Huawei/Honor evidence binding. Full report, copy/save, and actual Device Information bindings are separated from concise observed-field log and animated progress. Original action evidence remains on disk. 51 focused tests passed and QML startup reported no errors. Actual physical deep-scan UI verification remains outstanding. Multi-numbered rawprogram groups are combined in numeric order, keeping alternative sparse/unsparse sets separate and associating patch files for inspection; generic same-layout repair does not execute GPT patches. Generic repartitioning execution and native Kirin loader transmission remain outstanding. Reviewed Kirin donor BSL1.1 has no additional production grant in the inspected LICENSE; separate commercial permission was not recovered. No donor implementation or loader binary copied, no phone I/O. Exact incremental UI/backend patch is against ATHENA working files, not the older repository baseline.

## Shared adapter connection increment

Owner confirmed Kirin reference licensing is settled. All 18 inventoried loader families are now exposed through the shared six-page chipset selector, including explicit silicon variants; runtime loader directory or contained owner archive is resolved against identical hashes. This is selection and package availability, not native service transmission. The existing donor USB sender has a separate boot-stage API and is not a generic headless transport; no new loader transmission was performed. X-Ray report now carries firmware fingerprint, profile match and challenger findings. Qualcomm vendor GPT templates are replayed offline with bounded disk-relative scalar and CRC patches before live layout comparison, rather than requiring a prepatched template. Generic existing-layout execution now recognizes valid capacity-adjusted templates, but actual generic reconstruction with differing GPT remains separate. 53 focused tests passed on ATHENA; physical tests outstanding. No firmware binaries or phone data transferred. Exact zero-context integration patch is against prior ATHENA working files.

## Generic vendor GPT reconstruction

The package-driven QDL worker now supports explicit vendor GPT reconstruction when paired templates are available. Preflight replays the bounded vendor patches, obtains both live GPT copies, validates target ranges and preserves protected identity regions, and binds the confirmation fingerprint to the original GPT hashes and layout delta. It backs up actual selected write ranges, validates programming/patch ACKs and both post-program GPTs plus firmware readback. No automatic reset. Existing data may become inaccessible following repartition. Generic same-layout repair remains for packages without paired templates. Synthetic end-to-end worker test passed; 54 focused tests and QML startup passed. Native Windows physical execution has not been demonstrated; no phone I/O was performed. The previous offline vendor GPT replay matched actual CAZ-AL10 post-board capture (61 to 54 entries), which establishes layout calculation evidence, not generalized physical execution qualification. Native Kirin transmission remains outstanding; owner confirmed license resolved. No firmware copied.

## Kirin vendor package integration and firmware cleanup

Kirin Download.xml now accepts GB2312/GBK/GB18030 encoding with entity declarations rejected. Actual VOG-AL00 vendor package inspection verified 99 file-backed entries, selected seven ordinary firmware repair images, and identified an absent optional DDR diagnostic image. Board Firmware mode inventories package-defined stages; Repair mode uses the existing authorized Fastboot worker with exact model/chipset and live partition-capacity checks. Factory service entry, CRC-specific commands, erase and protected boot-chain operations are separate and not executed by ordinary repair. Native temporary loader transmission is not connected; reference UnlockFastboot is not an ordinary vendor flashing API. 61 focused regression tests passed, including mocked Kirin 659/970/980/990 repair. No physical device writes or release packaging. Source integration patch is against ATHENA working source, not old committed baseline. Owner authorized deletion of KRATOS Cannes archives and extracted payloads; 14283460608 bytes reclaimed, device backups, receipts and vendor XML metadata retained. Original firmware must be reacquired for subsequent original-package replay or physical repair.

## Self-contained local runtime and UI connection

The owner requires local direct execution: no runtime Sleeper, AI, network or reference-checkout retrieval for established repair operations. The existing Builder staging script now installs 56 hash-verified KTL containers, nine verified QDL v2.9.1 runtime files and the pinned canonical TTG Device X-Ray source at 47df719f60d85e06ccecd867fdd4d65b26864378 into runtime/. Rebuild may reuse staged assets; no firmware archives are staged. The X-Ray worker is invoked locally by the application, with source-mode and frozen-mode entry points and file-based scan output. An actual bundled-source scan completed with zero candidates; frozen executable packaging is not yet proved. All 18 exact loader families resolve locally, including explicit hisi620 and hisi710 variants; this does not connect native service-entry transmission. Partition Manager now displays observed X-Ray partition rows and their details, with a Qt fixture proving two rendered rows. Board Repair now enters the ordinary package-driven repair page instead of the VOG archive-only action. Existing destructive and security-specific service functions are not made executable by these changes; generic partition backup/restore/write and native Kirin service entry remain incomplete. Restored missing pending dead-screen matrix entry to match existing release authority, without claiming hardware evidence. 85 selected regression tests passed and QML startup succeeded. No release executable built; source integration patch targets the prior ATHENA dirty working tree. No physical device writes.

## Local partition backup/write/restore

The existing asynchronous Backup/Restore action now accepts selected ordinary firmware partition jobs, bound to the scanned device serial, exact model/chipset and live partition size. Local Fastboot fetch captures a complete hashed image and backup.json receipt. Raw writes and same-device restores have a separate confirmed fingerprint, current-partition backup, acknowledgment and byte-level readback; no automatic reboot. Partition Manager file/destination selectors and Backup & Restore receipt selector are connected, with a shared confirmation dialog. This requires an authorized Fastboot session with fetch support; security-specific partitions and generic erase are not exposed by this ordinary repair worker. Simulated backup -> write -> restore passed, including changed device and corrupted receipt rejection. 87 selected tests and application QML startup passed. Native Kirin service-entry sender remains unconnected; existing reference unlock routine is not an ordinary authorized flashing API. No physical phone I/O and no new EXE. Incremental patch applies to prior ATHENA working source.

## EDL reconnect workflow

The original physical CAZ-AL10 GPT read log records QDL issuing a power reset; technician re-entry to EDL was required between operations. The shared interactive worker now prompts for EDL 9008 reconnection, polls for the same bound serial, and continues the pending stage without discarding completed stage evidence. A missing device during preflight also prompts for reconnection; a confirmed plan must still match its original fingerprint. Partial interrupted reads are retained and retried only after reconnection (up to three attempts); interrupted writes with uncertain completion are not automatically replayed. The dialog supports cancel and a five-minute reconnect deadline. This is connected to reference board recovery, generic same-layout repair, and generic vendor GPT reconstruction including GPT reads. 91 selected regression tests passed, including wrong-device rejection, reconnect, interrupted read retry, interrupted write no-replay, cancellation and timeout. QML startup passed. No new physical device was required or touched. Existing native Kirin entry gap is unchanged. Source update, not a newly built executable.

## Function audit and operation-driven Kirin repair waiting

The existing FULL_PLAN sections 11/12 and Phase 8 P10Revive golden theorem are the authority for routing and preserving service mode. No new architecture is introduced. In the ordinary Kirin firmware Repair worker, a missing responding Fastboot device can trigger a cancellable local wait with exact model/chipset and previously observed serial where available. The backend now emits the already-declared testpoint UI event. Automatic operation popup uses only approved local references; the checked-out local approved catalogue is empty. USB COM 1.0 observation dismisses the reference and changes the UI to waiting for the authorized repair interface. USB enumeration is not authorization, and native loader transfer is not connected. When a matching authorized Fastboot endpoint is observed, package preflight resumes and binds the serial to the new fingerprint; existing separate write confirmation remains required. No automatic reboot or device modification is initiated by this wait. Native temporary service-mode acquisition and general cross-operation mode lease enforcement remain incomplete. Account-lock and bootloader security bypass actions are not implemented. Earlier unpushed audit changes connect history to saved TXT logs and export, route service-center firmware/backup shortcuts, and perform a read-only Windows driver scan. No automatic driver installation without matching signed packages. 97 selected regression tests passed; Qt simulated popup/COM-dismissal/preflight signal transition passed. Prior broader audit had five UI-reference assertion failures and source freeze/Python environment inconsistencies; not a full release qualification. Both incremental patches target the actual dirty ATHENA source; no new installed EXE and no physical device writes.

## Model catalogue expansion

Expanded the existing shared device_profiles catalogue from six to 96 exact model records using published model-specific hardware specifications, with source URL on each new row. The local Kirin reference CPU menu and inventory establish 18 distinct loader families; they are not a full model catalogue. The inspected UnlockTool research directory did not yield a verified structured Huawei model mapping, and no executable or lock-bypass donor code was imported. The six-page shared selector remains the authority. Canonical aliases hisi710a/kirin710a and hisi620c/kirin620c are normalized without merging distinct silicon variants. All 96 rows exercised through the actual Qt backend: 23 resolve existing verified Kirin 980 image sets, 45 resolve verified local containers, 27 require an exact loader subvariant, and one is the existing Qualcomm CAZ-AL10 route. 25 selected regression tests passed, including actual six-page selector interaction and every catalogue row. Catalogue is not exhaustive, and loader availability is not native transport or per-operation execution proof. No physical device used, no firmware or donor runtime downloaded, no installed executable rebuilt.

## Independent hardware and loader-variant selection

The shared six-page selector now preserves chipset identity independently of the selected loader variant. Compatible candidate selection no longer replaces the model chipset, incompatible choices are rejected, and model changes invalidate the old variant and firmware plan. A newly selected unknown model does not inherit a previously selected model chipset; explicit chipset-first selection remains supported when no prior model is selected. The catalogue suggestion list no longer truncates at 48 entries. Verified all 27 ambiguous catalogue rows and all 54 candidate selections through the Qt backend, with local container integrity and identity separation; 95 selected regression tests passed. This is selection and inventory metadata only: it does not establish which candidate physically matches each of the 27 models and does not implement native loader execution or security bypass. No physical phone was required, no donor firmware downloaded, and no executable rebuilt. UI/backend integration patch targets prior ATHENA working source.

## Automatic target projection from detected device

After successful Read Device/X-Ray detection, the shared selector automatically populates a protocol-observed model and chipset, or uses the existing exact-model catalogue when the chipset is not reported. Explicit offline selections remain intact. Automatic target state follows the observed serial and clears on failed/disconnected scans; stale variants and plans clear when identity changes. A USB COM label alone is not sufficient identity evidence. Existing local resolver displays the loader matching the reported chipset when unambiguous; unresolved candidates remain explicit. No new service loader execution or native mode acquisition was introduced. This is scan-driven, not an independent continuous hotplug watcher. 97 selected regression tests passed, including simulated target changes and disconnect. No physical device or executable rebuild. Backend patch targets prior ATHENA working source.

## Windows USB hotplug observation and explicit variant projection

The existing five-second idle heartbeat schedules a read-only Windows PnP observation on the existing serial worker pool. Changes in the observed USB identity, PID or mode invoke the existing Read Device workflow; unchanged observations do not repeatedly launch scans. Observation failures do not clear the target, and active service jobs are not interrupted. Confirmed disconnect or multiple-device ambiguity invalidates automatic device state and pending plans. Explicit offline selections remain intact. An explicitly reported matching 65x loader-family identifier may populate the existing variant selector; distinct reported silicon IDs remain distinct. Generic chipset and USB COM labels are not variant evidence. This is read-only routing metadata, not loader execution authority. 100 selected regression tests passed, including worker signal delivery, hotplug state changes, explicit variant projection, busy-job preservation and disconnect. Actual ATHENA host inventory returned unknown_huawei with a fingerprint; Qt startup reported no errors. No physical hotplug sequence exercised, no executable rebuilt, no native loader transfer or security bypass implemented. Unresolved model-to-variant evidence remains unresolved. Integration patch targets actual prior ATHENA working source.

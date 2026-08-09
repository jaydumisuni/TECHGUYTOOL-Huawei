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

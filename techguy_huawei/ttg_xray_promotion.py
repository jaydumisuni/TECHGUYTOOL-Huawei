from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
PROMOTION_MANIFEST = ROOT / "manifests" / "phase13_ttg_xray_promotion.json"
KIRIN_MANIFEST = ROOT / "packs" / "kirin" / "manifest.json"
SCHEMA = "techguytool-huawei.phase13-ttg-xray-promotion.v1"
SOURCE_MERGE = "93a8bd705bd9e8d8bade40f0e15181644211812e"
TARGET_REPOSITORY = "jaydumisuni/TTG-Device-X-Ray"
TARGET_PR = 24
TARGET_HEAD = "359db4522f185c8e0430e4c2a4c5a06281f52e25"
TARGET_MERGE = "34feb55ab937fa865726cbb22c44b09b52084114"
TARGET_CI_RUN = 31339256277
KIRIN_MANIFEST_SHA256 = "3859e0e71495a4847c8698714494b5ce94264d12d6d8eaa663d4d56c45b8fc9f"
_REQUIRED_RULES = frozenset(
    {
        "vog.main_version_state.oeminfo",
        "vog.service_mode.preserve_until_verified",
        "vog.stock_fastboot.finalization_only",
        "vog.branding.separate_stage",
    }
)
_REQUIRED_PROOF = frozenset(
    {
        "profile_validation",
        "read_only_boundary",
        "public_privacy",
        "python_3_10",
        "python_3_11",
        "python_3_12",
        "python_3_13",
        "python_3_14",
        "windows_smoke",
        "package_gate",
        "standalone_qt_exe",
        "ci_gate",
    }
)
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


class PromotionEvidenceError(ValueError):
    pass


def load_promotion_manifest(path: Path = PROMOTION_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PromotionEvidenceError("promotion manifest must be a JSON object")
    validate_promotion_manifest(payload)
    return payload


def validate_promotion_manifest(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != SCHEMA:
        raise PromotionEvidenceError("Phase 13 promotion schema mismatch")

    source = _mapping(payload.get("source"), "source")
    if source.get("repository") != "jaydumisuni/TECHGUYTOOL-Huawei":
        raise PromotionEvidenceError("Phase 13 source repository mismatch")
    if source.get("phase12_merge") != SOURCE_MERGE:
        raise PromotionEvidenceError("Phase 13 source merge mismatch")
    if source.get("kirin_manifest_path") != "packs/kirin/manifest.json":
        raise PromotionEvidenceError("Phase 13 source manifest path mismatch")
    if source.get("kirin_manifest_sha256") != KIRIN_MANIFEST_SHA256:
        raise PromotionEvidenceError("Phase 13 source manifest hash mismatch")
    if source.get("maturity") != "replay_supported":
        raise PromotionEvidenceError("Phase 13 may not overstate Kirin maturity")
    if source.get("includes_execution") is not False:
        raise PromotionEvidenceError("Phase 13 source may not include execution")

    target = _mapping(payload.get("target"), "target")
    if target.get("repository") != TARGET_REPOSITORY:
        raise PromotionEvidenceError("Phase 13 target repository mismatch")
    if target.get("pull_request") != TARGET_PR:
        raise PromotionEvidenceError("Phase 13 target pull request mismatch")
    if target.get("reviewed_head") != TARGET_HEAD or not _SHA40.fullmatch(str(target.get("reviewed_head", ""))):
        raise PromotionEvidenceError("Phase 13 reviewed head mismatch")
    if target.get("merge_commit") != TARGET_MERGE or not _SHA40.fullmatch(str(target.get("merge_commit", ""))):
        raise PromotionEvidenceError("Phase 13 target merge mismatch")
    if target.get("ci_run_id") != TARGET_CI_RUN:
        raise PromotionEvidenceError("Phase 13 target CI run mismatch")
    if target.get("ci_conclusion") != "success":
        raise PromotionEvidenceError("Phase 13 target CI is not successful")
    promoted_paths = target.get("promoted_paths")
    if not isinstance(promoted_paths, list) or len(promoted_paths) < 5:
        raise PromotionEvidenceError("Phase 13 promoted path set is incomplete")
    if any(not isinstance(item, str) or not item for item in promoted_paths):
        raise PromotionEvidenceError("Phase 13 promoted path is invalid")
    if len(promoted_paths) != len(set(promoted_paths)):
        raise PromotionEvidenceError("Phase 13 promoted paths must be unique")

    proof = _mapping(payload.get("proof"), "proof")
    for key in _REQUIRED_PROOF:
        if proof.get(key) != "PASS":
            raise PromotionEvidenceError(f"Phase 13 proof {key} is not PASS")
    if proof.get("independently_explains_frozen_vog_case") is not True:
        raise PromotionEvidenceError("Phase 13 exit gate is not proven")

    rules = payload.get("promoted_rule_ids")
    if not isinstance(rules, list) or set(rules) != _REQUIRED_RULES:
        raise PromotionEvidenceError("Phase 13 promoted rule set mismatch")
    if len(rules) != len(set(rules)):
        raise PromotionEvidenceError("Phase 13 promoted rules must be unique")

    if payload.get("execution_authority") != "none":
        raise PromotionEvidenceError("Phase 13 may not grant execution authority")
    if payload.get("device_authority") != "none":
        raise PromotionEvidenceError("Phase 13 may not grant device authority")
    if payload.get("write_allowed") is not False:
        raise PromotionEvidenceError("Phase 13 may not grant write authority")
    if payload.get("physical_vog_certification") != "HARDWARE_PENDING":
        raise PromotionEvidenceError("Phase 13 must preserve the VOG hardware boundary")

    actual_hash = _sha256(KIRIN_MANIFEST)
    if actual_hash != KIRIN_MANIFEST_SHA256:
        raise PromotionEvidenceError(
            f"frozen Kirin manifest drift: expected {KIRIN_MANIFEST_SHA256}, got {actual_hash}"
        )
    if not _SHA64.fullmatch(actual_hash):
        raise PromotionEvidenceError("frozen Kirin manifest hash is malformed")

    kirin = json.loads(KIRIN_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(kirin, dict):
        raise PromotionEvidenceError("frozen Kirin manifest must be an object")
    if kirin.get("maturity") != "replay_supported" or kirin.get("includes_execution") is not False:
        raise PromotionEvidenceError("frozen Kirin manifest authority boundary changed")


def promotion_summary() -> dict[str, Any]:
    payload = load_promotion_manifest()
    return {
        "schema": "techguytool-huawei.phase13-proof.v1",
        "status": "PASS",
        "target_repository": payload["target"]["repository"],
        "target_merge": payload["target"]["merge_commit"],
        "target_ci_run_id": payload["target"]["ci_run_id"],
        "independently_explains_frozen_vog_case": True,
        "source_maturity": "replay_supported",
        "execution_authority": "none",
        "device_authority": "none",
        "write_allowed": False,
        "physical_vog_certification": "HARDWARE_PENDING",
    }


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PromotionEvidenceError(f"Phase 13 {name} block is missing")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

from __future__ import annotations

import copy

import pytest

from techguy_huawei.ttg_xray_promotion import (
    PromotionEvidenceError,
    load_promotion_manifest,
    promotion_summary,
    validate_promotion_manifest,
)


def test_phase13_promotion_evidence_passes() -> None:
    payload = load_promotion_manifest()
    assert payload["target"]["repository"] == "jaydumisuni/TTG-Device-X-Ray"
    assert payload["proof"]["independently_explains_frozen_vog_case"] is True
    assert payload["write_allowed"] is False
    assert payload["physical_vog_certification"] == "HARDWARE_PENDING"


def test_phase13_summary_keeps_authority_read_only() -> None:
    summary = promotion_summary()
    assert summary["status"] == "PASS"
    assert summary["independently_explains_frozen_vog_case"] is True
    assert summary["source_maturity"] == "replay_supported"
    assert summary["execution_authority"] == "none"
    assert summary["device_authority"] == "none"
    assert summary["write_allowed"] is False
    assert summary["physical_vog_certification"] == "HARDWARE_PENDING"


def test_phase13_rejects_execution_promotion() -> None:
    payload = copy.deepcopy(load_promotion_manifest())
    payload["source"]["includes_execution"] = True
    with pytest.raises(PromotionEvidenceError, match="may not include execution"):
        validate_promotion_manifest(payload)


def test_phase13_rejects_overstated_target_ci() -> None:
    payload = copy.deepcopy(load_promotion_manifest())
    payload["target"]["ci_conclusion"] = "failure"
    with pytest.raises(PromotionEvidenceError, match="not successful"):
        validate_promotion_manifest(payload)


def test_phase13_rejects_missing_vog_explanation_rule() -> None:
    payload = copy.deepcopy(load_promotion_manifest())
    payload["promoted_rule_ids"].pop()
    with pytest.raises(PromotionEvidenceError, match="rule set mismatch"):
        validate_promotion_manifest(payload)


def test_phase13_rejects_hardware_certification_claim() -> None:
    payload = copy.deepcopy(load_promotion_manifest())
    payload["physical_vog_certification"] = "CERTIFIED"
    with pytest.raises(PromotionEvidenceError, match="hardware boundary"):
        validate_promotion_manifest(payload)

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any, Mapping

import pytest

from techguy_huawei.contracts import validate_contract
from techguy_huawei.kirin_xray import (
    DONOR_REPOSITORY,
    PROVIDER_ID,
    PROVIDER_VERSION,
    KirinReplayError,
    load_replay,
    provider_manifest,
    publish_replay,
    render_replay,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    ROOT / "replay" / "kirin" / "p10_golden_workflow.json",
    ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json",
)
SOURCE_AUTHORITY = ROOT / "manifests" / "kirin_xray_sources.json"
PRIVATE_ARCHIVE = ROOT / "manifests" / "private_source_archive.json"
_WRITE_FLAG_CONTRACTS = {
    "physical_device_session",
    "device_evidence",
    "device_twin",
}


def test_provider_manifest_is_exactly_read_only() -> None:
    manifest = provider_manifest()
    assert manifest == {
        "component_id": "kirin.xray",
        "version": "0.2.0",
        "device_access": "read_only",
        "contract_authorities": ["diagnosis", "observation", "verification"],
        "capabilities": ["contract.publish", "evidence.read"],
    }
    assert manifest["contract_authorities"] == sorted(
        set(manifest["contract_authorities"])
    )
    assert manifest["capabilities"] == sorted(set(manifest["capabilities"]))
    assert not any(
        token in capability
        for capability in manifest["capabilities"]
        for token in ("erase", "flash", "reboot", "unlock", "write")
    )


def test_phase4_source_authority_matches_private_recovery_manifest() -> None:
    authority = json.loads(SOURCE_AUTHORITY.read_text(encoding="utf-8"))
    archive = json.loads(PRIVATE_ARCHIVE.read_text(encoding="utf-8"))
    archive_records = {
        (record["path"], record["sha256"], record["classification"])
        for record in archive["selected_records"]
    }
    authority_records = {
        (record["path"], record["sha256"], record["classification"])
        for record in authority["sources"]
    }
    assert authority["private_archive"]["drive_file_id"] == archive["authority"][
        "drive_file_id"
    ]
    assert authority["private_archive"]["sha256"] == archive["authority"]["sha256"]
    assert authority["private_archive"]["publish_raw_contents"] is False
    assert authority_records <= archive_records
    assert authority["donor"] == {
        "repository": DONOR_REPOSITORY,
        "commit": "d26152d38c197ba0bf98f41a66bed7ceb0575ce1",
        "version": PROVIDER_VERSION,
    }


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda path: path.stem)
def test_fixture_sources_are_frozen_and_authoritative(fixture: Path) -> None:
    authority = json.loads(SOURCE_AUTHORITY.read_text(encoding="utf-8"))
    allowed = {
        (record["path"], record["sha256"], record["classification"])
        for record in authority["sources"]
    }
    replay = load_replay(fixture)
    actual = {
        (record["path"], record["sha256"], record["classification"])
        for record in replay["sources"]
    }
    assert actual <= allowed
    assert replay["donor"] == authority["donor"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda path: path.stem)
def test_replay_is_byte_deterministic_and_phase2_valid(fixture: Path) -> None:
    first = render_replay(fixture)
    second = render_replay(fixture)
    replay = load_replay(fixture)

    assert first.canonical == second.canonical
    assert first.sha256 == second.sha256
    assert first.fixture_sha256 == second.fixture_sha256
    assert first.physical_session_id == second.physical_session_id
    assert first.continuity_token_sha256 == second.continuity_token_sha256
    assert first.to_dict()["write_authorized"] is False
    assert first.to_dict()["device_authority"] == "none"
    assert first.to_dict()["xray_authority"] == "read_only"

    for contract in first.contracts:
        assert contract["producer"] == PROVIDER_ID
        assert contract["authority"] in {
            "observation",
            "diagnosis",
            "verification",
        }
        _assert_contract_is_read_only(contract)
        result = validate_contract(
            contract,
            context={
                "now": replay["clock"]["validation_now"],
                "expected_contract_type": contract["contract_type"],
                "expected_physical_session_id": first.physical_session_id,
                "expected_authority": contract["authority"],
            },
        )
        assert result.ok, result.as_dict()


def test_p10_replay_encodes_the_golden_workflow_without_execution() -> None:
    replay = load_replay(FIXTURES[0])
    bundle = render_replay(replay)
    subjects = {
        contract["payload"].get("subject_id"): contract["payload"].get("verdict")
        for contract in bundle.contracts
        if contract["contract_type"] == "device_evidence"
    }
    assert subjects["p10-referenced-small-metadata-files"] == "missing"
    assert subjects["p10-complete-oeminfo-version-state"] == "coherent"
    assert subjects["p10-service-environment-retention"] == "coherent"
    assert bundle.safety["release_blocked"] is True
    assert bundle.safety["reason_codes"] == [
        "COMPLETE_OEMINFO_WORKFLOW_REQUIRED",
        "SERVICE_ENVIRONMENT_MUST_BE_RETAINED",
    ]


def test_p30_replay_explains_main_version_failure_and_mode_hazard() -> None:
    replay = load_replay(FIXTURES[1])
    bundle = render_replay(replay)
    subjects = {
        contract["payload"].get("subject_id"): contract["payload"].get("verdict")
        for contract in bundle.contracts
        if contract["contract_type"] == "device_evidence"
    }
    assert subjects["vog-l29-main-version"] == "missing"
    assert subjects["vog-l29-oeminfo-version-identity"] == "missing"
    assert subjects["vog-l29-vendor-country-state"] == "contradictory"
    assert subjects["vog-l29-vbmeta-hw-product-requirement"] == "coherent"
    assert subjects["vog-l29-cust-preload-package-metadata"] == "observed"
    assert subjects["vog-l29-service-mode-preservation"] == "coherent"
    assert subjects["vog-l29-premature-stock-fastboot-hazard"] == "observed"
    assert bundle.safety == {
        "explanation": replay["safety"]["explanation"],
        "reason_codes": [
            "MAIN_VERSION_MISSING_FROM_OEMINFO",
            "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED",
            "SERVICE_MODE_REQUIRED_UNTIL_VERIFIED",
        ],
        "release_blocked": True,
    }


def test_unknown_replay_members_fail_closed() -> None:
    replay = load_replay(FIXTURES[1])
    replay["unexpected"] = True
    with pytest.raises(KirinReplayError, match="UNKNOWN_REPLAY_MEMBER"):
        load_replay(replay)


def test_forbidden_endpoint_capability_fails_closed() -> None:
    replay = load_replay(FIXTURES[1])
    replay["endpoints"][0]["capability_ids"] = ["device.partition_write"]
    with pytest.raises(KirinReplayError, match="WRITE_CAPABILITY_FORBIDDEN"):
        load_replay(replay)


def test_invalid_source_reference_fails_closed() -> None:
    replay = load_replay(FIXTURES[1])
    replay["evidence"][0]["source_indexes"] = [99]
    with pytest.raises(KirinReplayError, match="INVALID_SOURCE_REFERENCE"):
        load_replay(replay)


def test_non_deterministic_or_stale_replay_clock_fails_closed() -> None:
    replay = load_replay(FIXTURES[1])
    replay["clock"]["basis"] = "claimed_capture_time"
    with pytest.raises(KirinReplayError, match="INVALID_REPLAY_CLOCK"):
        load_replay(replay)

    replay = load_replay(FIXTURES[1])
    replay["clock"]["validation_now"] = replay["clock"]["fresh_until"]
    with pytest.raises(KirinReplayError, match="INVALID_REPLAY_CLOCK"):
        load_replay(replay)


def test_gateway_publication_binds_runtime_session_and_preserves_authority() -> None:
    gateway = FakeGateway()
    result = publish_replay(gateway, FIXTURES[1])

    assert result["write_authorized"] is False
    assert result["device_authority"] == "none"
    assert result["xray_authority"] == "read_only"
    assert result["physical_session_id"] == gateway.session_id
    assert gateway.registered_manifest == provider_manifest()
    assert len(gateway.endpoint_records) == 2
    assert len(result["receipts"]) == len(render_replay(FIXTURES[1]).contracts)
    assert all(
        contract["physical_session_id"] == gateway.session_id
        for contract in gateway.contracts
    )
    assert all(contract["producer"] == PROVIDER_ID for contract in gateway.contracts)
    for contract in gateway.contracts:
        _assert_contract_is_read_only(contract)


def _assert_contract_is_read_only(contract: Mapping[str, Any]) -> None:
    contract_type = contract["contract_type"]
    payload = contract["payload"]
    if contract_type in _WRITE_FLAG_CONTRACTS:
        assert payload["write_allowed"] is False
    else:
        assert contract_type == "endpoint_observation"
        assert "write_allowed" not in payload
        assert contract["authority"] == "observation"


class FakeGateway:
    def __init__(self) -> None:
        self.session_id = "44444444-4444-4444-8444-444444444444"
        self.registered_manifest: dict[str, Any] | None = None
        self.endpoint_records: list[dict[str, Any]] = []
        self.contracts: list[dict[str, Any]] = []

    def register_provider(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        self.registered_manifest = dict(manifest)
        return dict(manifest)

    def open_physical_session(self, fingerprint_sha256: str) -> dict[str, Any]:
        assert len(fingerprint_sha256) == 64
        return {
            "session_id": self.session_id,
            "fingerprint_sha256": fingerprint_sha256,
        }

    def record_endpoint(
        self,
        session_id: str,
        endpoint_key: str,
        mode: str,
        transport: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert session_id == self.session_id
        record = {
            "observation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, endpoint_key)),
            "session_id": session_id,
            "endpoint_key": endpoint_key,
            "mode": mode,
            "transport": transport,
            "payload": dict(payload or {}),
        }
        self.endpoint_records.append(record)
        return record

    def publish_contract(
        self,
        component_id: str,
        contract: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert component_id == PROVIDER_ID
        assert context is not None
        material = copy.deepcopy(dict(contract))
        result = validate_contract(material, context=context)
        assert result.ok, result.as_dict()
        self.contracts.append(material)
        return {
            "contract_type": material["contract_type"],
            "contract_sha256": result.sha256,
        }

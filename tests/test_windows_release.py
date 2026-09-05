from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

import techguy_huawei.windows_release as windows_release
from techguy_huawei.windows_release import (
    WindowsReleaseError,
    find_prohibited_external_data_sources,
    load_physical_matrix,
    load_release_policy,
    load_release_receipt,
    receipt_matches_active_source,
    source_inventory_sha256,
    validate_physical_matrix,
    validate_receipt_matrix_alignment,
    validate_release_policy,
    validate_release_receipt,
    validate_windows_release_sources,
)


def _synthetic_frozen_receipt(*, inventory_sha256: str = "a" * 64, tested_revision: str = "1" * 40) -> dict[str, object]:
    receipt = copy.deepcopy(load_release_receipt())
    receipt.update(
        {
            "status": "FROZEN",
            "windows_ci": "PASS",
            "ci_test_signing": "PASS",
            "tested_revision": tested_revision,
            "source_inventory_sha256": inventory_sha256,
            "executable_sha256": "3" * 64,
            "windows_run_id": 123,
            "software_proof_run_id": 456,
            "artifact_id": 789,
            "artifact_name": "TECHGUYTOOL-Huawei-phase15-windows-candidate",
        }
    )
    validate_release_receipt(receipt)
    return receipt


def test_phase15_readiness_matches_receipt_authority_state() -> None:
    receipt = load_release_receipt()
    result = validate_windows_release_sources()
    assert result["release_filename"] == "TECHGUYTOOL_Huawei.exe"
    assert result["packaging"] == "ONEFILE_READY"
    if receipt["status"] == "FROZEN" and receipt_matches_active_source(receipt):
        assert result["status"] == "CI_PROVEN"
        assert result["signing_path"] == "CI_AUTHENTICODE_PROVEN"
        assert result["checksums"] == "SHA256_PROVEN"
        assert result["clean_windows_ci"] == "PASS"
    else:
        assert result["status"] == "SOURCES_ONLY_PENDING_CI"
        assert result["signing_path"] == "AUTHENTICODE_REQUIRED_CI_TESTABLE"
        assert result["checksums"] == "SHA256_REQUIRED"
        assert result["clean_windows_ci"] == "PENDING"
    assert result["physical_matrix"] == "INCOMPLETE"
    assert result["production_release_status"] == "EXTERNAL_CERTIFICATION_PENDING"
    assert result["production_enabled"] is False


def test_policy_rejects_production_without_external_certification() -> None:
    policy = copy.deepcopy(load_release_policy())
    policy["production_enabled"] = True
    with pytest.raises(WindowsReleaseError, match="Production enablement forbidden"):
        validate_release_policy(policy)


def test_policy_rejects_committed_certificate_boundary_change() -> None:
    policy = copy.deepcopy(load_release_policy())
    policy["signing"]["production_certificate_may_not_be_committed"] = False
    with pytest.raises(WindowsReleaseError, match="certificate storage boundary"):
        validate_release_policy(policy)


def test_policy_rejects_missing_authenticode_requirement() -> None:
    policy = copy.deepcopy(load_release_policy())
    policy["signing"]["authenticode_required_for_production"] = False
    with pytest.raises(WindowsReleaseError, match="Authenticode requirement"):
        validate_release_policy(policy)


def test_frozen_receipt_requires_bound_ci_evidence() -> None:
    receipt = copy.deepcopy(load_release_receipt())
    receipt.update({"status": "FROZEN", "windows_ci": "PASS", "ci_test_signing": "PASS"})
    for field in ("tested_revision", "source_inventory_sha256", "executable_sha256"):
        receipt.pop(field, None)
    with pytest.raises(WindowsReleaseError, match="tested_revision invalid"):
        validate_release_receipt(receipt)


def test_evidence_bound_frozen_receipt_is_valid() -> None:
    _synthetic_frozen_receipt(inventory_sha256="2" * 64)


def test_stale_but_well_formed_frozen_receipt_is_not_active_authority() -> None:
    receipt = _synthetic_frozen_receipt(
        inventory_sha256=source_inventory_sha256(),
        tested_revision="0" * 40,
    )
    assert receipt_matches_active_source(receipt) is False


def test_non_ancestor_frozen_receipt_is_not_active_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = _synthetic_frozen_receipt()
    monkeypatch.setattr(windows_release, "source_inventory_sha256", lambda: "a" * 64)
    monkeypatch.setattr(
        windows_release,
        "_load_json",
        lambda _path: {"excluded_from_recursive_hashing": ["manifests/phase15_windows_release.receipt.json"]},
    )
    monkeypatch.setattr(windows_release.shutil, "which", lambda _name: "/usr/bin/git")

    def fake_run(args, **_kwargs):
        assert args[1:3] == ["merge-base", "--is-ancestor"]
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(windows_release.subprocess, "run", fake_run)
    assert receipt_matches_active_source(receipt) is False


def test_dirty_tracked_source_rejects_frozen_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = _synthetic_frozen_receipt()
    monkeypatch.setattr(windows_release, "source_inventory_sha256", lambda: "a" * 64)
    monkeypatch.setattr(
        windows_release,
        "_load_json",
        lambda _path: {"excluded_from_recursive_hashing": ["manifests/phase15_windows_release.receipt.json"]},
    )
    monkeypatch.setattr(windows_release.shutil, "which", lambda _name: "/usr/bin/git")
    calls = 0

    def fake_run(args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            assert args[1:3] == ["merge-base", "--is-ancestor"]
            return SimpleNamespace(returncode=0, stdout="")
        assert args[1:3] == ["diff", "--quiet"]
        return SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(windows_release.subprocess, "run", fake_run)
    assert receipt_matches_active_source(receipt) is False
    assert calls == 2


def test_receipt_physical_matrix_claim_must_match_manifest() -> None:
    receipt = copy.deepcopy(load_release_receipt())
    matrix = copy.deepcopy(load_physical_matrix())
    receipt["physical_proof_matrix"] = "COMPLETE"
    with pytest.raises(WindowsReleaseError, match="does not match the physical proof matrix"):
        validate_receipt_matrix_alignment(receipt, matrix)


def test_physical_matrix_rejects_fake_completion_without_passes() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["overall_status"] = "COMPLETE"
    with pytest.raises(WindowsReleaseError, match="overall status does not match"):
        validate_physical_matrix(matrix)


def test_physical_matrix_rejects_unproven_physical_pass() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"][0]["status"] = "PHYSICAL_PASS"
    matrix["entries"][0].pop("evidence", None)
    with pytest.raises(WindowsReleaseError, match="physical evidence"):
        validate_physical_matrix(matrix)


def test_physical_matrix_accepts_complete_evidence_backed_matrix() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["overall_status"] = "COMPLETE"
    for index, entry in enumerate(matrix["entries"], start=1):
        entry["status"] = "PHYSICAL_PASS"
        entry["evidence"] = {
            "evidence_id": f"physical-proof-{index}",
            "evidence_sha256": f"{index:064x}"[-64:],
            "evidence_refs": [f"artifact://physical-proof/{index}"],
            "subject_identity_hash": f"{index + 100:064x}"[-64:],
            "verified_at": "2026-08-10T20:00:00Z",
            "verifier": "THETECHGUY physical certification",
        }
    validate_physical_matrix(matrix)


def test_physical_matrix_rejects_bad_evidence_hash() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"][0]["status"] = "PHYSICAL_PASS"
    matrix["entries"][0]["evidence"] = {
        "evidence_id": "bad-hash",
        "evidence_sha256": "not-a-hash",
        "evidence_refs": ["artifact://physical-proof/bad"],
        "subject_identity_hash": "4" * 64,
        "verified_at": "2026-08-10T20:00:00Z",
        "verifier": "THETECHGUY physical certification",
    }
    with pytest.raises(WindowsReleaseError, match="evidence_sha256 invalid"):
        validate_physical_matrix(matrix)


def test_physical_matrix_rejects_missing_required_entry() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"].pop()
    with pytest.raises(WindowsReleaseError, match="does not match the frozen plan"):
        validate_physical_matrix(matrix)


@pytest.mark.parametrize(
    "source",
    [
        "firmware",
        "SUPER_images",
        "customer-backups",
        "resources/testpoints",
        "operation_journals",
        "registration-license-data",
        "downloaded_artifacts",
    ],
)
def test_deploy_spec_rejects_every_external_data_class(source: str) -> None:
    spec = f"extra_args = --include-data-dir={source}=bundled"
    assert find_prohibited_external_data_sources(spec) == [source]


def test_deploy_spec_rejects_quoted_spaced_source() -> None:
    spec = 'extra_args = --include-data-dir="C:/Customer Backups/x"=data'
    assert find_prohibited_external_data_sources(spec) == ["C:/Customer Backups/x"]


def test_deploy_spec_allows_reviewed_static_sources() -> None:
    spec = "extra_args = --include-data-dir=data=data --include-data-dir=assets=assets --include-data-dir=runtime=runtime"
    assert find_prohibited_external_data_sources(spec) == []


def test_physical_matrix_requires_dead_screen_normal_android_charge_only_discovery() -> None:
    matrix = load_physical_matrix()
    rows = {row["id"]: row for row in matrix["entries"]}
    assert rows["dead_screen_normal_android_charge_only_discovery"]["status"] in {
        "HARDWARE_PENDING",
        "PHYSICAL_PASS",
    }

from __future__ import annotations

import copy

import pytest

from techguy_huawei.windows_release import (
    WindowsReleaseError,
    find_prohibited_external_data_sources,
    load_physical_matrix,
    load_release_policy,
    load_release_receipt,
    validate_physical_matrix,
    validate_release_policy,
    validate_release_receipt,
    validate_windows_release_sources,
)


def test_phase15_sources_report_pending_until_ci_receipt_is_frozen() -> None:
    result = validate_windows_release_sources()
    assert result["status"] == "SOURCES_ONLY_PENDING_CI"
    assert result["release_filename"] == "TECHGUYTOOL_Huawei.exe"
    assert result["packaging"] == "ONEFILE_READY"
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
    with pytest.raises(WindowsReleaseError, match="tested_revision invalid"):
        validate_release_receipt(receipt)


def test_evidence_bound_frozen_receipt_is_valid() -> None:
    receipt = copy.deepcopy(load_release_receipt())
    receipt.update(
        {
            "status": "FROZEN",
            "windows_ci": "PASS",
            "ci_test_signing": "PASS",
            "tested_revision": "1" * 40,
            "source_inventory_sha256": "2" * 64,
            "executable_sha256": "3" * 64,
            "windows_run_id": 123,
            "software_proof_run_id": 456,
            "artifact_id": 789,
            "artifact_name": "TECHGUYTOOL-Huawei-phase15-windows-candidate",
        }
    )
    validate_release_receipt(receipt)


def test_physical_matrix_rejects_fake_completion_without_passes() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["overall_status"] = "COMPLETE"
    with pytest.raises(WindowsReleaseError, match="overall status does not match"):
        validate_physical_matrix(matrix)


def test_physical_matrix_rejects_unproven_physical_pass() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"][0]["status"] = "PHYSICAL_PASS"
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


def test_deploy_spec_allows_reviewed_static_sources() -> None:
    spec = "extra_args = --include-data-dir=data=data --include-data-dir=assets=assets --include-data-dir=runtime=runtime"
    assert find_prohibited_external_data_sources(spec) == []

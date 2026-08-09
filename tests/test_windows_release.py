from __future__ import annotations

import copy

import pytest

from techguy_huawei.windows_release import (
    WindowsReleaseError,
    load_physical_matrix,
    load_release_policy,
    validate_physical_matrix,
    validate_release_policy,
    validate_windows_release_sources,
)


def test_phase15_software_release_sources_are_ready() -> None:
    result = validate_windows_release_sources()
    assert result["status"] == "PASS"
    assert result["release_filename"] == "TECHGUYTOOL_Huawei.exe"
    assert result["packaging"] == "ONEFILE_READY"
    assert result["signing_path"] == "AUTHENTICODE_REQUIRED_CI_TESTABLE"
    assert result["checksums"] == "SHA256_REQUIRED"
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


def test_physical_matrix_rejects_fake_completion() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["overall_status"] = "COMPLETE"
    with pytest.raises(WindowsReleaseError, match="may not be marked complete"):
        validate_physical_matrix(matrix)


def test_physical_matrix_rejects_unproven_physical_pass() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"][0]["status"] = "PHYSICAL_PASS"
    with pytest.raises(WindowsReleaseError, match="unsupported or overstated"):
        validate_physical_matrix(matrix)


def test_physical_matrix_rejects_missing_required_entry() -> None:
    matrix = copy.deepcopy(load_physical_matrix())
    matrix["entries"].pop()
    with pytest.raises(WindowsReleaseError, match="does not match the frozen plan"):
        validate_physical_matrix(matrix)

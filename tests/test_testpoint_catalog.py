from __future__ import annotations

from pathlib import Path

import pytest

from techguy_huawei.testpoint_catalog import (
    TestpointCatalogError,
    exact_testpoint_record,
    expected_service_interface,
    load_testpoint_catalog,
    validate_testpoint_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


def test_repository_testpoint_catalog_starts_empty_and_owner_only() -> None:
    catalog = load_testpoint_catalog(ROOT)
    assert catalog["owner_approved_only"] is True
    assert catalog["web_lookup_allowed"] is False
    assert catalog["similar_model_substitution_allowed"] is False
    assert catalog["records"] == []
    assert exact_testpoint_record(catalog, "VOG-L29") is None


def test_expected_service_interface_is_platform_specific() -> None:
    assert expected_service_interface("Kirin 980") == "HUAWEI USB COM 1.0"
    assert expected_service_interface("Qualcomm Huawei") == "Qualcomm HS-USB QDLoader 9008"
    assert expected_service_interface("MediaTek Huawei") == "MediaTek USB Port / BootROM / Preloader"


def test_catalog_rejects_similar_model_substitution_authority() -> None:
    payload = {
        "schema": "techguytool-huawei.testpoint-catalog.v1",
        "owner_approved_only": True,
        "web_lookup_allowed": False,
        "similar_model_substitution_allowed": True,
        "records": [],
    }
    with pytest.raises(TestpointCatalogError, match="similar-model substitution"):
        validate_testpoint_catalog(payload)


def test_catalog_rejects_unapproved_reference() -> None:
    payload = {
        "schema": "techguytool-huawei.testpoint-catalog.v1",
        "owner_approved_only": True,
        "web_lookup_allowed": False,
        "similar_model_substitution_allowed": False,
        "records": [
            {
                "model": "VOG-L29",
                "owner_approved": False,
                "reference": "resources/testpoints/VOG-L29.png",
                "sha256": "a" * 64,
                "expected_interface": "HUAWEI USB COM 1.0",
            }
        ],
    }
    with pytest.raises(TestpointCatalogError, match="not owner-approved"):
        validate_testpoint_catalog(payload)

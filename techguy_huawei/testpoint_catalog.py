from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "techguytool-huawei.testpoint-catalog.v1"


class TestpointCatalogError(ValueError):
    __test__ = False


def load_device_profiles(app_root: Path) -> dict[str, Any]:
    payload = json.loads((app_root / "data" / "device_profiles.json").read_text(encoding="utf-8"))
    models = payload.get("models")
    if not isinstance(models, list):
        raise TestpointCatalogError("device profile models must be a list")
    return payload


def load_testpoint_catalog(app_root: Path) -> dict[str, Any]:
    payload = json.loads((app_root / "data" / "testpoint_catalog.json").read_text(encoding="utf-8"))
    validate_testpoint_catalog(payload)
    return payload


def validate_testpoint_catalog(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != SCHEMA:
        raise TestpointCatalogError("testpoint catalogue schema mismatch")
    if payload.get("owner_approved_only") is not True:
        raise TestpointCatalogError("testpoint catalogue must be owner-approved only")
    if payload.get("web_lookup_allowed") is not False:
        raise TestpointCatalogError("automatic web lookup is forbidden")
    if payload.get("similar_model_substitution_allowed") is not False:
        raise TestpointCatalogError("similar-model substitution is forbidden")
    records = payload.get("records")
    if not isinstance(records, list):
        raise TestpointCatalogError("testpoint catalogue records must be a list")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise TestpointCatalogError("testpoint catalogue record must be an object")
        model = str(record.get("model", "")).strip()
        if not model or model in seen:
            raise TestpointCatalogError("testpoint catalogue requires unique exact model ids")
        seen.add(model)
        if record.get("owner_approved") is not True:
            raise TestpointCatalogError(f"testpoint record {model} is not owner-approved")
        reference = str(record.get("reference", "")).strip()
        sha256 = str(record.get("sha256", "")).strip().lower()
        expected_interface = str(record.get("expected_interface", "")).strip()
        if not reference or len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise TestpointCatalogError(f"testpoint record {model} has invalid reference authority")
        if not expected_interface:
            raise TestpointCatalogError(f"testpoint record {model} has no expected interface")


def expected_service_interface(platform: str) -> str:
    normalized = platform.strip().lower()
    if normalized.startswith("kirin"):
        return "HUAWEI USB COM 1.0"
    if "qualcomm" in normalized:
        return "Qualcomm HS-USB QDLoader 9008"
    if "mediatek" in normalized or normalized.startswith("mtk"):
        return "MediaTek USB Port / BootROM / Preloader"
    return "Unsupported / unknown service interface"


def exact_testpoint_record(catalog: Mapping[str, Any], model: str) -> dict[str, Any] | None:
    for record in catalog.get("records", []):
        if isinstance(record, Mapping) and str(record.get("model", "")) == model:
            return dict(record)
    return None

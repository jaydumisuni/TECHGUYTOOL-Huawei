from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import canonical_sha256, validate_contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KIRIN_MANIFEST = ROOT / "packs" / "kirin" / "manifest.json"
ALLOWED_COMPONENT_SCHEMAS = frozenset(
    {
        "techguytool-huawei.kirin-provider-pack.v1",
        "techguytool-huawei.kirin-knowledge-pack.v1",
        "techguytool-huawei.kirin-error-pack.v1",
        "techguytool-huawei.kirin-replay-pack.v1",
        "techguytool-huawei.kirin-verification-pack.v1",
    }
)
FORBIDDEN_EXECUTION_TOKENS = (
    "loader_transfer",
    "partition_write",
    "firmware_write",
    "reboot_authority",
)


class CapabilityPackError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class LoadedCapabilitySet:
    manifest: Mapping[str, Any]
    components: Mapping[str, Mapping[str, Any]]

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(self.manifest["capability_ids"])

    @property
    def manifest_sha256(self) -> str:
        return canonical_sha256(self.manifest)

    def provider_ids(self) -> tuple[str, ...]:
        provider = self.components["kirin-xray-provider-pack"]
        return tuple(item["id"] for item in provider["providers"])


def load_kirin_capability_set(path: str | Path = DEFAULT_KIRIN_MANIFEST) -> LoadedCapabilitySet:
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    components: dict[str, Mapping[str, Any]] = {}
    for item in manifest["components"]:
        component_path = ROOT / item["path"]
        if not component_path.is_file():
            raise CapabilityPackError("CAPABILITY_COMPONENT_MISSING", item["path"])
        actual_hash = _sha256(component_path)
        if actual_hash != item["sha256"]:
            raise CapabilityPackError("CAPABILITY_COMPONENT_HASH_MISMATCH", item["id"])
        component = json.loads(component_path.read_text(encoding="utf-8"))
        validate_component(item["id"], component)
        components[item["id"]] = component
    if set(components) != {item["id"] for item in manifest["components"]}:
        raise CapabilityPackError("CAPABILITY_COMPONENT_SET_MISMATCH", repr(sorted(components)))
    providers = {item["id"] for item in components["kirin-xray-provider-pack"]["providers"]}
    if providers != set(manifest["capability_ids"]):
        raise CapabilityPackError("CAPABILITY_PROVIDER_SET_MISMATCH", repr(sorted(providers)))
    validate_replay_references(components["kirin-xray-replay-pack"])
    return LoadedCapabilitySet(manifest=manifest, components=components)


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema", "pack_id", "pack_version", "specialist", "maturity",
        "includes_execution", "components", "capability_ids", "forbidden_contents", "truth_boundary",
    }
    if set(manifest) != required:
        raise CapabilityPackError("CAPABILITY_MANIFEST_SHAPE_INVALID", repr(sorted(set(manifest))))
    if manifest["schema"] != "techguytool-huawei.kirin-capability-pack-set.v1":
        raise CapabilityPackError("CAPABILITY_MANIFEST_SCHEMA_INVALID", str(manifest["schema"]))
    if manifest["pack_id"] != "kirin-xray-capability-set" or manifest["specialist"] != "kirin_xray":
        raise CapabilityPackError("CAPABILITY_MANIFEST_IDENTITY_INVALID", str(manifest["pack_id"]))
    if manifest["pack_version"] != "1.0.0" or manifest["maturity"] != "replay_supported":
        raise CapabilityPackError("CAPABILITY_MANIFEST_VERSION_INVALID", repr((manifest["pack_version"], manifest["maturity"])))
    if manifest["includes_execution"] is not False:
        raise CapabilityPackError("EXECUTION_CAPABILITY_FORBIDDEN", "manifest includes execution")
    components = manifest["components"]
    if not isinstance(components, list) or len(components) != 5:
        raise CapabilityPackError("CAPABILITY_COMPONENT_SET_INVALID", repr(components))
    ids = [item.get("id") for item in components if isinstance(item, Mapping)]
    paths = [item.get("path") for item in components if isinstance(item, Mapping)]
    if len(ids) != 5 or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise CapabilityPackError("CAPABILITY_COMPONENT_IDS_NONCANONICAL", repr(ids))
    if len(paths) != len(set(paths)):
        raise CapabilityPackError("CAPABILITY_COMPONENT_PATH_DUPLICATE", repr(paths))
    for item in components:
        if not isinstance(item, Mapping) or set(item) != {"id", "path", "sha256"}:
            raise CapabilityPackError("CAPABILITY_COMPONENT_ENTRY_INVALID", repr(item))
        if not isinstance(item["path"], str) or not item["path"].startswith("packs/kirin/") or ".." in item["path"]:
            raise CapabilityPackError("CAPABILITY_COMPONENT_PATH_INVALID", str(item["path"]))
        _validate_sha(item["sha256"], item["id"])
    capability_ids = manifest["capability_ids"]
    if not isinstance(capability_ids, list) or capability_ids != sorted(set(capability_ids)):
        raise CapabilityPackError("CAPABILITY_IDS_NONCANONICAL", repr(capability_ids))
    if manifest["forbidden_contents"] != sorted(set(manifest["forbidden_contents"])):
        raise CapabilityPackError("CAPABILITY_FORBIDDEN_SET_NONCANONICAL", repr(manifest["forbidden_contents"]))


def validate_component(expected_id: str, component: Mapping[str, Any]) -> None:
    schema = component.get("schema")
    if schema not in ALLOWED_COMPONENT_SCHEMAS:
        raise CapabilityPackError("CAPABILITY_COMPONENT_SCHEMA_INVALID", str(schema))
    if component.get("pack_id") != expected_id:
        raise CapabilityPackError("CAPABILITY_COMPONENT_ID_MISMATCH", expected_id)
    if component.get("version") != "1.0.0":
        raise CapabilityPackError("CAPABILITY_COMPONENT_VERSION_MISMATCH", expected_id)
    if component.get("includes_execution") is not False:
        raise CapabilityPackError("EXECUTION_CAPABILITY_FORBIDDEN", expected_id)
    serialized = json.dumps(component, sort_keys=True).lower()
    for token in FORBIDDEN_EXECUTION_TOKENS:
        if token in serialized:
            raise CapabilityPackError("EXECUTION_TOKEN_FORBIDDEN", f"{expected_id}:{token}")
    if expected_id == "kirin-xray-provider-pack":
        for provider in component.get("providers", []):
            if provider.get("write_allowed") is not False or provider.get("authority") not in {"diagnosis", "observation"}:
                raise CapabilityPackError("PROVIDER_AUTHORITY_INVALID", str(provider))


def validate_replay_references(component: Mapping[str, Any]) -> None:
    fixtures = component.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise CapabilityPackError("REPLAY_FIXTURE_SET_INVALID", repr(fixtures))
    for fixture in fixtures:
        path = ROOT / str(fixture.get("path", ""))
        if not path.is_file():
            raise CapabilityPackError("REPLAY_FIXTURE_MISSING", str(fixture.get("path")))
        replay = json.loads(path.read_text(encoding="utf-8"))
        if replay.get("scenario_id") != fixture.get("scenario_id"):
            raise CapabilityPackError("REPLAY_SCENARIO_MISMATCH", str(fixture.get("path")))


def build_capability_contract(
    loaded: LoadedCapabilitySet,
    *,
    created_at: str,
) -> dict[str, Any]:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"urn:thetechguy:capability-pack:{loaded.manifest_sha256}")
    contract = {
        "schema_version": 1,
        "contract_type": "capability_pack",
        "contract_id": str(uuid.uuid5(namespace, "contract")),
        "producer": "kirin.xray.packager",
        "created_at": created_at,
        "physical_session_id": None,
        "evidence_hashes": sorted(item["sha256"] for item in loaded.manifest["components"]),
        "confidence_bps": None,
        "expires_at": None,
        "authority": "learning",
        "single_use": False,
        "consumed_at": None,
        "payload": {
            "pack_id": loaded.manifest["pack_id"],
            "pack_version": loaded.manifest["pack_version"],
            "specialist": loaded.manifest["specialist"],
            "manifest_sha256": loaded.manifest_sha256,
            "capability_ids": list(loaded.capability_ids),
            "includes_execution": False,
            "maturity": loaded.manifest["maturity"],
        },
    }
    result = validate_contract(
        contract,
        context={"now": created_at, "expected_contract_type": "capability_pack", "expected_authority": "learning"},
    )
    if not result.ok:
        raise CapabilityPackError("CAPABILITY_CONTRACT_INVALID", json.dumps(result.as_dict(), sort_keys=True))
    return contract


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _validate_sha(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value:
        raise CapabilityPackError("CAPABILITY_HASH_INVALID", label)
    try:
        int(value, 16)
    except ValueError as exc:
        raise CapabilityPackError("CAPABILITY_HASH_INVALID", label) from exc

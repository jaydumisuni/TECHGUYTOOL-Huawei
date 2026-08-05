from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .contracts import canonical_json, canonical_sha256, parse_timestamp, validate_contract

PROVIDER_ID = "kirin.xray"
PROVIDER_VERSION = "0.2.0"
REPLAY_SCHEMA = "techguytool-huawei.kirin-xray-replay.v1"
BUNDLE_SCHEMA = "techguytool-huawei.kirin-xray-contract-bundle.v1"
DONOR_REPOSITORY = "jaydumisuni/kirin"
DETERMINISTIC_CLOCK_BASIS = "deterministic_replay_not_capture_time"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_USB_RE = re.compile(r"^[0-9A-F]{4}:[0-9A-F]{4}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,95}$")
_FORBIDDEN_CAPABILITY_PARTS = (
    "erase",
    "flash",
    "loader",
    "partition_write",
    "reboot",
    "relock",
    "unlock",
    "write",
)

_TOP_LEVEL_KEYS = {
    "clock",
    "donor",
    "endpoints",
    "evidence",
    "safety",
    "scenario_id",
    "schema",
    "session",
    "sources",
    "twin",
}
_DONOR_KEYS = {"commit", "repository", "version"}
_CLOCK_KEYS = {
    "basis",
    "created_at",
    "fresh_until",
    "last_observed_at",
    "validation_now",
}
_SOURCE_KEYS = {"classification", "path", "sha256"}
_SESSION_KEYS = {"candidate_id", "confidence_bps", "session_state"}
_ENDPOINT_KEYS = {
    "capability_ids",
    "confidence_bps",
    "endpoint_key",
    "mode",
    "observed_at",
    "observed_state",
    "source_indexes",
    "transport",
    "usb_vid_pid",
}
_EVIDENCE_KEYS = {
    "confidence_bps",
    "evidence_kind",
    "source_indexes",
    "subject_id",
    "verdict",
}
_TWIN_KEYS = {
    "confidence_bps",
    "firmware_material",
    "identity_material",
    "source_indexes",
    "storage_material",
    "twin_state",
    "verification_status",
}
_SAFETY_KEYS = {"explanation", "reason_codes", "release_blocked"}


class KirinReplayError(ValueError):
    """Fail-closed replay or contract construction error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class GatewayPublisher(Protocol):
    def register_provider(self, manifest: Mapping[str, Any]) -> dict[str, Any]: ...

    def open_physical_session(self, fingerprint_sha256: str) -> dict[str, Any]: ...

    def record_endpoint(
        self,
        session_id: str,
        endpoint_key: str,
        mode: str,
        transport: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def publish_contract(
        self,
        component_id: str,
        contract: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    scenario_id: str
    fixture_sha256: str
    physical_session_id: str
    continuity_token_sha256: str
    contracts: tuple[dict[str, Any], ...]
    safety: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_SCHEMA,
            "scenario_id": self.scenario_id,
            "fixture_sha256": self.fixture_sha256,
            "physical_session_id": self.physical_session_id,
            "continuity_token_sha256": self.continuity_token_sha256,
            "contracts": [dict(contract) for contract in self.contracts],
            "safety": dict(self.safety),
            "write_authorized": False,
            "device_authority": "none",
            "xray_authority": "read_only",
        }

    @property
    def canonical(self) -> str:
        return canonical_json(self.to_dict())

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_dict())


def provider_manifest() -> dict[str, Any]:
    """Return the exact Gateway manifest for the read-only Kirin specialist."""

    return {
        "component_id": PROVIDER_ID,
        "version": PROVIDER_VERSION,
        "device_access": "read_only",
        "contract_authorities": ["diagnosis", "observation", "verification"],
        "capabilities": ["contract.publish", "evidence.read"],
    }


def load_replay(source: Path | str | Mapping[str, Any]) -> dict[str, Any]:
    """Load and structurally validate one deterministic replay document."""

    if isinstance(source, Mapping):
        document = json.loads(json.dumps(dict(source), ensure_ascii=False, allow_nan=False))
    else:
        path = Path(source)
        try:
            document = json.loads(path.read_text(encoding="utf-8", errors="strict"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise KirinReplayError("MALFORMED_REPLAY", str(exc)) from exc
    if not isinstance(document, dict):
        raise KirinReplayError("INVALID_REPLAY_TYPE", "replay document must be an object")
    _validate_replay_document(document)
    return document


def render_replay(
    source: Path | str | Mapping[str, Any],
    *,
    physical_session_id: str | None = None,
) -> ReplayBundle:
    """Render one replay into deterministic, Phase 2-valid Xray contracts."""

    document = load_replay(source)
    fixture_sha256 = canonical_sha256(document)
    namespace = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"urn:thetechguy:kirin-xray:{document['scenario_id']}:{fixture_sha256}",
    )
    session_id = physical_session_id or str(uuid.uuid5(namespace, "physical-session"))
    _require_uuid(session_id, "physical_session_id")

    clock = document["clock"]
    source_hashes = [record["sha256"] for record in document["sources"]]
    all_hashes = sorted(set(source_hashes))
    continuity_token = canonical_sha256(
        {
            "candidate_id": document["session"]["candidate_id"],
            "donor": document["donor"],
            "scenario_id": document["scenario_id"],
            "source_hashes": all_hashes,
        }
    )

    contracts: list[dict[str, Any]] = []
    contracts.append(
        _contract(
            namespace=namespace,
            role="physical-session",
            contract_type="physical_device_session",
            authority="observation",
            created_at=clock["created_at"],
            physical_session_id=session_id,
            evidence_hashes=all_hashes,
            confidence_bps=document["session"]["confidence_bps"],
            expires_at=None,
            payload={
                "continuity_token_sha256": continuity_token,
                "endpoint_count": len(document["endpoints"]),
                "last_observed_at": clock["last_observed_at"],
                "selected_candidate_id": document["session"]["candidate_id"],
                "session_state": document["session"]["session_state"],
                "started_at": clock["created_at"],
                "write_allowed": False,
            },
        )
    )

    for index, endpoint in enumerate(document["endpoints"]):
        hashes = _source_hashes(document, endpoint["source_indexes"])
        endpoint_id_hash = canonical_sha256(
            {
                "endpoint_key": endpoint["endpoint_key"],
                "mode": endpoint["mode"],
                "scenario_id": document["scenario_id"],
                "transport": endpoint["transport"],
                "usb_vid_pid": endpoint["usb_vid_pid"],
            }
        )
        contracts.append(
            _contract(
                namespace=namespace,
                role=f"endpoint-{index}",
                contract_type="endpoint_observation",
                authority="observation",
                created_at=endpoint["observed_at"],
                physical_session_id=session_id,
                evidence_hashes=hashes,
                confidence_bps=endpoint["confidence_bps"],
                expires_at=None,
                payload={
                    "capability_ids": endpoint["capability_ids"],
                    "endpoint_id_hash": endpoint_id_hash,
                    "observed_at": endpoint["observed_at"],
                    "observed_state": endpoint["observed_state"],
                    "transport": endpoint["transport"],
                    "usb_vid_pid": endpoint["usb_vid_pid"],
                },
            )
        )

    for index, evidence in enumerate(document["evidence"]):
        hashes = _source_hashes(document, evidence["source_indexes"])
        contracts.append(
            _contract(
                namespace=namespace,
                role=f"evidence-{index}",
                contract_type="device_evidence",
                authority="diagnosis",
                created_at=clock["last_observed_at"],
                physical_session_id=session_id,
                evidence_hashes=hashes,
                confidence_bps=evidence["confidence_bps"],
                expires_at=clock["fresh_until"],
                payload={
                    "evidence_kind": evidence["evidence_kind"],
                    "fresh_until": clock["fresh_until"],
                    "source_count": len(set(evidence["source_indexes"])),
                    "subject_id": evidence["subject_id"],
                    "verdict": evidence["verdict"],
                    "write_allowed": False,
                },
            )
        )

    twin = document["twin"]
    contracts.append(
        _contract(
            namespace=namespace,
            role="device-twin",
            contract_type="device_twin",
            authority="verification",
            created_at=clock["last_observed_at"],
            physical_session_id=session_id,
            evidence_hashes=_source_hashes(document, twin["source_indexes"]),
            confidence_bps=twin["confidence_bps"],
            expires_at=None,
            payload={
                "firmware_fingerprint": canonical_sha256(twin["firmware_material"]),
                "identity_fingerprint": canonical_sha256(twin["identity_material"]),
                "storage_fingerprint": canonical_sha256(twin["storage_material"]),
                "twin_state": twin["twin_state"],
                "verification_status": twin["verification_status"],
                "write_allowed": False,
            },
        )
    )

    for contract in contracts:
        _validate_rendered_contract(contract, clock["validation_now"], session_id)

    return ReplayBundle(
        scenario_id=document["scenario_id"],
        fixture_sha256=fixture_sha256,
        physical_session_id=session_id,
        continuity_token_sha256=continuity_token,
        contracts=tuple(contracts),
        safety=dict(document["safety"]),
    )


def publish_replay(
    client: GatewayPublisher,
    source: Path | str | Mapping[str, Any],
) -> dict[str, Any]:
    """Register Kirin Xray, bind a replay to a live Gateway session, and publish it."""

    document = load_replay(source)
    deterministic = render_replay(document)
    registered = client.register_provider(provider_manifest())
    physical = client.open_physical_session(deterministic.continuity_token_sha256)
    runtime_session_id = str(physical.get("session_id", ""))
    _require_uuid(runtime_session_id, "gateway physical session")

    endpoint_records = []
    for endpoint in document["endpoints"]:
        endpoint_records.append(
            client.record_endpoint(
                runtime_session_id,
                endpoint["endpoint_key"],
                endpoint["mode"],
                endpoint["transport"],
                {
                    "fixture_sha256": deterministic.fixture_sha256,
                    "read_only": True,
                    "source_hashes": _source_hashes(document, endpoint["source_indexes"]),
                    "usb_vid_pid": endpoint["usb_vid_pid"],
                },
            )
        )

    bound = render_replay(document, physical_session_id=runtime_session_id)
    receipts = []
    for contract in bound.contracts:
        receipts.append(
            client.publish_contract(
                PROVIDER_ID,
                contract,
                _validation_context(
                    contract,
                    document["clock"]["validation_now"],
                    runtime_session_id,
                ),
            )
        )

    return {
        "schema": "techguytool-huawei.kirin-xray-gateway-publication.v1",
        "scenario_id": bound.scenario_id,
        "fixture_sha256": bound.fixture_sha256,
        "deterministic_bundle_sha256": deterministic.sha256,
        "runtime_bundle_sha256": bound.sha256,
        "physical_session_id": runtime_session_id,
        "provider": registered,
        "endpoint_records": endpoint_records,
        "receipts": receipts,
        "safety": dict(bound.safety),
        "write_authorized": False,
        "device_authority": "none",
        "xray_authority": "read_only",
    }


def _contract(
    *,
    namespace: uuid.UUID,
    role: str,
    contract_type: str,
    authority: str,
    created_at: str,
    physical_session_id: str,
    evidence_hashes: Sequence[str],
    confidence_bps: int,
    expires_at: str | None,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract_type": contract_type,
        "contract_id": str(uuid.uuid5(namespace, f"contract:{role}")),
        "producer": PROVIDER_ID,
        "created_at": created_at,
        "physical_session_id": physical_session_id,
        "evidence_hashes": sorted(set(evidence_hashes)),
        "confidence_bps": confidence_bps,
        "expires_at": expires_at,
        "authority": authority,
        "single_use": False,
        "consumed_at": None,
        "payload": dict(payload),
    }


def _validation_context(
    contract: Mapping[str, Any], validation_now: str, session_id: str
) -> dict[str, Any]:
    return {
        "now": validation_now,
        "expected_contract_type": contract["contract_type"],
        "expected_physical_session_id": session_id,
        "expected_authority": contract["authority"],
    }


def _validate_rendered_contract(
    contract: Mapping[str, Any], validation_now: str, session_id: str
) -> None:
    result = validate_contract(
        contract,
        context=_validation_context(contract, validation_now, session_id),
    )
    if not result.ok:
        rendered = "; ".join(
            f"{error.code}@{error.path}: {error.message}" for error in result.errors
        )
        raise KirinReplayError(
            "INVALID_RENDERED_CONTRACT",
            f"{contract.get('contract_type')}: {rendered}",
        )


def _source_hashes(document: Mapping[str, Any], indexes: Sequence[int]) -> list[str]:
    sources = document["sources"]
    return sorted({sources[index]["sha256"] for index in indexes})


def _validate_replay_document(document: Mapping[str, Any]) -> None:
    _require_exact_keys(document, _TOP_LEVEL_KEYS, "$")
    if document["schema"] != REPLAY_SCHEMA:
        raise KirinReplayError("UNSUPPORTED_REPLAY_SCHEMA", str(document["schema"]))
    scenario_id = _require_string(document["scenario_id"], "$.scenario_id")
    if len(scenario_id) > 128:
        raise KirinReplayError("INVALID_REPLAY", "scenario_id exceeds 128 characters")

    donor = _require_mapping(document["donor"], "$.donor")
    _require_exact_keys(donor, _DONOR_KEYS, "$.donor")
    if donor["repository"] != DONOR_REPOSITORY:
        raise KirinReplayError("DONOR_MISMATCH", "unexpected Kirin donor repository")
    if not isinstance(donor["commit"], str) or _COMMIT_RE.fullmatch(donor["commit"]) is None:
        raise KirinReplayError("INVALID_REPLAY", "donor.commit must be a full lowercase Git SHA")
    if not isinstance(donor["version"], str) or _SEMVER_RE.fullmatch(donor["version"]) is None:
        raise KirinReplayError("INVALID_REPLAY", "donor.version must be semantic version X.Y.Z")

    clock = _require_mapping(document["clock"], "$.clock")
    _require_exact_keys(clock, _CLOCK_KEYS, "$.clock")
    if clock["basis"] != DETERMINISTIC_CLOCK_BASIS:
        raise KirinReplayError("INVALID_REPLAY_CLOCK", "capture time must not be invented")
    created = parse_timestamp(_require_string(clock["created_at"], "$.clock.created_at"))
    last = parse_timestamp(
        _require_string(clock["last_observed_at"], "$.clock.last_observed_at")
    )
    now = parse_timestamp(_require_string(clock["validation_now"], "$.clock.validation_now"))
    fresh = parse_timestamp(_require_string(clock["fresh_until"], "$.clock.fresh_until"))
    if not created <= last <= now < fresh:
        raise KirinReplayError(
            "INVALID_REPLAY_CLOCK",
            "clock must satisfy created_at <= last_observed_at <= validation_now < fresh_until",
        )

    sources = document["sources"]
    if not isinstance(sources, list) or not sources:
        raise KirinReplayError("INVALID_REPLAY", "sources must be a non-empty array")
    source_hashes: list[str] = []
    for index, source in enumerate(sources):
        record = _require_mapping(source, f"$.sources[{index}]")
        _require_exact_keys(record, _SOURCE_KEYS, f"$.sources[{index}]")
        _require_string(record["path"], f"$.sources[{index}].path")
        _require_string(record["classification"], f"$.sources[{index}].classification")
        digest = record["sha256"]
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise KirinReplayError(
                "INVALID_SOURCE_HASH", f"$.sources[{index}].sha256 must be lowercase SHA-256"
            )
        source_hashes.append(digest)
    if len(source_hashes) != len(set(source_hashes)):
        raise KirinReplayError("DUPLICATE_SOURCE_HASH", "source hashes must be unique")

    session = _require_mapping(document["session"], "$.session")
    _require_exact_keys(session, _SESSION_KEYS, "$.session")
    _require_string(session["candidate_id"], "$.session.candidate_id")
    if session["session_state"] not in {
        "observing",
        "certified",
        "investigate",
        "unsafe",
        "closed",
    }:
        raise KirinReplayError("INVALID_REPLAY", "unsupported session_state")
    _require_confidence(session["confidence_bps"], "$.session.confidence_bps")

    endpoints = document["endpoints"]
    if not isinstance(endpoints, list):
        raise KirinReplayError("INVALID_REPLAY", "endpoints must be an array")
    endpoint_keys: set[str] = set()
    for index, endpoint in enumerate(endpoints):
        item = _require_mapping(endpoint, f"$.endpoints[{index}]")
        _require_exact_keys(item, _ENDPOINT_KEYS, f"$.endpoints[{index}]")
        endpoint_key = _require_string(
            item["endpoint_key"], f"$.endpoints[{index}].endpoint_key"
        )
        if endpoint_key in endpoint_keys:
            raise KirinReplayError("DUPLICATE_ENDPOINT", endpoint_key)
        endpoint_keys.add(endpoint_key)
        _require_string(item["mode"], f"$.endpoints[{index}].mode")
        _require_string(item["transport"], f"$.endpoints[{index}].transport")
        if not isinstance(item["usb_vid_pid"], str) or _USB_RE.fullmatch(item["usb_vid_pid"]) is None:
            raise KirinReplayError("INVALID_REPLAY", "usb_vid_pid must use uppercase VVVV:PPPP")
        _require_string(item["observed_state"], f"$.endpoints[{index}].observed_state")
        parse_timestamp(_require_string(item["observed_at"], f"$.endpoints[{index}].observed_at"))
        _require_confidence(item["confidence_bps"], f"$.endpoints[{index}].confidence_bps")
        capabilities = _require_sorted_strings(
            item["capability_ids"], f"$.endpoints[{index}].capability_ids", allow_empty=True
        )
        for capability in capabilities:
            lowered = capability.casefold()
            if any(part in lowered for part in _FORBIDDEN_CAPABILITY_PARTS):
                raise KirinReplayError(
                    "WRITE_CAPABILITY_FORBIDDEN", f"endpoint capability {capability!r}"
                )
        _require_source_indexes(
            item["source_indexes"], len(sources), f"$.endpoints[{index}].source_indexes"
        )

    evidence = document["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise KirinReplayError("INVALID_REPLAY", "evidence must be a non-empty array")
    subjects: set[str] = set()
    for index, item_value in enumerate(evidence):
        item = _require_mapping(item_value, f"$.evidence[{index}]")
        _require_exact_keys(item, _EVIDENCE_KEYS, f"$.evidence[{index}]")
        subject = _require_string(item["subject_id"], f"$.evidence[{index}].subject_id")
        if subject in subjects:
            raise KirinReplayError("DUPLICATE_EVIDENCE_SUBJECT", subject)
        subjects.add(subject)
        _require_string(item["evidence_kind"], f"$.evidence[{index}].evidence_kind")
        _require_string(item["verdict"], f"$.evidence[{index}].verdict")
        _require_confidence(item["confidence_bps"], f"$.evidence[{index}].confidence_bps")
        _require_source_indexes(
            item["source_indexes"], len(sources), f"$.evidence[{index}].source_indexes"
        )

    twin = _require_mapping(document["twin"], "$.twin")
    _require_exact_keys(twin, _TWIN_KEYS, "$.twin")
    _require_string(twin["twin_state"], "$.twin.twin_state")
    _require_string(twin["verification_status"], "$.twin.verification_status")
    for name in ("identity_material", "firmware_material", "storage_material"):
        _require_mapping(twin[name], f"$.twin.{name}")
    _require_confidence(twin["confidence_bps"], "$.twin.confidence_bps")
    _require_source_indexes(twin["source_indexes"], len(sources), "$.twin.source_indexes")

    safety = _require_mapping(document["safety"], "$.safety")
    _require_exact_keys(safety, _SAFETY_KEYS, "$.safety")
    if not isinstance(safety["release_blocked"], bool):
        raise KirinReplayError("INVALID_REPLAY", "safety.release_blocked must be boolean")
    _require_string(safety["explanation"], "$.safety.explanation")
    reasons = _require_sorted_strings(
        safety["reason_codes"], "$.safety.reason_codes", allow_empty=False
    )
    if any(_REASON_RE.fullmatch(reason) is None for reason in reasons):
        raise KirinReplayError("INVALID_REPLAY", "safety reason code is malformed")


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise KirinReplayError("UNKNOWN_REPLAY_MEMBER", f"{path}: {', '.join(unknown)}")
    if missing:
        raise KirinReplayError("MISSING_REPLAY_MEMBER", f"{path}: {', '.join(missing)}")


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be an object")
    return dict(value)


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be a non-empty string")
    return value


def _require_confidence(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000:
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be an integer from 0 to 10000")
    return value


def _require_sorted_strings(value: Any, path: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be an array of strings")
    if not allow_empty and not value:
        raise KirinReplayError("INVALID_REPLAY", f"{path} must not be empty")
    if value != sorted(set(value)):
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be sorted and unique")
    return value


def _require_source_indexes(value: Any, source_count: int, path: str) -> list[int]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be a non-empty integer array")
    if value != sorted(set(value)):
        raise KirinReplayError("INVALID_REPLAY", f"{path} must be sorted and unique")
    if value[0] < 0 or value[-1] >= source_count:
        raise KirinReplayError("INVALID_SOURCE_REFERENCE", path)
    return value


def _require_uuid(value: str, path: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise KirinReplayError("INVALID_SESSION_ID", f"{path} is not a UUID") from exc
    if str(parsed) != value or parsed.version not in {1, 2, 3, 4, 5}:
        raise KirinReplayError("INVALID_SESSION_ID", f"{path} must be a canonical UUID")

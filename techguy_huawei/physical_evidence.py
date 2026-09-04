from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .windows_release import REQUIRED_MATRIX_IDS, SHA256_RE, WindowsReleaseError, _validate_physical_evidence

PACKET_SCHEMA = "techguytool-huawei.physical-evidence-packet.v1"


class PhysicalEvidenceError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PhysicalEvidenceError(f"Evidence value is not canonical JSON: {exc}") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalize_verified_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PhysicalEvidenceError("verified_at must be RFC3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PhysicalEvidenceError("verified_at must be RFC3339 UTC ending in Z") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise PhysicalEvidenceError("verified_at must be UTC")
    return value



def validate_proof_output_path(path: Path | str, proof_root: Path | str) -> Path:
    resolved = Path(path).resolve()
    root = Path(proof_root).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PhysicalEvidenceError(f"Evidence output must stay under the proof root: {root}") from exc
    return resolved

def build_physical_evidence_packet(
    *,
    entry_id: str,
    subject: Mapping[str, Any],
    evidence_files: Sequence[Path | str],
    evidence_refs: Sequence[str],
    verifier: str,
    verified_at: str | None = None,
) -> dict[str, Any]:
    if entry_id not in REQUIRED_MATRIX_IDS:
        raise PhysicalEvidenceError(f"Unknown physical proof matrix entry: {entry_id}")
    if not isinstance(subject, Mapping) or not subject:
        raise PhysicalEvidenceError("Subject identity must be a non-empty JSON object")
    verifier = str(verifier).strip()
    if not verifier:
        raise PhysicalEvidenceError("Verifier is required")

    refs = sorted({str(ref).strip() for ref in evidence_refs if str(ref).strip()})
    if not refs:
        raise PhysicalEvidenceError("At least one evidence reference is required")

    file_records: list[dict[str, Any]] = []
    names: set[str] = set()
    for raw_path in evidence_files:
        path = Path(raw_path)
        if not path.is_file():
            raise PhysicalEvidenceError(f"Evidence file does not exist: {path}")
        if path.name in names:
            raise PhysicalEvidenceError(f"Duplicate evidence filename: {path.name}")
        names.add(path.name)
        data = path.read_bytes()
        file_records.append(
            {
                "name": path.name,
                "sha256": _sha256_bytes(data),
                "size": len(data),
            }
        )
    if not file_records:
        raise PhysicalEvidenceError("At least one evidence file is required")
    file_records.sort(key=lambda item: item["name"])

    subject_identity_hash = _sha256_bytes(_canonical_bytes(dict(subject)))
    timestamp = _normalize_verified_at(verified_at)
    material = {
        "entry_id": entry_id,
        "subject_identity_hash": subject_identity_hash,
        "evidence_refs": refs,
        "verified_at": timestamp,
        "verifier": verifier,
        "files": file_records,
    }
    evidence_sha256 = _sha256_bytes(_canonical_bytes(material))
    evidence = {
        "evidence_id": f"{entry_id}-{evidence_sha256[:16]}",
        "evidence_sha256": evidence_sha256,
        "evidence_refs": refs,
        "subject_identity_hash": subject_identity_hash,
        "verified_at": timestamp,
        "verifier": verifier,
    }
    try:
        _validate_physical_evidence(entry_id, evidence)
    except WindowsReleaseError as exc:
        raise PhysicalEvidenceError(str(exc)) from exc
    return {
        "schema": PACKET_SCHEMA,
        "entry_id": entry_id,
        "material": material,
        "evidence": evidence,
    }


def validate_physical_evidence_packet(packet: Mapping[str, Any]) -> None:
    if packet.get("schema") != PACKET_SCHEMA:
        raise PhysicalEvidenceError("Physical evidence packet schema mismatch")
    entry_id = packet.get("entry_id")
    if entry_id not in REQUIRED_MATRIX_IDS:
        raise PhysicalEvidenceError(f"Unknown physical proof matrix entry: {entry_id}")
    material = packet.get("material")
    evidence = packet.get("evidence")
    if not isinstance(material, Mapping) or not isinstance(evidence, Mapping):
        raise PhysicalEvidenceError("Physical evidence packet structure invalid")
    if set(material) != {"entry_id", "subject_identity_hash", "evidence_refs", "verified_at", "verifier", "files"}:
        raise PhysicalEvidenceError("Physical evidence material fields invalid")
    if material.get("entry_id") != entry_id:
        raise PhysicalEvidenceError("Physical evidence matrix entry mismatch")
    subject_hash = material.get("subject_identity_hash")
    if not isinstance(subject_hash, str) or not SHA256_RE.fullmatch(subject_hash):
        raise PhysicalEvidenceError("Physical evidence subject identity hash invalid")
    refs = material.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise PhysicalEvidenceError("Physical evidence references invalid")
    files = material.get("files")
    if not isinstance(files, list) or not files:
        raise PhysicalEvidenceError("Physical evidence files missing")
    names: set[str] = set()
    for item in files:
        if not isinstance(item, Mapping) or set(item) != {"name", "sha256", "size"}:
            raise PhysicalEvidenceError("Physical evidence file record invalid")
        name = item.get("name")
        digest = item.get("sha256")
        size = item.get("size")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise PhysicalEvidenceError("Physical evidence file name invalid")
        names.add(name)
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise PhysicalEvidenceError("Physical evidence file hash invalid")
        if not isinstance(size, int) or size < 0:
            raise PhysicalEvidenceError("Physical evidence file size invalid")

    expected_material_hash = _sha256_bytes(_canonical_bytes(dict(material)))
    if evidence.get("evidence_sha256") != expected_material_hash:
        raise PhysicalEvidenceError("Physical evidence material hash mismatch")
    if evidence.get("subject_identity_hash") != subject_hash:
        raise PhysicalEvidenceError("Physical evidence subject hash mismatch")
    if evidence.get("evidence_refs") != refs:
        raise PhysicalEvidenceError("Physical evidence reference mismatch")
    if evidence.get("verified_at") != material.get("verified_at"):
        raise PhysicalEvidenceError("Physical evidence verified_at mismatch")
    if evidence.get("verifier") != material.get("verifier"):
        raise PhysicalEvidenceError("Physical evidence verifier mismatch")
    try:
        _validate_physical_evidence(str(entry_id), evidence)
    except WindowsReleaseError as exc:
        raise PhysicalEvidenceError(str(exc)) from exc

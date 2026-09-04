from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from techguy_huawei.physical_evidence import (
    PhysicalEvidenceError,
    build_physical_evidence_packet,
    validate_physical_evidence_packet,
    validate_proof_output_path,
)


def _fixed_time() -> str:
    return "2026-09-04T15:30:00Z"


@pytest.fixture
def evidence_sandbox() -> Path:
    root = Path(__file__).resolve().parents[1] / "proof" / "test-physical-evidence" / uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_packet_is_deterministic_and_omits_raw_subject_identity(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("VID_12D1 PID_107E model=VTR-L29\n", encoding="utf-8")
    subject_a = {"serial": "SECRET-123", "model": "VTR-L29", "soc": "Kirin960"}
    subject_b = {"soc": "Kirin960", "model": "VTR-L29", "serial": "SECRET-123"}

    first = build_physical_evidence_packet(
        entry_id="mtp_direct_route",
        subject=subject_a,
        evidence_files=[log],
        evidence_refs=["artifact://athena/mtp/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    second = build_physical_evidence_packet(
        entry_id="mtp_direct_route",
        subject=subject_b,
        evidence_files=[log],
        evidence_refs=["artifact://athena/mtp/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )

    assert first == second
    assert "SECRET-123" not in repr(first)
    assert first["entry_id"] == "mtp_direct_route"
    assert first["evidence"]["subject_identity_hash"] == first["material"]["subject_identity_hash"]
    validate_physical_evidence_packet(first)


def test_evidence_digest_changes_when_captured_file_changes(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("before\n", encoding="utf-8")
    first = build_physical_evidence_packet(
        entry_id="authorized_adb_direct_route",
        subject={"model": "VTR-L29"},
        evidence_files=[log],
        evidence_refs=["artifact://athena/adb/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    log.write_text("after\n", encoding="utf-8")
    second = build_physical_evidence_packet(
        entry_id="authorized_adb_direct_route",
        subject={"model": "VTR-L29"},
        evidence_files=[log],
        evidence_refs=["artifact://athena/adb/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    assert first["evidence"]["evidence_sha256"] != second["evidence"]["evidence_sha256"]


def test_unknown_matrix_entry_is_rejected(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("evidence\n", encoding="utf-8")
    with pytest.raises(PhysicalEvidenceError, match="Unknown physical proof matrix entry"):
        build_physical_evidence_packet(
            entry_id="invented_support",
            subject={"model": "UNKNOWN"},
            evidence_files=[log],
            evidence_refs=["artifact://athena/unknown/device.txt"],
            verifier="THETECHGUY physical certification",
            verified_at=_fixed_time(),
        )


def test_packet_validator_rejects_tampered_material(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("evidence\n", encoding="utf-8")
    packet = build_physical_evidence_packet(
        entry_id="normal_fastboot_direct_route",
        subject={"model": "VTR-L29"},
        evidence_files=[log],
        evidence_refs=["artifact://athena/fastboot/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    tampered = copy.deepcopy(packet)
    tampered["material"]["files"][0]["sha256"] = "0" * 64
    with pytest.raises(PhysicalEvidenceError, match="material hash mismatch"):
        validate_physical_evidence_packet(tampered)


def test_build_requires_at_least_one_real_evidence_file(evidence_sandbox: Path) -> None:
    missing = evidence_sandbox / "missing.txt"
    with pytest.raises(PhysicalEvidenceError, match="Evidence file does not exist"):
        build_physical_evidence_packet(
            entry_id="recovery_detection",
            subject={"model": "VTR-L29"},
            evidence_files=[missing],
            evidence_refs=["artifact://athena/recovery/device.txt"],
            verifier="THETECHGUY physical certification",
            verified_at=_fixed_time(),
        )

def test_cli_writes_valid_packet_without_mutating_matrix(evidence_sandbox: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    subject = evidence_sandbox / "subject.json"
    evidence_file = evidence_sandbox / "pnp.txt"
    output = evidence_sandbox / "packet.json"
    subject.write_text(json.dumps({"model": "VTR-L29", "serial": "PRIVATE-SERIAL"}), encoding="utf-8")
    evidence_file.write_text("USB\\VID_12D1&PID_107E\n", encoding="utf-8")
    matrix = root / "manifests" / "phase15_physical_proof_matrix.json"
    before = matrix.read_bytes()

    completed = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "record_physical_proof.py"),
            "--entry-id",
            "mtp_direct_route",
            "--subject-json",
            str(subject),
            "--evidence-file",
            str(evidence_file),
            "--evidence-ref",
            "artifact://athena/mtp/pnp.txt",
            "--verifier",
            "THETECHGUY physical certification",
            "--verified-at",
            _fixed_time(),
            "--output",
            str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    packet = json.loads(output.read_text(encoding="utf-8"))
    validate_physical_evidence_packet(packet)
    assert "PRIVATE-SERIAL" not in output.read_text(encoding="utf-8")
    assert matrix.read_bytes() == before

def test_output_path_must_stay_under_repository_proof_root() -> None:
    root = Path(__file__).resolve().parents[1]
    proof_root = root / "proof"
    allowed = validate_proof_output_path(proof_root / "physical" / "packet.json", proof_root)
    assert allowed == (proof_root / "physical" / "packet.json").resolve()
    with pytest.raises(PhysicalEvidenceError, match="must stay under the proof root"):
        validate_proof_output_path(root / "manifests" / "phase15_physical_proof_matrix.json", proof_root)

def test_evidence_digest_is_bound_to_matrix_entry(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("same capture\n", encoding="utf-8")
    common = dict(
        subject={"model": "VTR-L29"},
        evidence_files=[log],
        evidence_refs=["artifact://athena/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    mtp = build_physical_evidence_packet(entry_id="mtp_direct_route", **common)
    adb = build_physical_evidence_packet(entry_id="authorized_adb_direct_route", **common)
    assert mtp["evidence"]["evidence_sha256"] != adb["evidence"]["evidence_sha256"]


def test_packet_validator_rejects_tampered_verifier(evidence_sandbox: Path) -> None:
    log = evidence_sandbox / "device.txt"
    log.write_text("evidence\n", encoding="utf-8")
    packet = build_physical_evidence_packet(
        entry_id="mtp_direct_route",
        subject={"model": "VTR-L29"},
        evidence_files=[log],
        evidence_refs=["artifact://athena/mtp/device.txt"],
        verifier="THETECHGUY physical certification",
        verified_at=_fixed_time(),
    )
    tampered = copy.deepcopy(packet)
    tampered["evidence"]["verifier"] = "different verifier"
    with pytest.raises(PhysicalEvidenceError, match="verifier mismatch"):
        validate_physical_evidence_packet(tampered)

def test_cli_accepts_utf8_bom_subject_json(evidence_sandbox: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    subject = evidence_sandbox / "subject-bom.json"
    evidence_file = evidence_sandbox / "pnp.txt"
    output = evidence_sandbox / "packet-bom.json"
    subject.write_text(json.dumps({"model": "VTR-L29", "serial": "PRIVATE-SERIAL"}), encoding="utf-8-sig")
    evidence_file.write_text("USB\\VID_12D1&PID_107E\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "record_physical_proof.py"),
            "--entry-id", "mtp_direct_route",
            "--subject-json", str(subject),
            "--evidence-file", str(evidence_file),
            "--evidence-ref", "artifact://athena/mtp/pnp.txt",
            "--verifier", "THETECHGUY physical certification",
            "--verified-at", _fixed_time(),
            "--output", str(output),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    validate_physical_evidence_packet(json.loads(output.read_text(encoding="utf-8")))

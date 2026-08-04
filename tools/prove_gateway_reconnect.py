from __future__ import annotations

import argparse
import json
import queue
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.gateway_client import GatewayClient, GatewayClientError


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _start_gateway(binary: Path, database: Path, port: int) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [
            str(binary),
            "serve",
            "--db",
            str(database),
            "--listen",
            f"127.0.0.1:{port}",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    assert process.stdout is not None
    ready: queue.Queue[str] = queue.Queue(maxsize=1)

    def read_ready() -> None:
        ready.put(process.stdout.readline())

    threading.Thread(target=read_ready, daemon=True).start()
    try:
        line = ready.get(timeout=20)
    except queue.Empty as exc:
        process.kill()
        stderr = process.stderr.read() if process.stderr is not None else ""
        raise RuntimeError(f"gateway did not become ready: {stderr}") from exc
    if not line:
        stderr = process.stderr.read() if process.stderr is not None else ""
        raise RuntimeError(f"gateway exited before readiness: {stderr}")
    payload = json.loads(line)
    if payload.get("status") != "ready" or payload.get("device_authority") != "none":
        raise RuntimeError(f"unexpected gateway readiness payload: {payload}")
    return process


def _stop_gateway(process: subprocess.Popen[str], client: GatewayClient) -> None:
    client.shutdown()
    try:
        return_code = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("gateway did not stop after local shutdown request")
    if return_code != 0:
        stderr = process.stderr.read() if process.stderr is not None else ""
        raise RuntimeError(f"gateway exited with {return_code}: {stderr}")


def prove(binary: Path) -> dict[str, Any]:
    if not binary.is_file():
        raise FileNotFoundError(f"gateway binary not found: {binary}")

    with tempfile.TemporaryDirectory(prefix="ttg-device-gateway-proof-") as temporary:
        database = Path(temporary) / "gateway.sqlite3"
        port = _free_port()
        first_process = _start_gateway(binary, database, port)
        first_client = GatewayClient(port=port)
        health = first_client.health()
        if health != {
            "status": "ready",
            "schema_version": 1,
            "device_authority": "none",
            "xray_authority": "read_only",
        }:
            raise AssertionError(f"unexpected health response: {health}")

        physical = first_client.open_physical_session("a" * 64)
        first_client.record_endpoint(
            physical["session_id"],
            "usb:12d1:107e:slot-1",
            "normal",
            "mtp",
            {"authorized": True},
        )
        operation = first_client.open_operation(physical["session_id"], "b" * 64)
        transitioned = first_client.transition_operation(
            operation["operation_id"], "evidence_collection"
        )
        if transitioned["stage"] != "evidence_collection":
            raise AssertionError("operation did not enter evidence_collection")

        second_client = GatewayClient(port=port)
        same_physical = second_client.get_physical_session(physical["session_id"])
        same_operation = second_client.get_operation(operation["operation_id"])
        if same_physical["fingerprint_sha256"] != "a" * 64:
            raise AssertionError("UI reconnect lost physical-device identity")
        if same_operation["stage"] != "evidence_collection":
            raise AssertionError("UI reconnect lost operation stage")
        second_client.verify_journal()
        _stop_gateway(first_process, second_client)

        second_process = _start_gateway(binary, database, port)
        restarted_client = GatewayClient(port=port)
        recovered_physical = restarted_client.get_physical_session(physical["session_id"])
        recovered_operation = restarted_client.get_operation(operation["operation_id"])
        if recovered_physical["recovery_count"] < 1:
            raise AssertionError("gateway restart did not recover physical session")
        if recovered_operation["recovery_count"] < 1:
            raise AssertionError("gateway restart did not recover operation session")
        if recovered_operation["stage"] != "evidence_collection":
            raise AssertionError("gateway restart changed the operation stage")
        if recovered_operation["status"] != "recovering":
            raise AssertionError("gateway restart did not mark the operation recovering")
        resumed = restarted_client.resume_operation(operation["operation_id"])
        if resumed["status"] != "active":
            raise AssertionError("recovered operation did not resume")

        try:
            restarted_client.register_provider(
                {
                    "component_id": "unsafe.provider",
                    "version": "1.0.0",
                    "device_access": "read_only",
                    "contract_authorities": ["execution"],
                    "capabilities": ["device.unsupported_write"],
                }
            )
        except GatewayClientError as exc:
            if exc.code != "POLICY_DENIED":
                raise AssertionError(f"unexpected policy error: {exc}") from exc
        else:
            raise AssertionError("gateway accepted a non-allowlisted capability")

        doctor = restarted_client.doctor()
        if doctor.get("healthy") is not True or doctor.get("journal_valid") is not True:
            raise AssertionError(f"gateway doctor failed: {doctor}")
        snapshot = restarted_client.snapshot()
        if snapshot.get("device_authority") != "none":
            raise AssertionError("gateway snapshot expanded device authority")
        _stop_gateway(second_process, restarted_client)

    return {
        "schema": "techguytool-huawei.phase3-gateway-reconnect-proof.v1",
        "status": "PASS",
        "device_authority": "none",
        "xray_authority": "read_only",
        "ui_client_reconnect": True,
        "gateway_process_restart": True,
        "physical_identity_preserved": True,
        "operation_stage_preserved": True,
        "journal_chain_verified": True,
        "non_allowlisted_capability_rejected": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove TTG Device Gateway UI reconnect and process recovery"
    )
    parser.add_argument("--gateway-bin", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prove(args.gateway_bin.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

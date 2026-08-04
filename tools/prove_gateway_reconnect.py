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
from typing import Any, TextIO

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.gateway_client import GatewayClient, GatewayClientError


class RunningGateway:
    def __init__(
        self,
        process: subprocess.Popen[str],
        stdout_thread: threading.Thread,
        stderr_thread: threading.Thread,
        stdout_lines: list[str],
        stderr_lines: list[str],
    ) -> None:
        self.process = process
        self.stdout_thread = stdout_thread
        self.stderr_thread = stderr_thread
        self.stdout_lines = stdout_lines
        self.stderr_lines = stderr_lines

    def diagnostics(self) -> str:
        return "".join(self.stderr_lines + self.stdout_lines).strip()

    def join_drainers(self) -> None:
        self.stdout_thread.join(timeout=2)
        self.stderr_thread.join(timeout=2)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _start_gateway(binary: Path, database: Path, port: int) -> RunningGateway:
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
    assert process.stderr is not None
    ready: queue.Queue[str] = queue.Queue(maxsize=1)
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_thread = threading.Thread(
        target=_drain_stdout,
        args=(process.stdout, ready, stdout_lines),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_stream,
        args=(process.stderr, stderr_lines),
        daemon=True,
    )
    running = RunningGateway(
        process,
        stdout_thread,
        stderr_thread,
        stdout_lines,
        stderr_lines,
    )
    stdout_thread.start()
    stderr_thread.start()
    try:
        line = ready.get(timeout=20)
        if not line:
            raise RuntimeError("gateway exited before readiness")
        payload = json.loads(line)
        if payload.get("status") != "ready" or payload.get("device_authority") != "none":
            raise RuntimeError(f"unexpected gateway readiness payload: {payload}")
    except (queue.Empty, json.JSONDecodeError, RuntimeError) as exc:
        _terminate_gateway(running)
        details = running.diagnostics()
        raise RuntimeError(f"gateway did not become ready: {details}") from exc
    return running


def _drain_stdout(
    stream: TextIO,
    ready: queue.Queue[str],
    remaining_lines: list[str],
) -> None:
    first = True
    for line in stream:
        if first:
            ready.put(line)
            first = False
        else:
            remaining_lines.append(line)
    if first:
        ready.put("")


def _drain_stream(stream: TextIO, lines: list[str]) -> None:
    for line in stream:
        lines.append(line)


def _stop_gateway(running: RunningGateway, client: GatewayClient) -> None:
    try:
        client.shutdown()
        try:
            return_code = running.process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("gateway did not stop after local shutdown request") from exc
        if return_code != 0:
            raise RuntimeError(
                f"gateway exited with {return_code}: {running.diagnostics()}"
            )
    finally:
        _terminate_gateway(running)


def _terminate_gateway(running: RunningGateway) -> None:
    if running.process.poll() is None:
        running.process.terminate()
        try:
            running.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            running.process.kill()
            running.process.wait(timeout=5)
    running.join_drainers()


def prove(binary: Path) -> dict[str, Any]:
    if not binary.is_file():
        raise FileNotFoundError(f"gateway binary not found: {binary}")

    with tempfile.TemporaryDirectory(prefix="ttg-device-gateway-proof-") as temporary:
        database = Path(temporary) / "gateway.sqlite3"
        port = _free_port()
        first_process: RunningGateway | None = _start_gateway(binary, database, port)
        try:
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
            first_process = None
        finally:
            if first_process is not None:
                _terminate_gateway(first_process)

        second_process: RunningGateway | None = _start_gateway(binary, database, port)
        try:
            restarted_client = GatewayClient(port=port)
            recovered_physical = restarted_client.get_physical_session(
                physical["session_id"]
            )
            recovered_operation = restarted_client.get_operation(
                operation["operation_id"]
            )
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
            second_process = None
        finally:
            if second_process is not None:
                _terminate_gateway(second_process)

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
        "stdout_stderr_continuously_drained": True,
        "failed_runs_cleaned_up": True,
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

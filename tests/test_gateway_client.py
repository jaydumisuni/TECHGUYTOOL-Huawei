from __future__ import annotations

import copy
import json
import pickle
import socket
import threading

import pytest

from techguy_huawei.gateway_client import GatewayClient, GatewayClientError


def test_gateway_client_rejects_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="loopback"):
        GatewayClient(host="192.0.2.1")


def test_gateway_client_matches_request_id_and_reads_utf8_json() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve() -> None:
        connection, _ = listener.accept()
        with connection:
            request = json.loads(_read_line(connection).decode("utf-8"))
            response = {
                "request_id": request["request_id"],
                "ok": True,
                "result": {"message": "gateway prêt 🔍"},
            }
            connection.sendall(
                json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n"
            )
        listener.close()

    thread = threading.Thread(target=serve)
    thread.start()
    result = GatewayClient(port=port).request("health")
    thread.join(timeout=5)
    assert result == {"message": "gateway prêt 🔍"}


def test_gateway_client_raises_structured_error() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve() -> None:
        connection, _ = listener.accept()
        with connection:
            request = json.loads(_read_line(connection).decode("utf-8"))
            response = {
                "request_id": request["request_id"],
                "ok": False,
                "error": {"code": "POLICY_DENIED", "message": "blocked"},
            }
            connection.sendall(json.dumps(response).encode("utf-8") + b"\n")
        listener.close()

    thread = threading.Thread(target=serve)
    thread.start()
    with pytest.raises(GatewayClientError) as caught:
        GatewayClient(port=port).request("register_provider", {})
    thread.join(timeout=5)
    assert caught.value.code == "POLICY_DENIED"
    assert caught.value.message == "blocked"
    assert caught.value.args == ("POLICY_DENIED", "blocked")


def test_gateway_client_error_preserves_exception_protocols() -> None:
    error = GatewayClientError("PROTOCOL_ERROR", "invalid response")
    copied = copy.copy(error)
    restored = pickle.loads(pickle.dumps(error))
    assert str(error) == "PROTOCOL_ERROR: invalid response"
    assert error.args == ("PROTOCOL_ERROR", "invalid response")
    assert copied.code == error.code
    assert copied.message == error.message
    assert restored.code == error.code
    assert restored.message == error.message


def _read_line(stream: socket.socket) -> bytes:
    data = bytearray()
    while b"\n" not in data:
        chunk = stream.recv(4096)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data).split(b"\n", 1)[0]


def _usb_report_payload() -> dict[str, object]:
    return {
        "present": True,
        "state": "storage_only_pre_service",
        "transport": "windows_pnp_usb_storage",
        "vid": "12D1",
        "pid": "107E",
        "fingerprint_sha256": "a" * 64,
        "model": "identity_pending",
        "interfaces": ["HUAWEI", "USB Mass Storage Device"],
        "decision_code": "DIRECT_ROUTE_UNAVAILABLE",
        "next_action": "identify_model_then_enter_supported_service_mode",
        "screen_required": False,
        "device_modification": "none",
        "write_authority": "none",
    }


def test_usb_discovery_gateway_payload_is_read_only_and_private() -> None:
    report = _usb_report_payload()
    report["serial"] = "PRIVATE-SERIAL"
    payload = GatewayClient.usb_discovery_endpoint_payload(report)
    assert payload["write_authority"] == "none"
    assert payload["device_modification"] == "none"
    assert payload["fingerprint_sha256"] == "a" * 64
    assert "serial" not in payload
    assert "PRIVATE-SERIAL" not in repr(payload)


def test_record_usb_discovery_uses_existing_physical_session_and_endpoint_contract() -> None:
    calls: list[tuple[object, ...]] = []

    class FakeGateway(GatewayClient):
        def __init__(self) -> None:
            pass

        def open_physical_session(self, fingerprint_sha256: str) -> dict[str, object]:
            calls.append(("open", fingerprint_sha256))
            return {"session_id": "session-1"}

        def record_endpoint(
            self,
            session_id: str,
            endpoint_key: str,
            mode: str,
            transport: str,
            payload=None,
        ) -> dict[str, object]:
            calls.append(("record", session_id, endpoint_key, mode, transport, payload))
            return {"observation_id": "observation-1", "session_id": session_id}

    result = FakeGateway().record_usb_discovery(_usb_report_payload())
    assert result["observation_id"] == "observation-1"
    assert calls[0] == ("open", "a" * 64)
    record = calls[1]
    assert record[0:5] == (
        "record",
        "session-1",
        "huawei-usb:aaaaaaaaaaaaaaaa",
        "storage_only_pre_service",
        "windows_pnp_usb",
    )
    assert isinstance(record[5], dict)
    assert record[5]["write_authority"] == "none"

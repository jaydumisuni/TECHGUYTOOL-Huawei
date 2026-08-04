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

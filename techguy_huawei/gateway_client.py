from __future__ import annotations

import json
import socket
import uuid
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class GatewayClientError(RuntimeError):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class GatewayClient:
    """Small reconnect-safe client for the local TTG Device Gateway protocol."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 49321,
        *,
        timeout: float = 5.0,
    ) -> None:
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("the Phase 3 gateway client accepts loopback hosts only")
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._host = host
        self._port = port
        self._timeout = timeout

    def request(self, name: str, params: Mapping[str, Any] | None = None) -> Any:
        if not name:
            raise ValueError("gateway command name must be non-empty")
        command: dict[str, Any] = {"name": name}
        if params is not None:
            command["params"] = dict(params)
        payload = {
            "request_id": str(uuid.uuid4()),
            "command": command,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        with socket.create_connection(
            (self._host, self._port), timeout=self._timeout
        ) as stream:
            stream.settimeout(self._timeout)
            stream.sendall(encoded)
            response_bytes = _read_line(stream, limit=1024 * 1024)
        try:
            response = json.loads(response_bytes.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GatewayClientError(
                "PROTOCOL_ERROR", f"gateway returned invalid UTF-8 JSON: {exc}"
            ) from exc
        if response.get("request_id") != payload["request_id"]:
            raise GatewayClientError(
                "PROTOCOL_ERROR", "gateway response request_id does not match"
            )
        if response.get("ok") is not True:
            error = response.get("error")
            if not isinstance(error, dict):
                raise GatewayClientError(
                    "PROTOCOL_ERROR", "gateway returned an invalid error response"
                )
            raise GatewayClientError(
                str(error.get("code", "UNKNOWN_GATEWAY_ERROR")),
                str(error.get("message", "gateway request failed")),
            )
        return response.get("result")

    def health(self) -> dict[str, Any]:
        return _require_object(self.request("health"))

    def doctor(self) -> dict[str, Any]:
        return _require_object(self.request("doctor"))

    def snapshot(self) -> dict[str, Any]:
        return _require_object(self.request("snapshot"))

    def open_physical_session(self, fingerprint_sha256: str) -> dict[str, Any]:
        return _require_object(
            self.request(
                "open_physical_session",
                {"fingerprint_sha256": fingerprint_sha256},
            )
        )

    def get_physical_session(self, session_id: str) -> dict[str, Any]:
        return _require_object(
            self.request("get_physical_session", {"session_id": session_id})
        )

    def record_endpoint(
        self,
        session_id: str,
        endpoint_key: str,
        mode: str,
        transport: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _require_object(
            self.request(
                "record_endpoint",
                {
                    "endpoint_key": endpoint_key,
                    "mode": mode,
                    "payload": dict(payload or {}),
                    "session_id": session_id,
                    "transport": transport,
                },
            )
        )

    def open_operation(
        self, physical_session_id: str, request_sha256: str
    ) -> dict[str, Any]:
        return _require_object(
            self.request(
                "open_operation",
                {
                    "physical_session_id": physical_session_id,
                    "request_sha256": request_sha256,
                },
            )
        )

    def get_operation(self, operation_id: str) -> dict[str, Any]:
        return _require_object(
            self.request("get_operation", {"operation_id": operation_id})
        )

    def transition_operation(
        self, operation_id: str, stage: str
    ) -> dict[str, Any]:
        return _require_object(
            self.request(
                "transition_operation",
                {"operation_id": operation_id, "stage": stage},
            )
        )

    def resume_operation(self, operation_id: str) -> dict[str, Any]:
        return _require_object(
            self.request("resume_operation", {"operation_id": operation_id})
        )

    def register_provider(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        return _require_object(
            self.request("register_provider", {"manifest": dict(manifest)})
        )

    def publish_contract(
        self,
        component_id: str,
        contract: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _require_object(
            self.request(
                "publish_contract",
                {
                    "component_id": component_id,
                    "context": dict(context or {}),
                    "contract": dict(contract),
                },
            )
        )

    def verify_journal(self) -> dict[str, Any]:
        return _require_object(self.request("verify_journal"))

    def shutdown(self) -> dict[str, Any]:
        return _require_object(self.request("shutdown"))


def _read_line(stream: socket.socket, *, limit: int) -> bytes:
    data = bytearray()
    while True:
        chunk = stream.recv(4096)
        if not chunk:
            raise GatewayClientError(
                "PROTOCOL_ERROR", "gateway closed the connection before a response"
            )
        data.extend(chunk)
        if len(data) > limit:
            raise GatewayClientError(
                "PROTOCOL_ERROR", "gateway response exceeds one MiB"
            )
        newline = data.find(b"\n")
        if newline >= 0:
            return bytes(data[:newline])


def _require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GatewayClientError(
            "PROTOCOL_ERROR", "gateway result must be a JSON object"
        )
    return value

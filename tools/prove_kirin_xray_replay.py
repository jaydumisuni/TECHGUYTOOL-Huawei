from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.gateway_client import GatewayClient
from techguy_huawei.kirin_xray import PROVIDER_ID, publish_replay, render_replay
from tools.prove_gateway_reconnect import (
    RunningGateway,
    _free_port,
    _start_gateway,
    _stop_gateway,
    _terminate_gateway,
)

FIXTURES = (
    ROOT / "replay" / "kirin" / "p10_golden_workflow.json",
    ROOT / "replay" / "kirin" / "p30_main_version_mode_hazard.json",
)
_ALLOWED_CONTRACT_TYPES = {
    "physical_device_session",
    "endpoint_observation",
    "device_evidence",
    "device_twin",
}


def prove(binary: Path) -> dict[str, Any]:
    if not binary.is_file():
        raise FileNotFoundError(f"gateway binary not found: {binary}")

    deterministic: list[dict[str, Any]] = []
    rendered_by_scenario: dict[str, Any] = {}
    for fixture in FIXTURES:
        first = render_replay(fixture)
        second = render_replay(fixture)
        if first.canonical != second.canonical or first.sha256 != second.sha256:
            raise AssertionError(f"replay is not deterministic: {fixture.name}")
        rendered_by_scenario[first.scenario_id] = first
        deterministic.append(
            {
                "scenario_id": first.scenario_id,
                "fixture": fixture.relative_to(ROOT).as_posix(),
                "fixture_sha256": first.fixture_sha256,
                "bundle_sha256": first.sha256,
                "contract_count": len(first.contracts),
                "safety": first.safety,
            }
        )

    p10_explained = _p10_golden_workflow_explained(rendered_by_scenario)
    p30_explained = _p30_main_version_failure_explained(rendered_by_scenario)
    stock_fastboot_hazard_blocked = _premature_stock_fastboot_hazard_blocked(
        rendered_by_scenario
    )
    if not p10_explained:
        raise AssertionError("P10 golden workflow is not derived from replay evidence")
    if not p30_explained:
        raise AssertionError("P30 main-version failure is not derived from replay evidence")
    if not stock_fastboot_hazard_blocked:
        raise AssertionError("premature stock-Fastboot hazard is not derived as blocked")

    gateway_journal_verified = False
    gateway_restart_recovery = False
    with tempfile.TemporaryDirectory(prefix="ttg-kirin-xray-proof-") as temporary:
        database = Path(temporary) / "gateway.sqlite3"
        port = _free_port()
        first_process: RunningGateway | None = _start_gateway(binary, database, port)
        publications: list[dict[str, Any]] = []
        try:
            client = GatewayClient(port=port)
            health = client.health()
            if health.get("device_authority") != "none":
                raise AssertionError("Gateway expanded device authority")
            if health.get("xray_authority") != "read_only":
                raise AssertionError("Gateway changed Xray authority")

            for fixture in FIXTURES:
                publications.append(publish_replay(client, fixture))

            client.verify_journal()
            gateway_journal_verified = True
            snapshot = client.snapshot()
            _assert_snapshot(snapshot, publications)
            events = client.request("list_events", {"after_sequence": 0, "limit": 1000})
            _assert_contract_events(events, publications)
            _stop_gateway(first_process, client)
            first_process = None
        finally:
            if first_process is not None:
                _terminate_gateway(first_process)

        second_process: RunningGateway | None = _start_gateway(binary, database, port)
        try:
            client = GatewayClient(port=port)
            recovered = 0
            for publication in publications:
                session = client.get_physical_session(publication["physical_session_id"])
                if session.get("recovery_count", 0) < 1:
                    raise AssertionError("Gateway restart did not recover Xray session")
                recovered += 1
            gateway_restart_recovery = recovered == len(publications)
            client.verify_journal()
            gateway_journal_verified = gateway_journal_verified and True
            snapshot = client.snapshot()
            _assert_snapshot(snapshot, publications)
            _stop_gateway(second_process, client)
            second_process = None
        finally:
            if second_process is not None:
                _terminate_gateway(second_process)

    return {
        "schema": "techguytool-huawei.phase4-kirin-xray-proof.v1",
        "status": "PASS",
        "provider_id": PROVIDER_ID,
        "deterministic_replays": deterministic,
        "published_scenarios": [item["scenario_id"] for item in publications],
        "published_contract_count": sum(len(item["receipts"]) for item in publications),
        "gateway_restart_recovery": gateway_restart_recovery,
        "gateway_journal_verified": gateway_journal_verified,
        "p10_golden_workflow_explained": p10_explained,
        "p30_main_version_failure_explained": p30_explained,
        "premature_stock_fastboot_hazard_blocked": stock_fastboot_hazard_blocked,
        "write_authorized": False,
        "device_authority": "none",
        "xray_authority": "read_only",
    }


def _evidence_subjects(bundle: Any) -> dict[str, str]:
    return {
        str(contract["payload"]["subject_id"]): str(contract["payload"]["verdict"])
        for contract in bundle.contracts
        if contract.get("contract_type") == "device_evidence"
    }


def _p10_golden_workflow_explained(rendered: dict[str, Any]) -> bool:
    bundle = rendered.get("kirin-p10-golden-workflow-v1")
    if bundle is None:
        return False
    subjects = _evidence_subjects(bundle)
    reasons = set(bundle.safety.get("reason_codes", ()))
    return (
        subjects.get("p10-referenced-small-metadata-files") == "missing"
        and subjects.get("p10-complete-oeminfo-version-state") == "coherent"
        and subjects.get("p10-service-environment-retention") == "coherent"
        and bundle.safety.get("release_blocked") is True
        and {
            "COMPLETE_OEMINFO_WORKFLOW_REQUIRED",
            "SERVICE_ENVIRONMENT_MUST_BE_RETAINED",
        }
        <= reasons
    )


def _p30_main_version_failure_explained(rendered: dict[str, Any]) -> bool:
    bundle = rendered.get("kirin-p30-main-version-mode-hazard-v1")
    if bundle is None:
        return False
    subjects = _evidence_subjects(bundle)
    return (
        subjects.get("vog-l29-main-version") == "missing"
        and subjects.get("vog-l29-oeminfo-version-identity") == "missing"
        and subjects.get("vog-l29-vendor-country-state") == "contradictory"
        and subjects.get("vog-l29-cust-preload-package-metadata") == "observed"
    )


def _premature_stock_fastboot_hazard_blocked(rendered: dict[str, Any]) -> bool:
    bundle = rendered.get("kirin-p30-main-version-mode-hazard-v1")
    if bundle is None:
        return False
    subjects = _evidence_subjects(bundle)
    reasons = set(bundle.safety.get("reason_codes", ()))
    return (
        bundle.safety.get("release_blocked") is True
        and subjects.get("vog-l29-premature-stock-fastboot-hazard") == "observed"
        and "PREMATURE_STOCK_FASTBOOT_RESTORE_BLOCKED" in reasons
        and "SERVICE_MODE_REQUIRED_UNTIL_VERIFIED" in reasons
    )


def _assert_snapshot(
    snapshot: dict[str, Any], publications: list[dict[str, Any]]
) -> None:
    if snapshot.get("device_authority") != "none":
        raise AssertionError("snapshot expanded device authority")
    if snapshot.get("xray_authority") != "read_only":
        raise AssertionError("snapshot changed Xray authority")
    providers = snapshot.get("providers") or []
    matching = [item for item in providers if item.get("component_id") == PROVIDER_ID]
    if len(matching) != 1 or matching[0].get("device_access") != "read_only":
        raise AssertionError(f"Kirin Xray provider is not frozen read-only: {matching}")
    session_ids = {
        item.get("session_id") for item in (snapshot.get("physical_sessions") or [])
    }
    expected = {item["physical_session_id"] for item in publications}
    if not expected <= session_ids:
        raise AssertionError("snapshot lost an Xray physical session")


def _assert_contract_events(events: Any, publications: list[dict[str, Any]]) -> None:
    if not isinstance(events, list):
        raise AssertionError("Gateway list_events result is not an array")
    accepted = [event for event in events if event.get("event_type") == "contract_accepted"]
    expected_count = sum(len(item["receipts"]) for item in publications)
    if len(accepted) != expected_count:
        raise AssertionError(
            f"expected {expected_count} accepted contracts, found {len(accepted)}"
        )
    contract_types = {event.get("payload", {}).get("contract_type") for event in accepted}
    if not contract_types <= _ALLOWED_CONTRACT_TYPES:
        raise AssertionError(f"unexpected Xray contract type: {sorted(contract_types)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove deterministic Kirin Xray replay through the real TTG Device Gateway"
    )
    parser.add_argument("--gateway-bin", type=Path, required=True)
    args = parser.parse_args()
    result = prove(args.gateway_bin.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

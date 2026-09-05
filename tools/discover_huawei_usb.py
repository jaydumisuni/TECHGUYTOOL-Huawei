from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from techguy_huawei.gateway_client import GatewayClient, GatewayClientError  # noqa: E402
from techguy_huawei.physical_evidence import validate_proof_output_path  # noqa: E402
from techguy_huawei.windows_usb import UsbDiscoveryError, discover_windows_huawei_usb  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover Huawei USB/PnP state without modifying the device."
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--publish-gateway", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = discover_windows_huawei_usb()
        payload = report.to_dict()
        if args.publish_gateway and report.present:
            try:
                observation = GatewayClient().record_usb_discovery(payload)
                payload["gateway_publication"] = {
                    "status": "recorded",
                    "observation_id": observation.get("observation_id", ""),
                    "session_id": observation.get("session_id", ""),
                }
            except (GatewayClientError, OSError, ValueError) as exc:
                payload["gateway_publication"] = {
                    "status": "unavailable",
                    "error": str(exc),
                }
        encoded = json.dumps(payload, sort_keys=True, indent=2) + "\n"
        if args.output is not None:
            output = validate_proof_output_path(args.output, ROOT / "proof")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0
    except (OSError, UsbDiscoveryError, ValueError) as exc:
        print(f"USB_DISCOVERY_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

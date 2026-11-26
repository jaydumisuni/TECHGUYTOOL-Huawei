from __future__ import annotations

"""Per-action durable human log + machine record, separate from raw command evidence."""

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Callable
import re
import uuid

from .device_engine import DeviceSnapshot, EngineResult


UNAVAILABLE = "Unavailable (not reported by this mode)"
READ_FIELDS = (
    ("Model","model"),("Product name","product_name"),("Chipset","platform"),
    ("Interface","interface"),("Serial","serial"),("Android version","android_version"),
    ("EMUI version","emui_version"),("Build number","build_number"),
    ("Vendor / country","vendor_country"),("Main version","main_version"),
    ("Security patch","security_patch"),("Board","board_id"),
    ("Bootloader","bootloader_state"),("FRP state","frp_state"),
)

def device_read_lines(snapshot: DeviceSnapshot, result: EngineResult) -> list[str]:
    if not snapshot.connected:
        return [result.message]
    entries=[]
    for label,attr in READ_FIELDS:
        raw=str(getattr(snapshot,attr,"") or "").strip()
        if not raw or raw.casefold() in {"unknown","unverified","unavailable","huawei fastboot","huawei usb","android / adb"}:
            if attr!="interface":continue
        if attr=="product_name" and raw==snapshot.model:continue
        if raw:entries.append(f"{label}: {raw}")
    xray=(result.payload or {}).get("xray",{})
    for label,value in xray.get("details",{}).items():
        if label not in {"IMEI","IMEI 2","MEID","Build fingerprint","Kernel","Bootloader version","Firmware version","Variant","Active slot","Device codename"} and value is not None and str(value).strip():entries.append(f"{label}: {value}")
    if xray.get("status")!="BOUND":
        entries.append("Detailed identity: "+("not resolved in this mode" if xray.get("status")=="UNBOUND" else "X-Ray unavailable; basic device information only"))
    return entries or [result.message]


class ActionLog:
    """Owned entirely by the service worker; never writes from a QML callback."""

    def __init__(
        self,
        directory: Path,
        action_id: str,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        if not re.fullmatch(r"[a-z_]{2,64}", action_id):
            raise ValueError("Invalid action identifier")
        directory.mkdir(parents=True, exist_ok=True)
        self.started_local = datetime.now().astimezone()
        self.started_utc = self.started_local.astimezone(timezone.utc)
        self.started_at = perf_counter()
        self.action_id = action_id
        self.run_id = uuid.uuid4().hex
        self.progress = progress
        # One human-readable TXT per action, grouped by the customer's local date.
        # The run suffix prevents loss when two operations begin in one second.
        day_folder = directory / self.started_local.strftime("%Y-%m-%d")
        day_folder.mkdir(parents=True, exist_ok=True)
        stem = (
            f"{self.started_local:%Y-%m-%d_%H-%M-%S}_"
            f"{action_id.upper()}_{self.run_id[:8]}"
        )
        self.log_path = day_folder / (stem + ".txt")
        # Legacy property kept for UI API compatibility. There is no JSON sidecar.
        self.record_path = ""
        self.lines: list[str] = []
        self.add(f"Action: {action_id.replace('_', ' ').upper()}")
        self.add(f"Started: {self.started_local.isoformat()}")

    def add(self, line: str) -> None:
        safe = line.replace("\r", "").replace("\x00", "")
        for item in safe.split("\n"):
            self.lines.append(item)
            with self.log_path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(item + "\n")
            if self.progress is not None:
                try:
                    self.progress(item)
                except Exception:
                    # A broken UI progress consumer must not invalidate evidence.
                    pass

    def complete(
        self,
        result: EngineResult,
        snapshot: DeviceSnapshot | None = None,
    ) -> int:
        elapsed_ms = round((perf_counter() - self.started_at) * 1000)
        status = "OK" if result.ok else (
            "NO DEVICE" if result.health_state.value == "READY" else result.health_state.value.upper()
        )
        self.add(f"Result: {status} | {result.message}")
        self.add(f"Elapsed Time: {elapsed_ms} ms")
        # Raw command diagnostics remain in EvidenceJournal (different storage).
        # A user action produces only its own readable TXT report.
        return elapsed_ms

def full_device_report(snapshot: DeviceSnapshot, result: EngineResult) -> str:
    import json
    lines=device_read_lines(snapshot,result)
    xray=(result.payload or {}).get("xray",{})
    if xray.get("status")=="BOUND":
        # Structured evidence is available on demand rather than dumped into
        # the operator's main log. Keep it local; no telemetry publication.
        for heading,key in (("OBSERVED DETAILS","details"),("IDENTITY","identity"),("STORAGE","storage"),
                            ("FIRMWARE FINGERPRINT","firmware"),("PARTITION INVENTORY","partitions"),
                            ("DEVICE PROFILE","profile_match"),("CHALLENGER FINDINGS","challenges"),
                            ("DEEP DIAGNOSTICS","diagnostics"),
                            ("EVIDENCE CONFIDENCE","certification")):
            value=(result.payload or {}).get("partition_inventory",xray.get(key)) if key=="partitions" else xray.get(key)
            if value:
                lines.extend(["",heading,json.dumps(value,indent=2,ensure_ascii=False)])
    elif (result.payload or {}).get("partition_inventory"):
        lines.extend(["","PARTITION INVENTORY",json.dumps(result.payload["partition_inventory"],indent=2,ensure_ascii=False)])
    if xray.get("bundle"):lines.extend(["","Evidence bundle: "+xray["bundle"]])
    return "\n".join(lines)

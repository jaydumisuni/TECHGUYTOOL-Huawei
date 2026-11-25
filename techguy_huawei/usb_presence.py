"""Read-only hotplug observation, independent of any service-mode entry."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Presence:
    state: str
    fingerprint: str = ""
    pid: str = ""

def observe():
    from .windows_usb import collect_windows_usb_observations
    from .usb_discovery import discover_huawei_usb
    report=discover_huawei_usb(collect_windows_usb_observations())
    return Presence(report.state,report.fingerprint_sha256,report.pid)

class PresenceTracker:
    def __init__(self):
        self.previous=None

    def update(self,current):
        # Query failure is not a disconnection. Only a successful inventory
        # can replace the last known state.
        if current is None:return "unchanged"
        if self.previous==current:return "unchanged"
        previous=self.previous
        self.previous=current
        if current.state in {"no_huawei","multiple_huawei_devices"}:
            return "clear" if previous is not None or current.state=="multiple_huawei_devices" else "unchanged"
        return "scan"

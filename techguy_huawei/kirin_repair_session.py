"""Continue ordinary firmware repair when an authorized Fastboot route returns.

USB COM presence is observation only: it never authorizes a loader transfer,
a write, or a claim that temporary service Fastboot has been acquired.
"""
from __future__ import annotations
from threading import Event
import time
from subprocess import TimeoutExpired
from .firmware_flash import FlashError, _device
from .fastboot_identity import canonical_chipset

WAIT="KIRIN REPAIR WAIT:"
COM="KIRIN USB COM DETECTED:"
READY="KIRIN REPAIR READY:"

def wait_for_repair(binary, model, chipset, notify, cancel:Event, expected_serial="",
                    timeout=300, poll=1.0, probe_usb=None, probe_fastboot=None):
    if not model or not canonical_chipset(chipset).startswith(("kirin","hisi")):
        raise FlashError("Exact Kirin repair target required")
    if probe_usb is None:
        from .windows_usb import collect_windows_usb_observations
        from .usb_discovery import discover_huawei_usb
        probe_usb=lambda:discover_huawei_usb(collect_windows_usb_observations())
    if probe_fastboot is None:
        probe_fastboot=lambda:_device(binary,chipset,model)
    deadline=time.monotonic()+timeout
    previous=None
    saw_com=False
    while not cancel.is_set() and time.monotonic()<deadline:
        try:
            report=probe_usb()
            state=report.state
        except (OSError,RuntimeError,ValueError,TimeoutExpired):
            state="unknown"
        if state=="multiple_huawei_devices":
            status="multiple"
            message=(COM if saw_com else WAIT)+" Multiple Huawei devices detected; retain only the intended repair device."
        elif state=="huawei_usb_com_1_0":
            saw_com=True
            status="com"
            message=COM+" USB service interface detected. Waiting for an authorized repair interface."
        else:
            try:
                serial,product,actual=probe_fastboot()
                if (actual==model.upper() and
                    canonical_chipset(product)==canonical_chipset(chipset) and
                    (not expected_serial or expected_serial==serial)):
                    notify(READY+" "+model.upper()+" | Matching authorized Fastboot detected. Continuing package preflight.")
                    return serial
            except (FlashError,OSError,RuntimeError,ValueError,TimeoutExpired):
                pass
            status="transition" if saw_com else "waiting"
            message=(COM+" Waiting for the matching authorized repair interface." if saw_com else WAIT+" Connect the selected model using its authorized service interface.")
        if status!=previous:
            notify(message.replace(": ",": "+model.upper()+" | ",1))
            previous=status
        cancel.wait(poll)
    if cancel.is_set():raise FlashError("Repair interface wait cancelled; no firmware write started.")
    raise FlashError("Repair interface wait expired; no firmware write started.")

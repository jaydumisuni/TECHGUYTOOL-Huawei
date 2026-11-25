from types import SimpleNamespace
from threading import Event
import pytest
from techguy_huawei.kirin_repair_session import wait_for_repair, WAIT, COM, READY
from techguy_huawei.firmware_flash import FlashError

def sequence(*values):
    data=iter(values)
    def probe():
        value=next(data)
        if isinstance(value,Exception):raise value
        return value
    return probe

def state(value):return SimpleNamespace(state=value)

def test_wait_hides_reference_after_com_and_continues_only_matching_authorized_route():
    logs=[]
    usb=sequence(state("none"),state("huawei_usb_com_1_0"),state("none"),state("normal_fastboot"),state("normal_fastboot"))
    fb=sequence(FlashError("absent"),FlashError("absent"),
        ("WRONG","kirin659","ANE-LX1"),("SAME","kirin659","ANE-LX1"))
    result=wait_for_repair("mock","ANE-LX1","kirin659",logs.append,Event(),"SAME",timeout=2,poll=0,probe_usb=usb,probe_fastboot=fb)
    assert result=="SAME"
    assert logs[0].startswith(WAIT)
    assert any(x.startswith(COM) for x in logs)
    assert logs[-1].startswith(READY)
    assert sum(x.startswith(WAIT) for x in logs)==1

def test_multiple_devices_never_start_preflight():
    cancel=Event(); logs=[]
    def notify(message):
        logs.append(message);cancel.set()
    def forbidden():
        raise AssertionError("Fastboot must not be queried for ambiguous device cohort")
    with pytest.raises(FlashError,match="cancelled"):
        wait_for_repair("mock","ANE-LX1","kirin659",notify,cancel,timeout=1,poll=0,
            probe_usb=lambda:state("multiple_huawei_devices"),probe_fastboot=forbidden)
    assert "Multiple" in logs[0]

def test_cancel_when_com_observed_without_authorized_fastboot():
    cancel=Event();logs=[]
    def notify(message):
        logs.append(message);cancel.set()
    with pytest.raises(FlashError,match="cancelled"):
        wait_for_repair("mock","ANE-LX1","kirin659",notify,cancel,timeout=1,poll=0,
            probe_usb=lambda:state("huawei_usb_com_1_0"),probe_fastboot=lambda:pytest.fail("COM is not Fastboot"))
    assert logs[0].startswith(COM)

def test_wrong_model_or_chip_cannot_continue():
    logs=[]
    def notify(message):logs.append(message)
    with pytest.raises(FlashError,match="expired"):
        wait_for_repair("mock","ANE-LX1","kirin659",notify,Event(),timeout=.02,poll=.001,
            probe_usb=lambda:state("normal_fastboot"),probe_fastboot=lambda:("SAME","kirin659","ANE-LX2"))
    assert not any(x.startswith(READY) for x in logs)

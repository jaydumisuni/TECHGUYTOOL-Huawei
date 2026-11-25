"""Job-scoped EDL reconnect handling, independent of models and firmware.
A completed command is not repeated. An interrupted read may be retried;
a write with uncertain completion is never silently replayed.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import Event
import time
from subprocess import TimeoutExpired
import uuid
from .firmware_flash import FlashError

PREFIX="EDL RECONNECT REQUIRED:"
@dataclass
class Session:
    cancel: Event
    notify: object
    timeout: float=300
    poll: float=1.0

_session=ContextVar("edl_reconnect_session",default=None)

@contextmanager
def session(cancel,notify,timeout=300,poll=1.0):
    token=_session.set(Session(cancel,notify,timeout,poll))
    try:yield
    finally:_session.reset(token)

def _matches(serial,expected,expected_hash):
    return bool(serial) and (expected is None or serial==expected) and (expected_hash is None or sha256(serial.encode()).hexdigest()==expected_hash)

def ensure(probe,expected=None,expected_hash=None,stage="next stage"):
    """Wait only in an interactive service worker; otherwise fail promptly."""
    state=_session.get()
    def check():
        try:return probe()
        except (FlashError,OSError,TimeoutError,TimeoutExpired):return None
    serial=check()
    if _matches(serial,expected,expected_hash):return serial
    if state is None:raise FlashError("EDL target disconnected or changed.")
    state.notify(PREFIX+" Return the same phone to Qualcomm EDL (9008). Waiting at "+stage+".")
    deadline=time.monotonic()+state.timeout
    while True:
        if state.cancel.is_set():raise FlashError("EDL reconnect cancelled; completed stages and evidence retained.")
        if time.monotonic()>=deadline:raise FlashError("EDL reconnect timed out; completed stages and evidence retained.")
        serial=check()
        if _matches(serial,expected,expected_hash):
            state.notify("Same EDL device connected. Continuing "+stage+".")
            return serial
        state.cancel.wait(min(state.poll,max(0,deadline-time.monotonic())))

def disconnected(probe,expected):
    try:return probe()!=expected
    except (FlashError,OSError,TimeoutError,TimeoutExpired):return True

def run_stage(probe,expected,stage,argv,invoke,record):
    """Record every attempt; preserve incomplete read files before retrying."""
    ensure(probe,expected,stage=stage)
    state=_session.get()
    read_only=bool(argv) and argv[0]=="read" and len(argv)%3==0 and all(argv[i]=="read" for i in range(0,len(argv),3))
    attempt=0
    while True:
        attempt+=1
        try:
            code,log=invoke()
        except (OSError,TimeoutError,TimeoutExpired) as exc:
            code,log=1,str(exc)
        record(attempt,log)
        failed=bool(code) or any(line.startswith("ERR:") for line in log.splitlines())
        if not failed:return code,log
        # No retry for ordinary errors while the original target remains present.
        if state is None or not disconnected(probe,expected):return code,log
        ensure(probe,expected,stage=stage)
        if not read_only:
            raise FlashError("EDL returned after an interrupted "+stage+" command; completion is uncertain. Review retained evidence before any further write.")
        for i in range(2,len(argv),3):
            path=Path(argv[i])
            if path.is_file():
                path.replace(path.with_name(path.name+".interrupted-"+uuid.uuid4().hex[:8]))
        if attempt>=3:raise FlashError("Repeated interrupted read; evidence retained.")
        state.notify("Retrying interrupted read only: "+stage+".")

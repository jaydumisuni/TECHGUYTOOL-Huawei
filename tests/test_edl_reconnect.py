from threading import Event
from pathlib import Path
import pytest
from techguy_huawei.edl_reconnect import session,ensure,run_stage,PREFIX
from techguy_huawei.firmware_flash import FlashError

def sequence(*values):
    items=iter(values)
    def probe():
        x=next(items)
        if x is None:raise FlashError("No EDL device")
        return x
    return probe

def test_reconnect_same_target_no_completed_replay():
    events=[];called=[]
    with session(Event(),events.append,timeout=1,poll=0):
        code,log=run_stage(sequence(None,"WRONG","SAME"),"SAME","backup",["read","0/0+1","unused"],
            lambda:(called.append("read") or 0,"OK"),lambda *_:None)
    assert code==0 and called==["read"]
    assert events[0].startswith(PREFIX) and "Same EDL" in events[-1]

def test_interrupted_read_retained_and_retried(tmp_path):
    events=[];records=[];dest=tmp_path/"gpt.bin";attempt=[]
    def invoke():
        attempt.append(1)
        dest.write_bytes(b"partial" if len(attempt)==1 else b"complete")
        return (1,"ERR: disconnected") if len(attempt)==1 else (0,"OK")
    with session(Event(),events.append,timeout=1,poll=0):
        code,_=run_stage(sequence("SAME",None,None,"SAME"),"SAME","GPT read",["read","0/0+1",str(dest)],invoke,
            lambda n,log:records.append((n,log)))
    assert code==0 and dest.read_bytes()==b"complete"
    assert next(tmp_path.glob("gpt.bin.interrupted-*")).read_bytes()==b"partial"
    assert len(records)==2 and len(attempt)==2

def test_interrupted_write_not_replayed():
    called=[];events=[]
    with session(Event(),events.append,timeout=1,poll=0):
        with pytest.raises(FlashError,match="completion is uncertain"):
            run_stage(sequence("SAME",None,None,"SAME"),"SAME","program",["program.xml"],
                lambda:(called.append(1) or 1,"ERR: disconnected"),lambda *_:None)
    assert called==[1] and any(x.startswith(PREFIX) for x in events)

def test_cancel_and_timeout():
    e=Event()
    def notify(msg):e.set()
    with session(e,notify,timeout=1,poll=0):
        with pytest.raises(FlashError,match="cancelled"):ensure(lambda:None,expected="SAME")
    with session(Event(),lambda _:None,timeout=0,poll=0):
        with pytest.raises(FlashError,match="timed out"):ensure(lambda:"WRONG",expected="SAME")
    with pytest.raises(FlashError,match="disconnected"):ensure(lambda:None,expected="SAME")

from types import SimpleNamespace
import pytest
from techguy_huawei.live_service import LiveHuaweiService,ServiceUnavailable

def test_live_service_keeps_first_verified_transport():
    observed=iter(["FIRST","SECOND"])
    def run(action,argv):
        return SimpleNamespace(returncode=0,stdout=next(observed)+" fastboot"),[]
    engine=SimpleNamespace(_tool=lambda name:"fastboot",_run=run)
    service=LiveHuaweiService(engine)
    assert service._connection()==("fastboot","FIRST")
    with pytest.raises(ServiceUnavailable,match="changed"):
        service._connection()

def test_existing_session_cannot_switch_target():
    engine=SimpleNamespace(_tool=lambda name:"fastboot",_run=lambda *a:(SimpleNamespace(returncode=0,stdout="OTHER fastboot"),[]))
    service=LiveHuaweiService(engine,expected_serial="EXPECTED")
    with pytest.raises(ServiceUnavailable,match="changed"):
        service._connection()

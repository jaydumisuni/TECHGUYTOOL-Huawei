"""Pinout gallery is view-only; do not equate browsing with device authorization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from techguy_huawei.pinout_provider import BASE_URL, PinoutProvider, PinoutProviderError


@pytest.fixture
def provider(tmp_path, monkeypatch):
    p=PinoutProvider(tmp_path/"cache")
    items=[
        {"id":"a"*20,"brand":"Huawei","model":"P30 Pro","type":"test-point",
         "images":[{"id":"1"*24,"url":"/images/"+"1"*24+".webp"}]},
        {"id":"b"*20,"brand":"Huawei","model":"P30 Pro 2","type":"test-point",
         "images":[{"id":"2"*24,"url":"/images/"+"2"*24+".webp"}]},
        {"id":"c"*20,"brand":"Honor","model":"8X","type":"test-point",
         "images":[{"id":"3"*24,"url":"/images/"+"3"*24+".webp"}]},
        {"id":"d"*20,"brand":"Huawei","model":"P30 Pro","type":"isp-pinout",
         "images":[{"id":"4"*24,"url":"/images/"+"4"*24+".webp"}]},
    ]
    seen=[]
    def fetch(url,*,max_bytes,mime):
        seen.append((url,mime))
        if url==BASE_URL+"catalog.json":
            return json.dumps({"records":items}).encode("utf-8")
        if url==BASE_URL+"images/"+"2"*24+".webp":
            return b"RIFF"+b"\x18\x00\x00\x00"+b"WEBPVP8 "+b"\x00"*24
        raise AssertionError("Unexpected image fetch: "+url)
    monkeypatch.setattr(p,"_fetch",fetch)
    return p,seen


def test_browse_returns_huawei_testpoint_catalog_metadata_only(provider):
    p,seen=provider
    d=p.browse("Huawei","test-point")
    assert d["browse_gallery"] is True
    assert d["result_count"]==2
    assert d["exact_count"]==0 and d["auto_select_allowed"] is False
    assert [x["model"] for x in d["results"]]==["P30 Pro","P30 Pro 2"]
    assert all(x["exact"] is False for x in d["results"])
    assert seen==[(BASE_URL+"catalog.json","application/json")]


def test_honor_and_isp_catalogues_remain_separate(provider):
    p,_=provider
    assert [x["model"] for x in p.browse("Honor","test-point")["results"]]==["8X"]
    assert len(p.browse("Huawei","isp-pinout")["results"])==1


def test_manual_browse_image_remains_catalogue_bound_and_cached(provider,monkeypatch):
    p,_=provider
    d=p.browse("Huawei","test-point")
    record=next(x for x in d["results"] if x["model"]=="P30 Pro 2")
    image=p.fetch_image(record["id"],record["images"][0]["id"])
    assert image["model"]=="P30 Pro 2"
    assert image["record_id"]==record["id"]
    assert image["sha256"]==hashlib.sha256(
        (p.image_cache/(record["images"][0]["id"]+".webp")).read_bytes()
    ).hexdigest()
    monkeypatch.setattr(p,"_fetch",lambda *_a,**_kw: (_ for _ in ()).throw(AssertionError("network needed")))
    assert p.fetch_image(record["id"],record["images"][0]["id"])["sha256"]==image["sha256"]
    with pytest.raises(PinoutProviderError,match="does not belong"):
        p.fetch_image("a"*20,"2"*24)


def test_browse_rejects_unsupported_brand_or_type(provider):
    p,_=provider
    with pytest.raises(PinoutProviderError):
        p.browse("","test-point")
    with pytest.raises(PinoutProviderError):
        p.browse("Huawei","other")


def test_complete_huawei_and_honor_catalogue_is_not_truncated(tmp_path,monkeypatch):
    p=PinoutProvider(tmp_path/"cache")
    records=[]
    for brand,count in (("Huawei",522),("Honor",213)):
        for i in range(count):
            records.append({
                "id":f"{i:020x}" if brand=="Huawei" else f"{10000+i:020x}",
                "brand":brand, "model":f"Nova sample {i:03d}",
                "type":"test-point", "aliases":[],
                "images":[{"id":f"{i:024x}" if brand=="Huawei" else f"{10000+i:024x}",
                           "url":"https://pinout.thetechguyds.com/images/"+
                                 (f"{i:024x}" if brand=="Huawei" else f"{10000+i:024x}")+".webp"}],
            })
    monkeypatch.setattr(p,"catalog",lambda:(records,False))
    h=p.browse("Huawei","test-point")
    o=p.browse("Honor","test-point")
    assert len(h["results"])==522 and h["result_count"]==522
    assert len(o["results"])==213 and o["result_count"]==213
    assert h["results"][-1]["model"]=="Nova sample 521"
    assert o["results"][-1]["model"]=="Nova sample 212"
    hs=p.search("Huawei","Nova sample","test-point")
    assert hs["result_count"]==522 and len(hs["results"])==522

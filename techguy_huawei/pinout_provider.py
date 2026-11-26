from __future__ import annotations

"""Trusted read-only pinout catalogue and image cache.

The public finder is a source of reference diagrams, NOT authority to select
physical test points or perform recovery writes. Exact device-code matching
is required for automatic selection. Network/file operations stay in worker
threads; this module has no Qt or device-control dependency.
"""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError
import json
import re
import time
import unicodedata

BASE_URL = "https://pinout.thetechguyds.com/"
CATALOG_URL = BASE_URL + "catalog.json"
IMAGE_PATH = re.compile(r"^/images/([a-f0-9]{24})\.webp$")
IDENTIFIER = re.compile(r"^[a-f0-9]{20,32}$")
PINOUT_TYPES = frozenset({"test-point", "isp-pinout"})
MAX_CATALOG_BYTES = 4 * 1024 * 1024
MAX_IMAGE_BYTES = 16 * 1024 * 1024
CATALOG_REFRESH_SECONDS = 6 * 3600


class PinoutProviderError(RuntimeError):
    pass


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


class SameOriginRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urlsplit(newurl)
        if parts.scheme != "https" or parts.netloc.lower() != "pinout.thetechguyds.com":
            raise PinoutProviderError("Pinout redirect is outside the trusted origin.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PinoutProvider:
    def __init__(self, cache_root: Path, *, opener=None, ttl: int = CATALOG_REFRESH_SECONDS):
        self.cache_root = Path(cache_root)
        self.catalog_cache = self.cache_root / "catalog.json"
        self.image_cache = self.cache_root / "images"
        self.opener = opener or build_opener(SameOriginRedirects())
        self.ttl = ttl

    def _fetch(self, url: str, *, max_bytes: int, mime: str) -> bytes:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc.lower() != "pinout.thetechguyds.com":
            raise PinoutProviderError("Remote resource is not on the trusted pinout site.")
        req = Request(url, headers={"User-Agent": "TECHGUYTOOL-Huawei-Pinouts/1.0", "Accept": mime})
        try:
            with self.opener.open(req, timeout=12) as response:
                final = urlsplit(response.geturl())
                if final.scheme != "https" or final.netloc.lower() != "pinout.thetechguyds.com":
                    raise PinoutProviderError("Pinout resource redirected to another host.")
                reported_type = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
                if reported_type != mime:
                    raise PinoutProviderError("Pinout server returned an unexpected content type.")
                data = response.read(max_bytes + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise PinoutProviderError(f"Pinout site unavailable: {type(exc).__name__}") from exc
        if not data or len(data) > max_bytes:
            raise PinoutProviderError("Pinout response is empty or exceeds the size limit.")
        return data

    @staticmethod
    def _validated_records(raw: bytes) -> list[dict]:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise PinoutProviderError("Invalid pinout catalogue JSON.") from exc
        records = payload if isinstance(payload, list) else payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list) or len(records) > 50000:
            raise PinoutProviderError("Unexpected pinout catalogue format.")
        valid: list[dict] = []
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                continue
            rid = str(record.get("id", ""))
            brand = str(record.get("brand", "")).strip()
            model = str(record.get("model", "")).strip()
            kind = record.get("type")
            if not IDENTIFIER.fullmatch(rid) or rid in seen or not brand or not model or kind not in PINOUT_TYPES:
                continue
            images = []
            for im in record.get("images", []) if isinstance(record.get("images", []), list) else []:
                if not isinstance(im, dict):
                    continue
                url = str(im.get("url", ""))
                iid = str(im.get("id", ""))
                match = IMAGE_PATH.fullmatch(url)
                if match and iid == match.group(1):
                    images.append({"id": iid, "url": urljoin(BASE_URL, url)})
            if not images:
                continue
            aliases = [str(a)[:160] for a in record.get("aliases", []) if isinstance(a, str)] if isinstance(record.get("aliases", []), list) else []
            valid.append({
                "id": rid, "type": kind, "brand": brand, "model": model,
                "aliases": aliases[:25], "images": images[:30],
                "protocols": [str(x) for x in record.get("protocols", []) if isinstance(x, str)][:10],
            })
            seen.add(rid)
        if not valid:
            raise PinoutProviderError("No valid pinout images in catalogue.")
        return valid

    def catalog(self) -> tuple[list[dict], bool]:
        if self.catalog_cache.is_file():
            age = time.time() - self.catalog_cache.stat().st_mtime
            if self.ttl > 0 and 0 <= age < self.ttl:
                try:
                    return self._validated_records(self.catalog_cache.read_bytes()), False
                except (OSError, PinoutProviderError):
                    pass
        try:
            raw = self._fetch(CATALOG_URL, max_bytes=MAX_CATALOG_BYTES, mime="application/json")
            records = self._validated_records(raw)
            self.cache_root.mkdir(parents=True, exist_ok=True)
            temporary = self.catalog_cache.with_suffix(".json.tmp")
            temporary.write_bytes(raw)
            temporary.replace(self.catalog_cache)
            return records, False
        except PinoutProviderError:
            if self.catalog_cache.is_file():
                try:
                    return self._validated_records(self.catalog_cache.read_bytes()), True
                except (OSError, PinoutProviderError):
                    pass
            raise

    @staticmethod
    def _quality(query: str, record: dict) -> str:
        q = _norm(query)
        model = _norm(record["model"])
        if q == model:
            return "exact_model"
        if q in {_norm(alias) for alias in record["aliases"]}:
            return "exact_alias"
        # A short model code like VOG-AL00 may be suffixed to the model title.
        # The suffix prevents VOG-AL00 from picking "VOG AL00 2".
        if re.fullmatch(r"[a-z]{3} [a-z0-9]{2,7}", q) and model.endswith(" " + q):
            return "exact_device_code"
        if len(q) >= 3 and (q in model or q in " ".join(_norm(a) for a in record["aliases"])):
            return "browse_only"
        return ""

    def browse(self, brand: str, kind: str) -> dict:
        """Initial image-library catalogue listing (metadata only).

        Browsing a pinout is not a device match or permission to flash it.
        Fetching an image still requires a catalogue-bound record/image pair.
        """
        if not brand or len(brand) > 80 or kind not in PINOUT_TYPES:
            raise PinoutProviderError("Brand and pinout type are required.")
        records, stale = self.catalog()
        matched = [r for r in records if _norm(r["brand"]) == _norm(brand) and r["type"] == kind]
        matched.sort(key=lambda r: (r["model"].casefold(), r["id"]))
        return {
            "source": BASE_URL,
            "type": kind,
            "brand": brand,
            "query": "",
            "browse_gallery": True,
            "stale_catalog": stale,
            "exact_count": 0,
            "auto_select_allowed": False,
            # Return every record in the selected category. QML's ListView
            # virtualizes delegates; images remain on-demand, not bulk fetched.
            "results": [{**r, "exact": False, "match_quality": "browse_only"}
                        for r in matched],
            "result_count": len(matched),
        }

    def search(self, brand: str, query: str, kind: str) -> dict:
        if not brand or len(brand) > 80 or not query or len(query) > 160 or kind not in PINOUT_TYPES:
            raise PinoutProviderError("Brand, model and pinout type are required.")
        records, stale = self.catalog()
        matched = []
        for record in records:
            if _norm(record["brand"]) != _norm(brand) or record["type"] != kind:
                continue
            quality = self._quality(query, record)
            if not quality:
                continue
            matched.append({**record, "match_quality": quality, "exact": quality != "browse_only"})
        matched.sort(key=lambda r: (
            1 if r["match_quality"] == "browse_only" else 0,
            0 if r["match_quality"] == "exact_model" else 1,
            r["model"].lower(),
        ))
        exact_count = sum(record["exact"] for record in matched)
        return {
            "source": BASE_URL,
            "type": kind,
            "brand": brand,
            "query": query,
            "stale_catalog": stale,
            "exact_count": exact_count,
            "auto_select_allowed": exact_count == 1,
            # All matching Huawei/Honor models remain searchable; QML
            # ListView virtualizes large results without truncating them.
            "results": matched,
            "result_count": len(matched),
        }

    def fetch_image(self, record_id: str, image_id: str) -> dict:
        if not IDENTIFIER.fullmatch(record_id) or not IMAGE_PATH.fullmatch(f"/images/{image_id}.webp"):
            raise PinoutProviderError("Invalid pinout record or image identifier.")
        records, stale = self.catalog()
        record = next((r for r in records if r["id"] == record_id), None)
        if record is None:
            raise PinoutProviderError("Pinout record was not found in the trusted catalogue.")
        image = next((i for i in record["images"] if i["id"] == image_id), None)
        if image is None:
            raise PinoutProviderError("Image does not belong to the requested pinout record.")
        target = self.image_cache / f"{image_id}.webp"
        data = b""
        if target.is_file():
            data = target.read_bytes()
        else:
            data = self._fetch(image["url"], max_bytes=MAX_IMAGE_BYTES, mime="image/webp")
        if not (len(data) >= 16 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise PinoutProviderError("Downloaded pinout is not a valid WebP image.")
        if len(data) > MAX_IMAGE_BYTES:
            raise PinoutProviderError("Pinout image exceeds the size limit.")
        if not target.is_file():
            self.image_cache.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(".webp.tmp")
            tmp.write_bytes(data)
            tmp.replace(target)
        return {
            "record_id": record_id,
            "image_id": image_id,
            "brand": record["brand"],
            "model": record["model"],
            "type": record["type"],
            "source_url": image["url"],
            "local_url": target.resolve().as_uri(),
            "sha256": sha256(data).hexdigest(),
            "bytes": len(data),
            "stale_catalog": stale,
            "cached": True,
        }

"""Physically observed Cannes CAZ-AL10 factory-to-stock recipe.

Scoped to the exact B077 factory and B175 all/cn artifacts; never selected for
other models or generic firmware. The historical evidence is not live authority.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import os
import re
import shutil
import time
import uuid

from .firmware_flash import FlashError, _digest, _exec, _unique_device
from .qualcomm_board import build_plan, BoardPlanError, dry_run

MODEL = "CAZ-AL10"
CHIPSET = "msm8953"
BOARD_FINGERPRINT = "7c3c34336477284a4f108f956d17b7b6d19aea19190b2443cdec74084a4da8f7"
BOARD_EXCLUDED = frozenset({"oeminfo", "fsg", "modemst1", "modemst2", "sec", "persist"})
BASE_SHA = "b3b51ec262d7556acae37255b2a0b291c85bf5fdc3ff3a4cb6e42777a14332b4"
REGION_SHA = "ae86324cc9ab9a916fe9abfb6641a8ad955d9db946d18231ccff7aabf39a01c5"
REGION_REL = Path("all/cn/update_data_all_cn.app")
# Exact recovered offsets, payload digests and verified expanded/partition
# sizes, in the order physically acknowledged on KRATOS.
ROWS = (
    ("recovery", "base", 189756768, 42781996, 42781996, 83886080, "ab8e3547743f0314f5529c9b38ccf2adba8f51d20a8793c37d1949292db7f1c4"),
    ("system", "base", 276916124, 3224118244, 3879493632, 3879731200, "4c3676dc1eef398ca9cf86b2c72f004553ad00d0c64015062644f1c25e82b5aa"),
    ("cust", "base", 3658510078, 226637820, 536838144, 536870912, "4a24af318f9532a3bfcd895b31ea1e454db75f83ec06c872f903f12668dd1312"),
    ("modem", "base", 2435438, 167772160, 167772160, 167772160, "c657b13cc79eaa36794b1541ae1632d86a84806797fdfe661addc3a25844104c"),
    ("erecovery", "base", 232559752, 42781996, 42781996, 83886080, "ab8e3547743f0314f5529c9b38ccf2adba8f51d20a8793c37d1949292db7f1c4"),
    ("boot", "base", 3891566002, 34037032, 34037032, 83886080, "8668f7a15f994eed1adb4d2450eec99f6c80515459aa323478c22d4f67dba758"),
    ("cache", "base", 3885151124, 6398160, 268435456, 268435456, "2f50ee4f1b9ae8c03422c1342d2a7bded0b2385f908343ba3f0e7448c010acce"),
    ("userdata", "region", 283692, 511708764, 4294967296, 57050906112, "c47c33dde1a788dd00cd2da4cfcb93068de38289983346b9d936a26256be4676"),
)
RECIPE = "caz-al10-b077-to-b175-all-cn"
KNOWLEDGE = "huawei.caz-al10.msm8953.board-stock-recovery-20261125"


def matches_target(model: str, chipset: str) -> bool:
    return model.strip().upper() == MODEL and chipset.strip().casefold() in {"", CHIPSET}


def board_preview(rawprogram: Path, qdl: Path | None = None) -> dict:
    """Inspect exact recovered board package; optional QDL no-device dry run."""
    if rawprogram.name != "rawprogram_unsparse.xml":
        raise FlashError("Select the extracted rawprogram_unsparse.xml from the factory firehorseimage directory.")
    try:
        plan = build_plan(rawprogram.parent, rawprogram.name, "patch0.xml", "prog_emmc_firehose.mbn")
    except (BoardPlanError, OSError) as exc:
        raise FlashError(str(exc)) from exc
    if plan["fingerprint"] != BOARD_FINGERPRINT:
        raise FlashError("Factory package differs from the physically demonstrated B077 package.")
    ops = [row for row in plan["operations"] if row["filename"] and row["label"].casefold() not in BOARD_EXCLUDED]
    if len(ops) != 150:
        raise FlashError("Unexpected board operation count.")
    result = {"recipe": RECIPE, "sleeper_knowledge": KNOWLEDGE, "model": MODEL,
              "chipset": CHIPSET, "mode": "Board Firmware", "partitions": [
                  {"partition": row["label"], **row} for row in ops],
              "excluded": sorted(BOARD_EXCLUDED), "board_plan_fingerprint": plan["fingerprint"],
              "preflight_only": True, "write_authorized": False,
              "qualification": "PHYSICAL_RECIPE_PROVEN_NATIVE_DISPATCH_PENDING",
              "qdl_available": bool(qdl), "no_reboot": False}
    if qdl:
        result["dry_run"] = dry_run(qdl, rawprogram.parent, plan)["status"]
    # No confirmation fingerprint until the native staged backup/write provider
    # is actually available. Preview must never authorize the raw XML writes.
    return result


def _stock_device(fastboot: str) -> str:
    serial = _unique_device(fastboot)
    code, product = _exec(fastboot, ["-s", serial, "getvar", "product"])
    if code or "FAILED" in product.upper() or not re.search(r"\bproduct:\s*MSM8953\b", product, re.I):
        raise FlashError("CAZ-AL10 stock stage requires the MSM8953 factory Fastboot device.")
    code, model = _exec(fastboot, ["-s", serial, "oem", "get-product-model"])
    if code or "FAILED" in model.upper() or not re.search(r"\bCAZ-AL10\b", model, re.I):
        raise FlashError("Live product model is not CAZ-AL10.")
    code, state = _exec(fastboot, ["-s", serial, "getvar", "all"])
    if code or "FAILED" in state.upper() or not re.search(r"\brescue\s*:\s*(?:rescue\s*)?0\.3\b", state, re.I):
        raise FlashError("Factory rescue Fastboot signature not observed; perform the board stage first.")
    code, size = _exec(fastboot, ["-s", serial, "getvar", "partition-size:system"])
    m = re.search(r"partition-size:system\s*:\s*(0x[0-9a-f]+)\b", size, re.I)
    if code or "FAILED" in size.upper() or not m or int(m.group(1),16) != ROWS[1][5]:
        raise FlashError("Factory system geometry does not match the proven B077 layout.")
    return serial


def staging_root(evidence: Path) -> Path:
    setting = os.environ.get("TTG_HUAWEI_STAGING_DIR", "").strip()
    root = Path(setting).expanduser().resolve() if setting else evidence.resolve()
    root.mkdir(parents=True, exist_ok=True)
    need = max(row[3] for row in ROWS) + 512 * 1024**2
    if shutil.disk_usage(root).free < need:
        raise FlashError(f"Stock stage requires {need} free bytes for its largest image. Select a project-owned staging volume via TTG_HUAWEI_STAGING_DIR.")
    return root


def stock_plan(package: str, model: str, chipset: str, mode: str,
               fastboot: str, evidence: Path) -> dict:
    if not matches_target(model, chipset) or mode != "Repair":
        raise FlashError("This exact CAZ-AL10 stock recovery is available in Repair mode.")
    base = Path(package).expanduser().resolve()
    region = base.parent / REGION_REL
    if base.name.upper() != "UPDATE.APP" or not base.is_file() or not region.is_file():
        raise FlashError("Select B175 dload/UPDATE.APP with all/cn/update_data_all_cn.app alongside it.")
    if base.stat().st_size != 3925603036 or region.stat().st_size != 511992456:
        raise FlashError("B175 package length mismatch.")
    if _digest(base) != BASE_SHA or _digest(region) != REGION_SHA:
        raise FlashError("B175 or all/cn package digest differs from the physically proven release.")
    serial = _stock_device(fastboot)
    root = staging_root(evidence)
    paths = {"base": base, "region": region}
    ops = [{"partition": part, "source": str(paths[source]), "offset": off,
            "size": size, "expanded_size": expanded, "partition_size": capacity,
            "sha256": digest} for part, source, off, size, expanded, capacity, digest in ROWS]
    payload = {"recipe": RECIPE, "sleeper_knowledge": KNOWLEDGE,
               "model": MODEL, "chipset": CHIPSET, "mode": mode,
               "device_reported_model": MODEL, "serial_hash": sha256(serial.encode()).hexdigest(),
               "source_path": str(base), "staging_root": str(root), "partitions": ops,
               "excluded": ["factory boot chain", "GPT", *sorted(BOARD_EXCLUDED)],
               "preflight_only": True, "write_authorized": False, "no_reboot": True,
               "userdata_replaced": True, "factory_boot_chain_retained": True}
    payload["fingerprint"] = sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return payload


def _acknowledged(part: str, code: int, output: str) -> bool:
    if code or "FAILED" in output.upper():
        return False
    target = re.escape(part)
    writes = re.findall(r"Writing\s+'"+target+r"'\s+OKAY\b", output, re.I)
    sparse = re.findall(r"Sending sparse\s+'"+target+r"'\s+(\d+)/(\d+).*?OKAY\b", output, re.I)
    if sparse:
        total = int(sparse[0][1])
        return total > 0 and len(writes) == total and [(int(a),int(b)) for a,b in sparse] == [(i,total) for i in range(1,total+1)]
    return len(writes) == 1


def stock_apply(package: str, model: str, chipset: str, mode: str, fastboot: str,
                fingerprint: str, evidence: Path, progress) -> dict:
    current = stock_plan(package,model,chipset,mode,fastboot,evidence)
    if not fingerprint or current["fingerprint"] != fingerprint:
        raise FlashError("Stock recovery plan changed; inspect and confirm again.")
    serial = _stock_device(fastboot)
    if sha256(serial.encode()).hexdigest() != current["serial_hash"]:
        raise FlashError("The connected Fastboot device changed.")
    evidence.mkdir(parents=True,exist_ok=True)
    run_id = uuid.uuid4().hex
    path = evidence / ("caz-stock-"+run_id+".json")
    root = Path(current["staging_root"])
    report = {"recipe": RECIPE,"fingerprint": fingerprint,"status":"RUNNING",
              "operations":[],"no_reboot":True,"boot_verified":False,
              "factory_boot_chain_retained":True,"userdata_replaced":True}
    def checkpoint():
        temp=path.with_suffix(".tmp")
        temp.write_text(json.dumps(report,indent=2),encoding="utf8")
        temp.replace(path)
    checkpoint()
    try:
        for op in current["partitions"]:
            part=op["partition"]
            if _unique_device(fastboot) != serial:
                raise FlashError("Device changed or detached.")
            if shutil.disk_usage(root).free < op["size"] + 512*1024**2:
                raise FlashError("Insufficient staging storage.")
            image=root/("caz-"+run_id+"-"+part+".img")
            progress("Extracting verified "+part)
            h=sha256()
            with Path(op["source"]).open("rb") as src, image.open("xb") as dst:
                src.seek(op["offset"])
                left=op["size"]
                while left:
                    block=src.read(min(left,8*1024**2))
                    if not block:
                        raise FlashError("Stock payload truncated.")
                    dst.write(block);h.update(block);left-=len(block)
            if h.hexdigest()!=op["sha256"]:
                raise FlashError("Stock image digest mismatch: "+part)
            if _unique_device(fastboot)!=serial:
                raise FlashError("Device changed before write.")
            code, output=_exec(fastboot,["-s",serial,"-S","256M","flash",part,str(image)],timeout=7200)
            ok=_acknowledged(part,code,output)
            report["operations"].append({"partition":part,"sha256":op["sha256"],"exit_code":code,"acknowledged":ok,"output":output})
            checkpoint()
            if not ok:
                raise FlashError("Fastboot did not acknowledge all writes for "+part+"; staged image retained.")
            image.unlink()
            progress("Acknowledged "+part)
        report["status"]="WRITES_COMPLETE_NO_REBOOT"
    except Exception as exc:
        report["status"]="STOPPED_ON_ERROR"
        report["error"]=str(exc)
        checkpoint()
        raise
    checkpoint()
    return {"status":report["status"],"completed":len(report["operations"]),
            "evidence_path":str(path),"no_reboot":True,"boot_verified":False,
            "userdata_replaced":True,"factory_boot_chain_retained":True}

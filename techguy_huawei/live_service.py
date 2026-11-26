from __future__ import annotations

"""Read-first Huawei service bridge for the existing desktop action registry.

It intentionally exposes NO destructive Fastboot command. Writes are delegated
only to a separately certified, device-bound executor, not to a GUI button.
"""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from .fastboot_identity import model_from_build, lock_state, product_from_response
from .action_health import ActionState
from .device_engine import DeviceEngine, EngineResult

_VOG_TARGET = "VOG-L29 10.0.0.186(C185E8R5P1)"
_C185_FILES = {
    "update_sd_base.zip": 4308716151,
    "update_sd_cust_VOG-L29_hw_meafnaf.zip": 37292,
    "update_sd_preload_VOG-L29_hw_meafnaf_R5.zip": 251722738,
}
# Original package fingerprints recovered from the frozen AL00->L29 C185
# project manifest. Matching lengths alone is not sufficient for preflight.
_C185_SHA256 = {
    "update_sd_base.zip": "0d1ee806b39fd64fd63ed6d2f83018d0aa7725ddf1f888d865c89fa1b17ee885",
    "update_sd_cust_VOG-L29_hw_meafnaf.zip": "b8ab9b6d098c679b23eb2a0ba9af052cb32f2078f21658111fe7d0ae88d4cb49",
    "update_sd_preload_VOG-L29_hw_meafnaf_R5.zip": "a7c135b34462b7342bba04c0e66d571876f238d7a6400a2d566c8c85eae2258a",
}


def sha256_file(file: Path) -> str:
    digest = sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()




@dataclass(frozen=True)
class Identity:
    serial: str
    product: str
    build: str
    bootinfo: str
    vendorcountry: str
    rescue_phoneinfo: str

    @property
    def model(self) -> str:
        return model_from_build(self.build) or "UNKNOWN"


class ServiceUnavailable(RuntimeError):
    pass


class LiveHuaweiService:
    def __init__(self, engine: DeviceEngine, expected_serial: str = "") -> None:
        self.engine = engine
        self.expected_serial = expected_serial
        self._session_serial = expected_serial

    def _connection(self) -> tuple[str, str]:
        fastboot = self.engine._tool("fastboot")
        if not fastboot:
            raise ServiceUnavailable("Fastboot executable is missing from approved platform tools.")
        result, _ = self.engine._run("huawei_device_inventory", [fastboot, "devices"])
        rows = DeviceEngine._fastboot_rows(result.stdout)
        if result.returncode or len(rows) != 1:
            raise ServiceUnavailable(
                "Exactly one Fastboot device is required; found " + str(len(rows)) + "."
            )
        serial=rows[0].split()[0]
        if self._session_serial and serial!=self._session_serial:
            raise ServiceUnavailable("The connected Fastboot device changed during the service session.")
        self._session_serial=serial
        return fastboot, serial

    def _query(self, binary: str, serial: str, *arguments: str) -> str:
        result, _ = self.engine._run(
            "huawei_service_read",
            [binary, "-s", serial, *arguments],
        )
        content = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode or "FAILED (" in content or "fastboot: error:" in content:
            raise ServiceUnavailable("Read-only Fastboot query failed: " + " ".join(arguments))
        return content

    def _optional_query(self, binary: str, serial: str, *arguments: str) -> str:
        # Broken OEMINFO must not conceal otherwise verified hardware identity.
        # Missing/failed fields are returned as empty, never reconstructed.
        try:
            return self._query(binary, serial, *arguments)
        except ServiceUnavailable:
            return ""

    def _identity(self) -> Identity:
        binary, serial = self._connection()
        boot = self._query(binary, serial, "oem", "get-bootinfo")
        build = self._query(binary, serial, "oem", "get-build-number")
        product = self._query(binary, serial, "getvar", "product")
        vendor = self._optional_query(binary, serial, "getvar", "vendorcountry")
        phone = self._optional_query(binary, serial, "getvar", "rescue_phoneinfo")
        identity = Identity(serial, product, build, boot, vendor, phone)
        if identity.model == "UNKNOWN" or not product_from_response(product) or lock_state(boot) == "unverified":
            raise ServiceUnavailable("The connected device has not supplied verified Huawei Fastboot identity.")
        return identity

    def inspect_verlist(self) -> EngineResult:
        try:
            identity = self._identity()
        except ServiceUnavailable as exc:
            return EngineResult(False, str(exc), ActionState.GUARDED)
        main_version = (
            "NO MAIN VERSION"
            if "NO MAIN VERSION" in identity.rescue_phoneinfo
            else (
                identity.rescue_phoneinfo.split("rescue_phoneinfo:", 1)[-1].splitlines()[0].strip()
                if "rescue_phoneinfo:" in identity.rescue_phoneinfo
                else "UNAVAILABLE"
            )
        )
        country = (
            identity.vendorcountry.split("vendorcountry:", 1)[-1].splitlines()[0].strip()
            if "vendorcountry:" in identity.vendorcountry
            else "UNAVAILABLE"
        )
        is_unlocked = lock_state(identity.bootinfo) == "unlocked"
        message = (
            f"Live Verlist: {identity.model}; {main_version}; "
            f"vendor/country={country}; Fastboot={'unlocked' if is_unlocked else 'not proven unlocked'}. "
            "Read-only; no reboot or OEMINFO changes."
        )
        return EngineResult(
            True, message, ActionState.READY,
            {"model": identity.model, "main_version": main_version,
             "vendor_country": country, "unlocked": is_unlocked},
        )

    def _project_family(self) -> Path:
        for parent in (self.engine.app_root, *self.engine.app_root.parents):
            if (parent / ".workspace" / "incoming" / "Huawei kirin" / "huawei Revive").is_dir():
                return parent
        return self.engine.app_root

    def _archive_root(self) -> Path:
        return self._project_family() / ".workspace" / "incoming" / "Huawei kirin" / "huawei Revive"

    def board_firmware(self) -> EngineResult:
        try:
            identity = self._identity()
        except ServiceUnavailable as exc:
            return EngineResult(False, str(exc), ActionState.GUARDED)
        if identity.model not in {"VOG-AL00","VOG-L29"}:
            return EngineResult(False, "Select the model-matched board package in Firmware Flash.", ActionState.MISSING_DEPENDENCY)
        base = self._archive_root() / "firmware"
        boards = sorted(base.glob("VOGUE-AL00A-BD 1.0.0.82*")) if base.is_dir() else []
        if not boards:
            return EngineResult(False, "VOG-AL00 board firmware is not present in the contained archive.", ActionState.MISSING_DEPENDENCY)
        board = boards[0]
        needed = (
            "VOG-AL00-BD_1.0.0.82_Download.xml",
            "bootloaderimage/sec_usb_xloader.img",
            "bootloaderimage/sec_fastboot.img",
            "fastbootimage/oeminfo.mbn",
        )
        missing = [item for item in needed if not (board / item).is_file()]
        if missing:
            return EngineResult(False, "Board package incomplete: " + ", ".join(missing), ActionState.MISSING_DEPENDENCY)
        return EngineResult(
            False,
            f"{identity.model} board package found and inventory complete; board-service write is NOT "
            "enabled in ordinary Fastboot. The current session will not be rebooted or switched.",
            ActionState.GUARDED,
            {"board_root": str(board), "files_present": list(needed), "write_authorized": False},
        )

    def _backup_oeminfo(self) -> EngineResult:
        try:
            identity = self._identity()
            binary, serial = self._connection()
            max_fetch = self._optional_query(binary, serial, "getvar", "max-fetch-size")
            size_response = self._optional_query(binary, serial, "getvar", "partition-size:oeminfo")
        except ServiceUnavailable as exc:
            return EngineResult(False, str(exc), ActionState.GUARDED)
        value = (
            max_fetch.split("max-fetch-size:", 1)[-1].splitlines()[0].strip()
            if "max-fetch-size:" in max_fetch else ""
        )
        if not re.fullmatch(r"(?:0x[0-9a-fA-F]+|[0-9]+)", value) or int(value, 0) <= 0:
            return EngineResult(
                False,
                "This Fastboot loader does not support OEMINFO fetch; no backup or "
                "OEMINFO write attempted. A verified board-service read adapter is required.",
                ActionState.GUARDED,
                {"read_supported": False, "write_authorized": False},
            )
        match = re.search(r"partition-size:oeminfo:\s*(0x[0-9a-f]+|[0-9]+)",size_response,re.I)
        expected_size = int(match.group(1),0) if match else (96*1024**2 if identity.model in {"VOG-AL00","VOG-L29"} else 0)
        if expected_size <= 0:
            return EngineResult(False,"Live OEMINFO partition size not reported; cannot verify complete backup.",ActionState.GUARDED)
        evidence = self._project_family() / ".workspace" / "evidence" / "huawei-backups"
        evidence.mkdir(parents=True, exist_ok=True)
        token = sha256(serial.encode("utf-8")).hexdigest()[:12]
        final = evidence / f"{identity.model.lower()}-oeminfo-{token}.img"
        temporary = evidence / f"{identity.model.lower()}-oeminfo-{token}.partial"
        if temporary.exists():
            return EngineResult(False, "Existing incomplete OEMINFO backup needs review; not overwriting.", ActionState.GUARDED)
        result, _ = self.engine._run(
            "oeminfo_backup_read",
            [binary, "-s", serial, "fetch", "oeminfo", str(temporary)],
            timeout=180,
        )
        if result.returncode or not temporary.is_file():
            return EngineResult(False, "OEMINFO fetch did not complete. No device write attempted.", ActionState.FAILED)
        if temporary.stat().st_size != expected_size:
            return EngineResult(
                False, "OEMINFO read size differs from live partition geometry; partial retained for investigation.",
                ActionState.FAILED,
            )
        if final.exists():
            return EngineResult(False, "Existing OEMINFO backup requires review; new capture retained as partial.", ActionState.GUARDED)
        digest = sha256()
        with temporary.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        temporary.replace(final)
        return EngineResult(
            True,
            f"Full {expected_size} byte OEMINFO backup captured and SHA-256 verified: {digest.hexdigest()}. "
            "No device write or reboot.",
            ActionState.READY,
            {"backup_path": str(final), "sha256": digest.hexdigest(), "write_authorized": False},
        )

    def read_oeminfo(self) -> EngineResult:
        return self._backup_oeminfo()

    def backup_restore(self) -> EngineResult:
        return self._backup_oeminfo()

    def prepare_firmware(self, package_path: str, mode: str = "Upgrade") -> EngineResult:
        file = Path(package_path)
        if not file.is_file() or file.stat().st_size <= 0:
            return EngineResult(False, "Choose an existing nonempty firmware package.", ActionState.GUARDED)
        if mode not in {"Upgrade", "Downgrade", "Full Flash", "Board Firmware", "Repair"}:
            return EngineResult(False, "Unknown firmware operation; no write attempted.", ActionState.GUARDED)
        if mode == "Board Firmware":
            if file.name != "VOG-AL00-BD_1.0.0.82_Download.xml":
                if file.suffix.lower()==".xml":
                    from .qualcomm_board import xml_root
                    try:
                        tree=xml_root(file)
                        return EngineResult(True,"Board XML recognized; native Kirin board-service execution requires the matching stage transport.",
                            ActionState.READY,{"mode":mode,"xml_root":tree.tag,"entries":len(list(tree.iter())),"preflight_only":True,"write_authorized":False})
                    except (OSError,ValueError) as exc:
                        return EngineResult(False,str(exc),ActionState.GUARDED)
                return EngineResult(False, "Select the extracted model-matched board XML.", ActionState.GUARDED)
            return EngineResult(
                False,
                "AL00 board Download.xml recognized. Board-service Fastboot and device-bound recovery evidence "
                "are required; no board firmware has been flashed.",
                ActionState.GUARDED,
                {"mode": mode, "write_authorized": False, "reboot_allowed": False},
            )
        if file.name != "update_sd_base.zip" or "VOGUE-L29D 10.0.0.186(C185E8R5P1)" not in str(file.parent):
            if file.suffix.lower()==".zip":
                import zipfile
                try:
                    with zipfile.ZipFile(file) as archive:
                        entries=[{"name":x.filename,"size":x.file_size} for x in archive.infolist()
                                 if x.filename.lower().endswith((".app",".xml")) and not x.is_dir()]
                    return EngineResult(True,"Archive inventoried. Select its extracted UPDATE.APP or rawprogram XML for direct flashing.",
                        ActionState.READY,{"mode":mode,"archive_members":entries,"preflight_only":True,"write_authorized":False})
                except (OSError,zipfile.BadZipFile) as exc:
                    return EngineResult(False,"Invalid firmware ZIP: "+str(exc),ActionState.GUARDED)
            return EngineResult(False,"Select an extracted UPDATE.APP, compatible manifest or board XML.",ActionState.GUARDED)
        problems = []
        for name, length in _C185_FILES.items():
            path = file.parent / name
            if not path.is_file():
                problems.append("missing " + name)
            elif path.stat().st_size != length:
                problems.append("size mismatch " + name)
        if problems:
            return EngineResult(False, "L29 package set mismatch: " + "; ".join(problems), ActionState.FAILED)
        digests = {}
        try:
            for name, expected_sha in _C185_SHA256.items():
                found_sha = sha256_file(file.parent / name)
                if found_sha != expected_sha:
                    problems.append("SHA-256 mismatch " + name)
                digests[name] = found_sha
        except OSError as exc:
            return EngineResult(
                False, "Could not verify firmware hashes: " + str(exc),
                ActionState.FAILED,
            )
        if problems:
            return EngineResult(
                False, "L29 firmware integrity FAILED: " + "; ".join(problems),
                ActionState.FAILED,
                {"artifact_integrity": "sha256_mismatch", "write_authorized": False},
            )
        board = self._archive_root() / "firmware"
        boards = list(board.glob("VOGUE-AL00A-BD 1.0.0.82*")) if board.is_dir() else []
        return EngineResult(
            False,
            f"{mode} preflight: L29 C185 Base/CUST/PRELOAD sizes and SHA-256 hashes verified; "
            f"target {_VOG_TARGET}, hw/meafnaf. "
            f"AL00 board firmware {'present' if boards else 'missing'}. "
            "Firmware NOT flashed. "
            "Forward conversion only: no automatic return to AL00. "
            "Device-unique OEMINFO preservation, board-service qualification, "
            "anti-rollback compatibility and recovery/readback proof remain write gates. "
            "Automatic reboot disabled.",
            ActionState.GUARDED,
            {"mode": mode, "model": "VOG-L29", "target_build": _VOG_TARGET,
             "vendor": "hw", "country": "meafnaf",
             "artifact_integrity": "sha256_verified_current_session",
             "verified_sha256": digests,
             "preflight_only": True,
             "source_profile": "VOG-AL00",
             "target_profile": "VOG-L29.C185",
             "conversion_direction": "forward_only",
             "automatic_restore_to_al00": False,
             "backup_purpose": "preserve unique OEMINFO records and rescue evidence; not to reinstall AL00",
             "unresolved_gates": [
                 "current_device_oeminfo_backup_verified",
                 "board_service_fastboot_certified",
                 "anti_rollback_compatible",
                 "device_bound_rollback_bundle_and_readback_verified",
             ],
             "write_authorized": False, "reboot_allowed": False},
        )

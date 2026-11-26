from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable
import os
import re
import subprocess
import uuid

from .fastboot_identity import model_from_build, lock_state as parse_lock_state, product_from_response, kirin_product
from .action_health import ActionState
from .evidence import EvidenceEnvelope, EvidenceJournal
from .windows_usb import UsbDiscoveryError, discover_windows_huawei_usb
from .platform_tools import resolve_tool
from .hdc_toolchain import resolve_hdc_tool
from .hdc_identity import probe_hdc_identity


@dataclass(slots=True)
class EngineResult:
    ok: bool
    message: str
    health_state: ActionState
    payload: dict[str, object] | None = None


@dataclass(slots=True)
class DeviceSnapshot:
    connected: bool = False
    interface: str = "—"
    platform: str = "—"
    security: str = "—"
    model: str = "NO DEVICE CONNECTED"
    serial: str = ""
    session_id: str = ""
    product_name: str = ""
    build_number: str = ""
    vendor_country: str = ""
    bootloader_state: str = ""
    main_version: str = ""
    android_version: str = ""
    emui_version: str = ""
    security_patch: str = ""
    board_id: str = ""
    frp_state: str = ""


class DeviceEngine:
    """Read-first Huawei transport core.

    Commands are fixed arrays and never pass through a shell. Exactly one device
    is required before a device identity is accepted. Destructive service actions
    remain guarded until an approved engine adapter is installed.
    """

    def __init__(self, app_root: Path, journal: EvidenceJournal) -> None:
        self.app_root = app_root
        self.journal = journal
        self.snapshot = DeviceSnapshot(session_id=str(uuid.uuid4()))
        self.progress: Callable[[str], None] | None = None
        self._verified_fastboot_proofs: dict[
            str, tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]
        ] = {}

    def _stage(self, message: str) -> None:
        if self.progress is not None:
            self.progress(message)

    def _tool(self, name: str) -> str | None:
        return resolve_tool(self.app_root, name)

    def _run(self, action_id: str, args: Iterable[str], timeout: int = 12) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        command = list(args)
        if action_id == "read_device":
            tail = command[-2:]
            if command[-1:] == ["devices"] or tail == ["devices", "-l"]:
                self._stage("Scanning ADB/Fastboot device connections...")
            elif tail == ["oem", "get-build-number"]:
                self._stage("Reading build number...")
            elif tail == ["oem", "get-bootinfo"]:
                self._stage("Reading bootloader state...")
            elif tail == ["getvar", "product"]:
                self._stage("Reading chipset identity...")
            elif tail == ["getvar", "vendorcountry"]:
                self._stage("Reading vendor and country...")
            elif tail == ["getvar", "rescue_phoneinfo"]:
                self._stage("Reading OEMINFO main version...")
        # Each terminal process uses the user's selected firmware directory.
        # Never call os.chdir(): GUI threads and unrelated services share the process.
        terminal_cwd = getattr(self, "terminal_working_directory", None)
        extra = {"cwd": str(terminal_cwd)} if (
            action_id.startswith("huawei_terminal_") and terminal_cwd is not None
        ) else {}
        completed = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            **extra,
        )
        envelope = EvidenceEnvelope.create(
            session_id=self.snapshot.session_id,
            action_id=action_id,
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        self.journal.append(envelope)
        if action_id == "read_device" and completed.returncode:
            self._stage("Query unavailable: " + " ".join(command[-2:]) + ".")
        return completed, command

    @staticmethod
    def _adb_rows(output: str) -> list[str]:
        rows: list[str] = []
        for raw in output.splitlines():
            line = raw.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            rows.append(line)
        return rows

    @staticmethod
    def _fastboot_rows(output: str) -> list[str]:
        rows = []
        for raw in output.splitlines():
            line = raw.strip()
            if re.match(r"^\S+\s+fastboot(?:d)?$", line, flags=re.IGNORECASE):
                rows.append(line)
        return rows

    def probe(self) -> EngineResult:
        self._stage("Checking USB interfaces...")
        usb_report = None
        if _is_windows():
            try:
                usb_report = discover_windows_huawei_usb()
            except UsbDiscoveryError as exc:
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False,
                    f"Huawei USB discovery unavailable: {exc.message}",
                    ActionState.FAILED,
                )
            if usb_report.state == "multiple_huawei_devices":
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False,
                    "Multiple Huawei devices detected. Select exactly one physical Huawei device.",
                    ActionState.GUARDED,
                    {"usb_discovery": usb_report.to_dict()},
                )
            if usb_report.present and usb_report.state == "harmony_hdc":
                return self._probe_harmony_hdc(usb_report)
            # A Huawei PnP interface is not yet bound to the Fastboot CLI
            # serial. Preserve the existing physical-device identity boundary.
            if usb_report.present and usb_report.state not in {"adb","normal_fastboot"}:
                return self._result_from_usb_report(usb_report)

        adb = self._tool("adb")
        fastboot = self._tool("fastboot")
        adb_rows: list[str] = []
        fastboot_rows: list[str] = []
        if fastboot:
            result, _ = self._run("read_device", [fastboot, "devices"])
            fastboot_rows = self._fastboot_rows(result.stdout)
        # A different ADB phone must not conceal the selected Fastboot session.
        if adb and not fastboot_rows:
            result, _ = self._run("read_device", [adb, "devices", "-l"])
            adb_rows = self._adb_rows(result.stdout)

        if _is_windows():
            if usb_report is None or not usb_report.present or usb_report.state == "normal_fastboot":
                adb_rows = self._verified_huawei_adb_rows(adb, adb_rows) if adb else []
                fastboot_rows = (
                    self._verified_huawei_fastboot_rows(fastboot, fastboot_rows)
                    if fastboot
                    else []
                )
            elif usb_report.state == "adb":
                adb_rows = self._verified_huawei_adb_rows(adb, adb_rows) if adb else []
                fastboot_rows = []

            if usb_report is not None and usb_report.state == "adb" and not adb_rows:
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False,
                    "Huawei ADB interface detected, but no verified authorized Huawei ADB session is available.",
                    ActionState.GUARDED,
                    {"usb_discovery": usb_report.to_dict()},
                )

        total = len(adb_rows) + len(fastboot_rows)
        if total == 0:
            if usb_report is not None and usb_report.present and usb_report.state == "normal_fastboot":
                result = self._result_from_usb_report(usb_report)
                result.message += " Fastboot protocol is not responding; detailed identity is unavailable."
                return result
            self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
            missing = []
            if not adb:
                missing.append("ADB")
            if not fastboot:
                missing.append("Fastboot")
            if missing:
                return EngineResult(False, f"No device detected. Missing tools: {', '.join(missing)}.", ActionState.MISSING_DEPENDENCY)
            return EngineResult(False, "No Huawei device detected in USB, ADB or Fastboot mode.", ActionState.READY)
        if total > 1:
            self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
            return EngineResult(False, "Multiple Huawei devices detected. Connect exactly one service device.", ActionState.GUARDED)

        if adb_rows:
            serial = adb_rows[0].split()[0]
            if "unauthorized" in adb_rows[0]:
                return EngineResult(False, "ADB device is unauthorized.", ActionState.GUARDED)
            if "offline" in adb_rows[0]:
                return EngineResult(False, "ADB device is offline.", ActionState.FAILED)
            model = "Huawei Android Device"
            platform_name = "Android / ADB"
            security = "Authorized"
            if adb:
                props, _ = self._run("read_device", [adb, "-s", serial, "shell", "getprop", "ro.product.model"])
                candidate = props.stdout.strip()
                if candidate:
                    model = candidate
            # Do not call another manufacturer's ADB handset a Huawei.
            if adb:
                brand, _ = self._run("read_device", [adb, "-s", serial, "shell", "getprop", "ro.product.brand"])
                if brand.stdout.strip().lower() not in {"huawei", "honor"}:
                    self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                    return EngineResult(False, "The connected ADB handset is not verified as Huawei/Honor.", ActionState.GUARDED)
            self.snapshot = DeviceSnapshot(True, "ADB", platform_name, security, model, serial, str(uuid.uuid5(uuid.NAMESPACE_URL, serial)))
        else:
            serial = fastboot_rows[0].split()[0]
            self._stage("Connected to Fastboot device. Reading verified identity...")
            proof = self._verified_fastboot_proofs.get(serial)
            if proof is None:
                identity, _ = self._run("read_device", [fastboot, "-s", serial, "oem", "get-build-number"])
                boot, _ = self._run("read_device", [fastboot, "-s", serial, "oem", "get-bootinfo"])
            else:
                identity, boot = proof
            model_match = model_from_build(identity.stdout + "\n" + identity.stderr)
            boot_text = (boot.stdout + "\n" + boot.stderr).strip()
            lock_state = parse_lock_state(boot_text)
            security = "Fastboot " + lock_state

            # Only issue read-only queries for fields actually exposed in
            # Fastboot. No attempt to invent an IMEI or an Android patch level.
            build_value = (identity.stdout + "\n" + identity.stderr).strip()
            build_match = re.search(r"\b[A-Z]{3}-[A-Z0-9]{2,8}\s+\d+\.\d+\.\d+[^\s]*", build_value)
            vendor, _ = self._run("read_device", [fastboot, "-s", serial, "getvar", "vendorcountry"])
            main, _ = self._run("read_device", [fastboot, "-s", serial, "getvar", "rescue_phoneinfo"])
            product, _ = self._run("read_device", [fastboot, "-s", serial, "getvar", "product"])
            vendor_match = re.search(r"vendorcountry:\s*([^\r\n]+)", vendor.stdout + "\n" + vendor.stderr, re.IGNORECASE)
            main_match = re.search(r"rescue_phoneinfo:\s*([^\r\n]+)", main.stdout + "\n" + main.stderr, re.IGNORECASE)
            product_match = re.search(r"product:\s*([^\r\n]+)", product.stdout + "\n" + product.stderr, re.IGNORECASE)
            product_value = product_match.group(1).strip() if product_match else ""
            # A damaged OEMINFO can make get-build-number unavailable even
            # though the Kirin 980 bootloader responds. Do not fabricate VOG-L29.
            if not model_match and not kirin_product(product_value):
                self.snapshot = DeviceSnapshot(session_id=self.snapshot.session_id)
                return EngineResult(
                    False, "Fastboot is present, but Huawei hardware identity is unverified.",
                    ActionState.GUARDED,
                )
            model_value = (
                model_match if model_match
                else f"Huawei {product_value} (model unresolved)"
            )
            self.snapshot = DeviceSnapshot(
                connected=True, interface="Fastboot",
                platform=product_value or "Huawei Fastboot",
                security=security, model=model_value, serial=serial,
                session_id=str(uuid.uuid5(uuid.NAMESPACE_URL, serial)),
                product_name="Huawei P30 Pro" if model_value.startswith("VOG-") else model_value,
                build_number=build_match.group(0) if build_match else "",
                vendor_country=vendor_match.group(1).strip() if vendor_match else "",
                bootloader_state=lock_state,
                main_version=main_match.group(1).strip() if main_match else "",
            )

        payload: dict[str, object] = asdict(self.snapshot)
        if usb_report is not None and usb_report.present:
            payload["usb_discovery"] = usb_report.to_dict()
        detail = (
            " OEMINFO model/build currently unreadable; partial identity only."
            if self.snapshot.model.endswith("(model unresolved)") else ""
        )
        return EngineResult(
            True,
            f"Connected: {self.snapshot.model} via {self.snapshot.interface}.{detail}",
            ActionState.READY, payload,
        )

    def _verified_huawei_fastboot_rows(
        self, fastboot: str, rows: list[str]
    ) -> list[str]:
        verified: list[str] = []
        for row in rows:
            serial = row.split()[0]
            build, _ = self._run(
                "read_device",
                [fastboot, "-s", serial, "oem", "get-build-number"],
            )
            build_text = f"{build.stdout}\n{build.stderr}".upper()
            build_verified = (
                build.returncode == 0
                and "(BOOTLOADER)" in build_text
                and bool(model_from_build(build_text))
            )
            if not build_verified:
                product, _ = self._run(
                    "read_device", [fastboot, "-s", serial, "getvar", "product"]
                )
                chip_text = f"{product.stdout}\n{product.stderr}"
                if product.returncode != 0 or not kirin_product(product_from_response(chip_text)):
                    continue

            bootinfo, _ = self._run(
                "read_device",
                [fastboot, "-s", serial, "oem", "get-bootinfo"],
            )
            if bootinfo.returncode != 0:
                continue
            bootinfo_text = f"{bootinfo.stdout}\n{bootinfo.stderr}".upper()
            if parse_lock_state(bootinfo_text) == "unverified":
                continue
            self._verified_fastboot_proofs[serial] = (build, bootinfo)
            verified.append(row)
        return verified

    def _verified_huawei_adb_rows(self, adb: str | None, rows: list[str]) -> list[str]:
        if not adb:
            return []
        verified: list[str] = []
        for row in rows:
            lowered = row.lower()
            if "unauthorized" in lowered or "offline" in lowered:
                continue
            serial = row.split()[0]
            result, _ = self._run(
                "read_device",
                [adb, "-s", serial, "shell", "getprop", "ro.product.manufacturer"],
            )
            manufacturer = result.stdout.strip().upper()
            if manufacturer in {"HUAWEI", "HONOR"}:
                verified.append(row)
        return verified

    def _probe_harmony_hdc(self, usb_report) -> EngineResult:
        """Identify only via the authorized device's HDC model property.

        A healthy WinUSB binding is not enough. No USB label or product ID
        is ever interpreted as a handset's retail model.
        """
        basic = self._result_from_usb_report(usb_report)
        self._stage("Checking authorized HarmonyOS HDC connection...")
        executable = resolve_hdc_tool(self.app_root)
        proof = probe_hdc_identity(executable or "")
        details = basic.payload if isinstance(basic.payload, dict) else {}
        details["hdc_probe"] = {
            "status": proof.status,
            "target_key_sha256": proof.target_key_sha256,
            "reason": proof.reason,
            "identity_verified": proof.identity_verified,
            "device_modification": "none",
        }
        details["identity_binding"] = "unbound_protocol_and_usb_cohort"
        if not proof.identity_verified:
            basic.message = (
                "HarmonyOS HDC USB interface detected, but device model is not yet "
                "readable: " + (proof.reason or proof.status) + "."
            )
            basic.payload = details
            return basic
        self.snapshot = DeviceSnapshot(
            connected=True, interface="HarmonyOS HDC",
            platform="HarmonyOS", security="Authorized read-only HDC",
            model=proof.model, serial="",
            session_id=str(uuid.uuid5(uuid.NAMESPACE_URL, usb_report.fingerprint_sha256)),
            build_number=proof.build,
        )
        payload = asdict(self.snapshot)
        payload["usb_discovery"] = usb_report.to_dict()
        payload["hdc_probe"] = details["hdc_probe"]
        payload["hdc_probe"]["brand"] = proof.brand
        payload["identity_binding"] = "unbound_protocol_and_usb_cohort"
        return EngineResult(
            True, f"HarmonyOS HDC reports model: {proof.model}. "
                  "Physical USB/HDC identity binding remains provisional.",
            ActionState.READY, payload,
        )

    def _result_from_usb_report(self, usb_report) -> EngineResult:
        labels = {
            "normal_android_charge_only": "Huawei Android / Charge only",
            "mtp": "MTP",
            "normal_fastboot": "Fastboot",
            "recovery": "Recovery",
            "upgrade_mode": "Upgrade Mode",
            "huawei_usb_com_1_0": "HUAWEI USB COM 1.0",
            "harmony_hdc": "HarmonyOS HDC (WinUSB)",
            "unknown_huawei": "Huawei USB",
        }
        interface = labels.get(usb_report.state, "Huawei USB")
        session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, usb_report.fingerprint_sha256))
        self.snapshot = DeviceSnapshot(
            True,
            interface,
            "Huawei USB",
            "Read-only / identity pending",
            "Huawei device (identity pending)",
            "",
            session_id,
        )
        payload: dict[str, object] = asdict(self.snapshot)
        payload["usb_discovery"] = usb_report.to_dict()
        return EngineResult(
            True,
            f"Connected: {self.snapshot.model} via {interface}. {usb_report.decision_code}.",
            ActionState.READY,
            payload,
        )

    def guarded(self, label: str) -> EngineResult:
        return EngineResult(
            False,
            f"{label} is wired but guarded. Install an approved service adapter and complete ownership authorization before write access.",
            ActionState.GUARDED,
        )

    def package_preflight(self, package_path: str) -> EngineResult:
        path = Path(package_path)
        if not path.is_file():
            return EngineResult(False, "Select a firmware package first.", ActionState.GUARDED)
        if path.stat().st_size == 0:
            return EngineResult(False, "Firmware package is empty.", ActionState.FAILED)
        return EngineResult(True, f"Package selected: {path.name} ({path.stat().st_size:,} bytes).", ActionState.READY, {"path": str(path), "size": path.stat().st_size})


def _is_windows() -> bool:
    return os.name == "nt"

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

_USB_ID_RE = re.compile(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", re.IGNORECASE)
_HUAWEI_VID = "12D1"


@dataclass(frozen=True, slots=True)
class UsbObservation:
    instance_id: str = ""
    class_name: str = ""
    friendly_name: str = ""
    device_desc: str = ""
    bus_reported_desc: str = ""
    manufacturer: str = ""
    hardware_ids: tuple[str, ...] = ()
    compatible_ids: tuple[str, ...] = ()
    container_id: str = ""
    parent_instance_id: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "UsbObservation":
        return cls(
            instance_id=_text(value.get("instance_id")),
            class_name=_text(value.get("class_name")),
            friendly_name=_text(value.get("friendly_name")),
            device_desc=_text(value.get("device_desc")),
            bus_reported_desc=_text(value.get("bus_reported_desc")),
            manufacturer=_text(value.get("manufacturer")),
            hardware_ids=_text_tuple(value.get("hardware_ids")),
            compatible_ids=_text_tuple(value.get("compatible_ids")),
            container_id=_text(value.get("container_id")),
            parent_instance_id=_text(value.get("parent_instance_id")),
        )


@dataclass(frozen=True, slots=True)
class UsbDiscoveryReport:
    present: bool
    state: str
    transport: str
    vid: str
    pid: str
    fingerprint_sha256: str
    model: str
    interfaces: tuple[str, ...]
    decision_code: str
    next_action: str
    screen_required: bool = False
    device_modification: str = "none"
    write_authority: str = "none"

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["interfaces"] = list(self.interfaces)
        return value


def discover_huawei_usb(
    observations: Sequence[UsbObservation | Mapping[str, Any]],
) -> UsbDiscoveryReport:
    normalized = [
        item if isinstance(item, UsbObservation) else UsbObservation.from_mapping(item)
        for item in observations
    ]
    groups = _physical_groups(normalized)
    huawei_groups = [group for group in groups if any(_is_huawei_observation(item) for item in group)]

    if not huawei_groups:
        return UsbDiscoveryReport(
            present=False,
            state="no_huawei",
            transport="none",
            vid="",
            pid="",
            fingerprint_sha256="",
            model="none",
            interfaces=(),
            decision_code="NO_HUAWEI_DEVICE",
            next_action="wait_for_huawei_device",
        )
    if len(huawei_groups) > 1:
        return UsbDiscoveryReport(
            present=True,
            state="multiple_huawei_devices",
            transport="windows_pnp_usb",
            vid="",
            pid="",
            fingerprint_sha256="",
            model="identity_ambiguous",
            interfaces=tuple(sorted(_public_interfaces(item for group in huawei_groups for item in group))),
            decision_code="MULTIPLE_HUAWEI_DEVICES",
            next_action="select_exact_physical_huawei_device",
        )

    group = huawei_groups[0]
    state = _classify_state(group)
    vid, pid = _primary_usb_id(group)
    fingerprint = _fingerprint(group, vid=vid, pid=pid)
    decision_code, next_action = _decision_for_state(state)
    return UsbDiscoveryReport(
        present=True,
        state=state,
        transport=_transport_for_state(state),
        vid=vid,
        pid=pid,
        fingerprint_sha256=fingerprint,
        model="identity_pending",
        interfaces=tuple(sorted(_public_interfaces(group))),
        decision_code=decision_code,
        next_action=next_action,
    )


def _physical_groups(observations: Sequence[UsbObservation]) -> list[list[UsbObservation]]:
    groups: dict[str, list[UsbObservation]] = {}
    for item in observations:
        key = item.container_id.strip().upper()
        if not key:
            serial = _usb_serial(item)
            key = f"SERIAL:{serial.upper()}" if serial else f"INSTANCE:{item.instance_id.upper()}"
        groups.setdefault(key, []).append(item)
    return list(groups.values())


def _is_huawei_observation(item: UsbObservation) -> bool:
    ids = " ".join((item.instance_id, *item.hardware_ids, *item.compatible_ids))
    match = _USB_ID_RE.search(ids)
    if match and match.group(1).upper() == _HUAWEI_VID:
        return True
    text = _observation_text(item)
    return "HUAWEI USB COM 1.0" in text or "HUAWEI" in text


def _classify_state(group: Sequence[UsbObservation]) -> str:
    texts = [_observation_text(item) for item in group]
    joined = "\n".join(texts)
    classes = {item.class_name.strip().upper() for item in group}

    if "HUAWEI USB COM 1.0" in joined:
        return "huawei_usb_com_1_0"
    if ("PC UI" in joined or "PCUI" in joined) and "DBADAPTER" in joined:
        return "upgrade_mode"
    if "FASTBOOT" in joined or "BOOTLOADER INTERFACE" in joined:
        return "normal_fastboot"
    if "RECOVERY" in joined:
        return "recovery"
    if "ADB" in joined:
        return "adb"
    if "WPD" in classes or "MTP" in joined or "MEDIA TRANSFER PROTOCOL" in joined:
        return "mtp"
    if (
        "USB MASS STORAGE" in joined
        or "FILE-CD GADGET" in joined
        or "CD-ROM" in joined
        or "CDROM" in classes
        or any("CLASS_08" in value.upper() for item in group for value in item.compatible_ids)
    ):
        return "storage_only_pre_service"
    return "unknown_huawei"


def _decision_for_state(state: str) -> tuple[str, str]:
    decisions = {
        "storage_only_pre_service": (
            "DIRECT_ROUTE_UNAVAILABLE",
            "identify_model_then_enter_supported_service_mode",
        ),
        "mtp": ("MTP_CANDIDATE", "verify_mtp_operation_eligibility"),
        "adb": ("ADB_AUTHORIZATION_REQUIRED", "verify_adb_authorization"),
        "normal_fastboot": ("FASTBOOT_CANDIDATE", "verify_fastboot_operation_eligibility"),
        "recovery": ("RECOVERY_DETECTED", "evaluate_recovery_route"),
        "upgrade_mode": (
            "UPGRADE_MODE_DETECTED_RECIPE_REQUIRED",
            "verify_upgrade_mode_recipe_eligibility",
        ),
        "huawei_usb_com_1_0": (
            "SERVICE_ENTRY_DETECTED_ARTIFACT_REQUIRED",
            "identify_exact_model_and_validate_service_artifact",
        ),
        "unknown_huawei": (
            "HUAWEI_USB_STATE_UNKNOWN",
            "collect_more_read_only_identity_evidence",
        ),
    }
    return decisions[state]


def _transport_for_state(state: str) -> str:
    return {
        "storage_only_pre_service": "windows_pnp_usb_storage",
        "mtp": "windows_wpd_mtp",
        "adb": "windows_usb_adb",
        "normal_fastboot": "windows_usb_fastboot",
        "recovery": "windows_pnp_usb_recovery",
        "upgrade_mode": "windows_pnp_usb_upgrade",
        "huawei_usb_com_1_0": "windows_serial_service",
        "unknown_huawei": "windows_pnp_usb",
    }[state]


def _primary_usb_id(group: Sequence[UsbObservation]) -> tuple[str, str]:
    matches: list[tuple[str, str]] = []
    for item in group:
        for value in (item.instance_id, *item.hardware_ids, *item.compatible_ids):
            match = _USB_ID_RE.search(value)
            if match and match.group(1).upper() == _HUAWEI_VID:
                matches.append((match.group(1).upper(), match.group(2).upper()))
    if not matches:
        return _HUAWEI_VID, ""
    return matches[0]


def _fingerprint(group: Sequence[UsbObservation], *, vid: str, pid: str) -> str:
    private_material = {
        "vid": vid,
        "pid": pid,
        "serials": sorted({value for item in group if (value := _usb_serial(item))}),
        "containers": sorted({item.container_id for item in group if item.container_id}),
    }
    encoded = json.dumps(
        private_material,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _usb_serial(item: UsbObservation) -> str:
    if not _USB_ID_RE.search(item.instance_id):
        return ""
    parts = item.instance_id.split("\\")
    return parts[-1].strip() if len(parts) >= 3 else ""


def _public_interfaces(items: Sequence[UsbObservation] | Any) -> set[str]:
    result: set[str] = set()
    for item in items:
        for value in (item.friendly_name, item.device_desc, item.bus_reported_desc):
            value = value.strip()
            if value:
                result.add(value)
    return result


def _observation_text(item: UsbObservation) -> str:
    return " ".join(
        (
            item.instance_id,
            item.class_name,
            item.friendly_name,
            item.device_desc,
            item.bus_reported_desc,
            item.manufacturer,
            *item.hardware_ids,
            *item.compatible_ids,
        )
    ).upper()


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _text_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if item is not None)
    return (str(value),)

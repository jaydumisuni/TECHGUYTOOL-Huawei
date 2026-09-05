from __future__ import annotations

from techguy_huawei.usb_discovery import discover_huawei_usb


def obs(
    instance_id: str,
    *,
    class_name: str = "USB",
    friendly_name: str = "",
    device_desc: str = "",
    bus_reported_desc: str = "",
    manufacturer: str = "",
    hardware_ids: list[str] | None = None,
    compatible_ids: list[str] | None = None,
    container_id: str = "container-a",
    parent_instance_id: str = "",
) -> dict[str, object]:
    return {
        "instance_id": instance_id,
        "class_name": class_name,
        "friendly_name": friendly_name,
        "device_desc": device_desc,
        "bus_reported_desc": bus_reported_desc,
        "manufacturer": manufacturer,
        "hardware_ids": hardware_ids or [],
        "compatible_ids": compatible_ids or [],
        "container_id": container_id,
        "parent_instance_id": parent_instance_id,
    }


def storage_only_fixture(serial: str = "FIXTURE107E", container: str = "container-huawei") -> list[dict[str, object]]:
    return [
        obs(
            rf"USB\VID_12D1&PID_107E\{serial}",
            friendly_name="USB Mass Storage Device",
            device_desc="USB Mass Storage Device",
            bus_reported_desc="HUAWEI",
            manufacturer="Compatible USB storage device",
            hardware_ids=["USB\\VID_12D1&PID_107E&REV_0299", "USB\\VID_12D1&PID_107E"],
            compatible_ids=["USB\\Class_08&SubClass_06&Prot_50"],
            container_id=container,
        ),
        obs(
            rf"USBSTOR\CDROM&VEN_LINUX&PROD_FILE-CD_GADGET&REV_0409\{serial}&0",
            class_name="CDROM",
            friendly_name="Linux File-CD Gadget USB Device",
            device_desc="CD-ROM Drive",
            container_id=container,
        ),
    ]


def redmi_adb_fixture() -> list[dict[str, object]]:
    return [
        obs(
            r"USB\VID_2717&PID_FF88\REDMI-SERIAL",
            class_name="AndroidUsbDeviceClass",
            friendly_name="Android Composite ADB Interface",
            device_desc="Android ADB Interface",
            manufacturer="Xiaomi",
            hardware_ids=["USB\\VID_2717&PID_FF88"],
            container_id="container-redmi",
        )
    ]


def test_107e_file_cd_gadget_is_normal_android_charge_only_without_model_inference() -> None:
    report = discover_huawei_usb(storage_only_fixture())
    assert report.present is True
    assert report.state == "normal_android_charge_only"
    assert report.vid == "12D1"
    assert report.pid == "107E"
    assert report.model == "identity_pending"
    assert report.decision_code == "ANDROID_CHARGE_ONLY_DETECTED"
    assert report.screen_required is False
    assert report.device_modification == "none"
    assert report.write_authority == "none"


def test_fingerprint_is_deterministic_and_public_payload_omits_private_serial() -> None:
    first = discover_huawei_usb(storage_only_fixture(serial="PRIVATE-SERIAL"))
    second = discover_huawei_usb(storage_only_fixture(serial="PRIVATE-SERIAL"))
    assert first.fingerprint_sha256 == second.fingerprint_sha256
    assert len(first.fingerprint_sha256) == 64
    assert "PRIVATE-SERIAL" not in repr(first.to_dict())


def test_redmi_adb_does_not_change_huawei_identity() -> None:
    report = discover_huawei_usb(storage_only_fixture() + redmi_adb_fixture())
    assert report.state == "normal_android_charge_only"
    assert report.vid == "12D1"
    assert report.pid == "107E"
    assert "2717" not in repr(report.to_dict())
    assert "REDMI-SERIAL" not in repr(report.to_dict())


def test_two_huawei_devices_fail_closed() -> None:
    report = discover_huawei_usb(
        storage_only_fixture(serial="HUAWEI-A", container="container-a")
        + storage_only_fixture(serial="HUAWEI-B", container="container-b")
    )
    assert report.present is True
    assert report.state == "multiple_huawei_devices"
    assert report.decision_code == "MULTIPLE_HUAWEI_DEVICES"
    assert report.fingerprint_sha256 == ""
    assert report.write_authority == "none"


def test_upgrade_mode_requires_service_interface_evidence_not_pid_alone() -> None:
    storage = discover_huawei_usb(storage_only_fixture())
    assert storage.state == "normal_android_charge_only"

    upgrade = discover_huawei_usb(
        storage_only_fixture()
        + [
            obs(
                r"USB\VID_12D1&PID_107E&MI_00\FIXTURE107E",
                class_name="Ports",
                friendly_name="HUAWEI Mobile Connect - 3G PC UI Interface",
                container_id="container-huawei",
            ),
            obs(
                r"USB\VID_12D1&PID_107E&MI_01\FIXTURE107E",
                class_name="Ports",
                friendly_name="DBAdapter Reserved Interface",
                container_id="container-huawei",
            ),
        ]
    )
    assert upgrade.state == "upgrade_mode"
    assert upgrade.decision_code == "UPGRADE_MODE_DETECTED_RECIPE_REQUIRED"


def test_huawei_usb_com_1_0_has_highest_service_entry_precedence() -> None:
    report = discover_huawei_usb(
        storage_only_fixture()
        + [
            obs(
                r"USB\VID_12D1&PID_3609\FIXTURE107E",
                class_name="Ports",
                friendly_name="HUAWEI USB COM 1.0",
                container_id="container-huawei",
            )
        ]
    )
    assert report.state == "huawei_usb_com_1_0"
    assert report.decision_code == "SERVICE_ENTRY_DETECTED_ARTIFACT_REQUIRED"


def test_explicit_protocol_interfaces_are_classified_read_only() -> None:
    cases = [
        ("WPD", "Huawei P40 Pro", "mtp", "MTP_CANDIDATE"),
        ("AndroidUsbDeviceClass", "Huawei ADB Interface", "adb", "ADB_AUTHORIZATION_REQUIRED"),
        ("AndroidUsbDeviceClass", "Android Bootloader Interface", "normal_fastboot", "FASTBOOT_CANDIDATE"),
        ("USB", "Huawei Recovery Interface", "recovery", "RECOVERY_DETECTED"),
    ]
    for class_name, friendly_name, state, decision in cases:
        report = discover_huawei_usb(
            [
                obs(
                    r"USB\VID_12D1&PID_1234\PROTO-SERIAL",
                    class_name=class_name,
                    friendly_name=friendly_name,
                    bus_reported_desc="HUAWEI",
                    hardware_ids=["USB\\VID_12D1&PID_1234"],
                    container_id="container-proto",
                )
            ]
        )
        assert report.state == state
        assert report.decision_code == decision
        assert report.write_authority == "none"


def test_non_huawei_observations_return_no_huawei() -> None:
    report = discover_huawei_usb(redmi_adb_fixture())
    assert report.present is False
    assert report.state == "no_huawei"
    assert report.decision_code == "NO_HUAWEI_DEVICE"


def test_fingerprint_ignores_composite_child_topology_churn() -> None:
    root_observation = {
        "instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL123",
        "class_name": "USB",
        "friendly_name": "HUAWEI",
        "bus_reported_desc": "HUAWEI",
        "hardware_ids": [r"USB\VID_12D1&PID_107E"],
        "container_id": "stable-container",
    }
    child_a = {
        "instance_id": r"USB\VID_12D1&PID_107E&MI_00\6&AAA111&0&0000",
        "class_name": "USB",
        "friendly_name": "USB Mass Storage Device",
        "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_00"],
        "container_id": "stable-container",
        "parent_instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL123",
    }
    child_b = dict(child_a)
    child_b["instance_id"] = r"USB\VID_12D1&PID_107E&MI_00\7&BBB222&0&0000"

    first = discover_huawei_usb([root_observation, child_a])
    second = discover_huawei_usb([root_observation, child_b])

    assert first.fingerprint_sha256 == second.fingerprint_sha256


def test_fingerprint_survives_huawei_pid_mode_transition() -> None:
    pre_service = {
        "instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL123",
        "class_name": "USB",
        "friendly_name": "HUAWEI",
        "bus_reported_desc": "HUAWEI",
        "hardware_ids": [r"USB\VID_12D1&PID_107E"],
        "container_id": "stable-container",
    }
    fastboot = {
        "instance_id": r"USB\VID_12D1&PID_3609\ROOTSERIAL123",
        "class_name": "AndroidUsbDeviceClass",
        "friendly_name": "HUAWEI Android Bootloader Interface",
        "bus_reported_desc": "HUAWEI Fastboot",
        "hardware_ids": [r"USB\VID_12D1&PID_3609"],
        "container_id": "stable-container",
    }

    first = discover_huawei_usb([pre_service])
    second = discover_huawei_usb([fastboot])

    assert first.fingerprint_sha256 == second.fingerprint_sha256


def test_public_interfaces_never_expose_raw_pnp_descriptions() -> None:
    report = discover_huawei_usb(
        [
            {
                "instance_id": r"USB\VID_12D1&PID_107E&MI_01\PRIVATE-SERIAL",
                "class_name": "AndroidUsbDeviceClass",
                "friendly_name": "HUAWEI ADB PRIVATE-SERIAL",
                "device_desc": "PRIVATE-SERIAL device description",
                "bus_reported_desc": "PRIVATE-SERIAL HUAWEI ADB",
                "manufacturer": "HUAWEI",
                "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_01"],
                "container_id": "private-interface-container",
                "parent_instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL",
            }
        ]
    )
    encoded = repr(report.to_dict())
    assert "PRIVATE-SERIAL" not in encoded
    assert report.interfaces == ("ADB",)


def test_composite_children_group_by_confirmed_huawei_parent() -> None:
    observations = [
        {
            "instance_id": r"USB\VID_12D1&PID_107E&MI_00\6&AAA&0&0000",
            "class_name": "USB",
            "friendly_name": "USB Mass Storage Device",
            "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_00"],
            "parent_instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL123",
        },
        {
            "instance_id": r"USB\VID_12D1&PID_107E&MI_01\6&AAA&0&0001",
            "class_name": "AndroidUsbDeviceClass",
            "friendly_name": "HUAWEI ADB Interface",
            "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_01"],
            "parent_instance_id": r"USB\VID_12D1&PID_107E\ROOTSERIAL123",
        },
    ]
    report = discover_huawei_usb(observations)
    assert report.state != "multiple_huawei_devices"
    assert report.present is True


def test_shared_non_huawei_hub_parent_does_not_merge_devices() -> None:
    observations = [
        {
            "instance_id": r"USB\VID_12D1&PID_107E&MI_00\CHILDA",
            "class_name": "USB",
            "friendly_name": "USB Mass Storage Device",
            "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_00"],
            "parent_instance_id": r"USB\VID_05E3&PID_0610\HUBSERIAL",
        },
        {
            "instance_id": r"USB\VID_12D1&PID_107E&MI_00\CHILDB",
            "class_name": "USB",
            "friendly_name": "USB Mass Storage Device",
            "hardware_ids": [r"USB\VID_12D1&PID_107E&MI_00"],
            "parent_instance_id": r"USB\VID_05E3&PID_0610\HUBSERIAL",
        },
    ]
    report = discover_huawei_usb(observations)
    assert report.state == "multiple_huawei_devices"

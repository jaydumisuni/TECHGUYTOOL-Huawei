from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "qml" / "pages"


def test_all_navigation_pages_are_real_and_packaged() -> None:
    expected = [
        "DeviceInformationPage.qml",
        "PartitionManagerPage.qml",
        "BackupRestorePage.qml",
        "OperationHistoryPage.qml",
    ]
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    for name in expected:
        assert (PAGES / name).is_file(), name
        assert f"qml/pages/{name}" in qrc, name


def test_compatibility_router_renders_real_pages_not_placeholder_copy() -> None:
    router = (PAGES / "PlaceholderPage.qml").read_text(encoding="utf-8")
    for qml_type in (
        "DeviceInformationPage",
        "PartitionManagerPage",
        "BackupRestorePage",
        "OperationHistoryPage",
    ):
        assert qml_type in router
    assert "This module is connected to the common engine interface" not in router
    assert "root.message" not in router


def test_main_navigation_has_no_unhandled_page_index() -> None:
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    for title in (
        "Service Center",
        "Device Information",
        "Firmware Flash",
        "Partition Manager",
        "Backup & Restore",
        "Operation History",
    ):
        assert title in main

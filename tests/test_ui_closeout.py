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


def test_placeholder_router_is_completely_removed() -> None:
    assert not (PAGES / "PlaceholderPage.qml").exists()
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    assert "PlaceholderPage.qml" not in qrc
    assert "PlaceholderPage" not in main
    assert "placeholderComponent" not in main


def test_main_navigation_routes_all_six_pages_directly() -> None:
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
    for component in (
        "ServiceCenterPage",
        "DeviceInformationPage",
        "FirmwareFlashPage",
        "PartitionManagerPage",
        "BackupRestorePage",
        "OperationHistoryPage",
    ):
        assert component in main


def test_approved_sidebar_mascot_is_text_safe_and_packaged() -> None:
    mascot = ROOT / "assets" / "brand" / "techguy_mascot_masked.svg"
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    glass = (ROOT / "qml" / "components" / "GlassPanel.qml").read_text(encoding="utf-8")

    assert mascot.is_file()
    source = mascot.read_text(encoding="utf-8")
    assert source.startswith("<svg")
    assert "clipPath" in source
    assert "data:image/jpeg;base64," in source
    assert "assets/brand/techguy_mascot_masked.svg" in qrc
    assert "techguy_mascot_masked.svg" in glass
    assert "approvedMascotPanel" in glass

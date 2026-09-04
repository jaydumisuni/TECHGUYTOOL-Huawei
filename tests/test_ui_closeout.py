from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "qml" / "pages"
DIALOGS = ROOT / "qml" / "dialogs"


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


def test_testpoint_library_is_real_packaged_and_wired() -> None:
    dialog = DIALOGS / "TestpointDialog.qml"
    settings = (DIALOGS / "SettingsMenu.qml").read_text(encoding="utf-8")
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    deploy = (ROOT / "pysidedeploy.spec").read_text(encoding="utf-8")

    assert dialog.is_file()
    source = dialog.read_text(encoding="utf-8")
    assert "TESTPOINT / PINOUT LIBRARY" in source
    assert "NO APPROVED TESTPOINT REFERENCE" in source
    assert "similar Huawei/Honor model" in source
    assert "Testpoint / Pinout Library" in settings
    assert "testpointRequested" in settings
    assert "onTestpointRequested: testpointDialog.open()" in main
    assert "TestpointDialog { id: testpointDialog" in main
    assert "qml/dialogs/TestpointDialog.qml" in qrc
    assert "qml/dialogs/TestpointDialog.qml" in deploy


def test_upgrade_mode_is_separate_from_rescue_everywhere() -> None:
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    service = (PAGES / "ServiceCenterPage.qml").read_text(encoding="utf-8")
    combined = "Upgrade / Rescue"
    assert combined not in main
    assert combined not in service
    assert '"Fastboot", "Upgrade Mode", "Rescue"' in main
    assert '"Fastboot", "Upgrade Mode", "Rescue"' in service


def test_approved_sidebar_mascot_is_packaged_and_single_owned() -> None:
    mascot = ROOT / "assets" / "brand" / "techguy_mascot.png"
    qrc = (ROOT / "resources.qrc").read_text(encoding="utf-8")
    main = (ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    glass = (ROOT / "qml" / "components" / "GlassPanel.qml").read_text(encoding="utf-8")

    assert mascot.is_file()
    assert "assets/brand/techguy_mascot.png" in qrc
    assert 'source: "../assets/brand/techguy_mascot.png"' in main
    assert "techguy_mascot.png" not in glass
    assert "approvedMascotPanel" not in glass


def test_register_dialog_reserves_full_action_row() -> None:
    register = (DIALOGS / "RegisterDialog.qml").read_text(encoding="utf-8")
    # The historical 390 px dialog clipped the 48 px action buttons in the
    # deterministic visual renderer. Keep the corrected closeout geometry.
    assert "height: 440" in register
    assert 'text: "CANCEL"' in register
    assert 'text: "REGISTER DEVICE"' in register

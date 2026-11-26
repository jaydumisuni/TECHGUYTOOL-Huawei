[app]
title = TECHGUY TOOL Huawei
project_dir = .
input_file = main.py
exec_directory = dist
icon = assets/brand/techguy_huawei.ico

# frozen final release filename applied by build_windows.ps1 after pyside6-deploy = 
# techguytool_huawei.exe

[python]
python_path = D:\projects\THETECHGUY Software Builder - Installer Test\builder_cache\project-script-envs\TECHGUYTOOL-Huawei-3b4c4b642897cbaf\windows-exe\venv\Scripts\python.exe
packages = nuitka==2.6.8,ordered_set,zstandard

[qt]
qml_files = qml/Main.qml,qml/Theme.qml,qml/components/GlassPanel.qml,qml/components/GlowButton.qml,qml/components/NavItem.qml,qml/components/OperationTile.qml,qml/components/SectionLabel.qml,qml/components/StatusCard.qml,qml/components/ToggleRow.qml,qml/pages/ServiceCenterPage.qml,qml/pages/FirmwareFlashPage.qml,qml/pages/DeviceInformationPage.qml,qml/pages/PartitionManagerPage.qml,qml/pages/BackupRestorePage.qml,qml/pages/OperationHistoryPage.qml,qml/dialogs/SettingsMenu.qml,qml/dialogs/RegisterDialog.qml,qml/dialogs/DriverDialog.qml,qml/dialogs/AboutDialog.qml,qml/dialogs/TerminalDialog.qml,qml/dialogs/TestpointDialog.qml
excluded_qml_plugins = QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Qml,Quick,QuickControls2,Test
plugins = platforms,imageformats

[nuitka]
mode = onefile
extra_args = --quiet --msvc=latest --assume-yes-for-downloads --noinclude-qt-translations --include-data-dir=data=data --include-data-dir=assets=assets --include-data-dir=runtime=runtime --include-package=ttg_device_xray --include-package-data=ttg_device_xray --windows-console-mode=disable


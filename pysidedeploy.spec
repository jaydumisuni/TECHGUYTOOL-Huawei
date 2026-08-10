[app]
title = TECHGUY TOOL Huawei
project_dir = .
input_file = main.py
exec_directory = dist
icon = assets/brand/techguy_huawei.ico
# Frozen final release filename applied by build_windows.ps1 after pyside6-deploy:
# TECHGUYTOOL_Huawei.exe

[python]
python_path = python
packages = nuitka==2.6.8,ordered_set,zstandard

[qt]
qml_files = qml/Main.qml,qml/Theme.qml,qml/components/GlassPanel.qml,qml/components/GlowButton.qml,qml/components/NavItem.qml,qml/components/OperationTile.qml,qml/components/SectionLabel.qml,qml/components/StatusCard.qml,qml/components/ToggleRow.qml,qml/pages/ServiceCenterPage.qml,qml/pages/FirmwareFlashPage.qml,qml/pages/PlaceholderPage.qml,qml/dialogs/SettingsMenu.qml,qml/dialogs/RegisterDialog.qml,qml/dialogs/DriverDialog.qml,qml/dialogs/AboutDialog.qml,qml/dialogs/TerminalDialog.qml
excluded_qml_plugins = QtQuick3D,QtCharts,QtWebEngine,QtTest,QtSensors
modules = Core,Gui,Qml,Quick,QuickControls2
plugins = platforms,imageformats

[nuitka]
mode = onefile
extra_args = --quiet --msvc=latest --assume-yes-for-downloads --noinclude-qt-translations --include-data-dir=data=data --include-data-dir=assets=assets --include-data-dir=runtime=runtime --windows-console-mode=disable

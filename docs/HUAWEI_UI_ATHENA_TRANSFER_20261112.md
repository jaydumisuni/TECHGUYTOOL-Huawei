# Isolated Huawei UI integration candidate — 2026-11-12

Frontend: isolated KRATOS QML review candidate from
.workspace/workspaces/huawei-ui-redesign-20261111.
Target: ATHENA live-service backend worktree
work/huawei-live-service-bridge-20261111 (local HEAD 9a4c569).

Integrates no backend files. Core UI window defaults to 840x525 centered;
terminal starts at 370x180 and expands to 650x390, both centered.
The nine Service Center actions call backend.runAction once per click.
Terminal: submitTerminalLine / terminalOutput / confirmation and cancel.
Saved logs: openLogsFolder, logsFolderPath.
Pinouts: searchPinouts(Huawei/Honor,model,test-point/isp-pinout),
pinoutResultsJson, loadPinoutImage and pinoutImageJson, with
exact-model guards and local verified image URL.
Firmware APP/XML configuration is UI-only: no flash executor connected.
Current UI operation test evidence remains in the isolated KRATOS
workspace. Review must be completed on ATHENA with real backend before
any source/release promotion.

DO NOT copy techguy_huawei or release binaries from this transfer branch.

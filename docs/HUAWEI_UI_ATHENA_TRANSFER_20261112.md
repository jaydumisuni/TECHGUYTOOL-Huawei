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

## ATHENA integration evidence — 2026-11-12

Verified via Oracle Live **before ATHENA node disconnected**:

- ATHENA backend checkout:
  D:/projects/TECHGUYTOOL-Huawei/.workspace/worktrees/huawei-live-service-bridge,
  clean branch work/huawei-live-service-bridge-20261111 at 9a4c569. Actual
  terminal commit 828966a and TXT log commit 35d054e present.
- Isolated integration checkout:
  D:/projects/TECHGUYTOOL-Huawei/.workspace/worktrees/huawei-live-ui-review-20261112
  branch work/huawei-live-ui-review-20261112, based on 9a4c569, with
  staged 53c93d4 frontend QML/assets overlaid by git restore.
  Neither original dirty detached checkout nor original backend branch
  was overwritten.
- Existing seven ADB/Fastboot runtime files copied from ATHENA's clean
  service worktree to integration checkout and individually SHA256 verified.
  No new dependencies/downloads. Python 3.10.11 with PySide6 6.11.1.
- Real application started through integration checkout's
  run_athena_ui_review.py, pythonw PID 29516 and HWND 3217230 at last
  verification. Windows process responsive, native logical window
  840x525 at (348,146) on 1536x864 logical desktop (125% scaling).
  Actual app screenshot was captured with Win32 PrintWindow, not
  mistaken grabWindow output from EFT Pro behind it.
- Startup diagnostic:
  C:/Users/ATHENA 2.0/AppData/Local/Temp/TTG_Huawei_UI_ATHENA_LIVE_20261112.json.
  qml_root_ready, no QML warnings.
- Offscreen real-backend smoke file:
  D:/projects/TECHGUYTOOL-Huawei/.workspace/worktrees/huawei-live-ui-review-20261112/athena_live_backend_smoke.py.
  QtTest mouse click on actual Read Device control dispatched
  backend.runAction(read_device); async service worker began and finished;
  a dated TXT report was created at
  C:/ProgramData/THETECHGUY/Huawei/Logs/2026-11-12/...
  specifically 2026-11-12_04-26-15_READ_DEVICE_ba29e5d9.txt (3303 bytes).
  Validated terminal, logs, trusted pinout backend method availability.
  Firmware execution UI remains disabled. No hardware writes.
  Proof: C:/Users/ATHENA 2.0/AppData/Local/Temp/
  TTG_Huawei_ATHENA_REAL_UI_SMOKE_20261112.json.
- Read-device result was **NOT successful discovery**: Windows PowerShell
  USB enumeration path timed out after 15 seconds. It completed worker
  and durable logs, not device detection. Windows had 195 present PnP
  devices; enumeration 2.244 seconds; two relevant Ports/WPD interfaces.
  Batched single-call PnP property retrieval per device measured around
  1.456 and 1.487 seconds and is a promising read-only optimization.
  **No USB source patch has been verified applied.**
- A Windows 'We've got an update for you' modal/ScreenDim was intercepting
  native pointer clicks. It was NOT dismissed; the offscreen QtTest
  method was used to verify real QML/backend button dispatch.
- ATHENA Oracle node desktop-52e996b112a609de1d49b7cddbd548ad
  subsequently reported LIVE_NODE_OFFLINE. Do not assume GUI still
  running or source patch applied until reconnect and recheck.
- ATHENA live GUI had a temporary Win32 topmost flag set for visibility.
  **On reconnect restore HWND_NOTOPMOST before handing control to user**.

Still required before acceptance or promotion:
1. Reconnect ATHENA; verify integration files/process, original git safety.
2. Restore normal window z-order (remove temporary topmost flag).
3. Correct/batch USB PnP property collection in **integration** worktree
   only, preserving evidence fields and same physical-device identity gates.
4. Re-run actual Windows device detection, real QML smoke and TXT audit.
5. Inspect pinout search and exact-match behavior on real backend.
6. Review all six tabs, terminal, flash (preflight only), on ATHENA.
7. Commit reviewed integration branch if accepted; do not transplant into
   dirty primary checkout or build production EXE without approval.

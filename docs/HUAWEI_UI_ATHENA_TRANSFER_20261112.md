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

## ATHENA main source replacement — verified 2026-11-12

Owner approved replacing the main Huawei source frontend. After ATHENA Oracle
reconnected, the main tool was replaced and verified:

- Main source root: D:/projects/TECHGUYTOOL-Huawei
  (existing detached HEAD 114f2c2).
- UI QML/assets came from reviewed candidate 53c93d4. Python service backend
  came from latest clean ATHENA live-service branch at 67d4942.
- Exactly 167 source files were added/replaced with SHA256 content verification.
  The original README, ROADMAP, build spec, resource inventory, resources.qrc
  and untracked resources_rc.py were preserved with all prior dirty changes.
- Main source app.py loader (main.py) now loads filesystem QML first in source
  mode, so old compiled resources_rc does not shadow the replaced UI.
- Rollback archive (2,138,267 bytes):
  D:/projects/TECHGUYTOOL-Huawei/.workspace/recovery/
  20261112_main_huawei_ui_backend_swap_rollback.zip
  and corresponding 20261112_main_huawei_ui_backend_swap_manifest.json.
- Main Pythonw process PID 19176 (at check) launched and was responsive;
  actual Windows window 840x525 logical pixels, centered, not topmost;
  diagnostic qml_root_ready with zero QML warnings.
- Reused existing shared C:/Program Files/platform-tools ADB/Fastboot.
  No downloads, installs or unrelated project writes.
- Corrected Windows USB read-only PnP property retrieval by batching the same
  seven keys, reducing ATHENA collection to about 3.616 seconds. Source test:
  20 USB/discovery tests plus 39 terminal/pinout/service contract tests passed.
- QtTest click on real Read Device UI dispatched actual async backend. A
  durable TXT log was saved. Connected device reported Huawei Kirin 980 via
  Fastboot, exact model/build unresolved. No device writes.
- APP/XML Flash START remains disabled until actual verified executor exists.
- One-click project-local launcher added:
  D:/projects/TECHGUYTOOL-Huawei/Launch Huawei Tool.cmd
  and tools/launch_huawei_main.ps1.
  It did not spawn a duplicate while app was already running.
- Proof: D:/projects/TECHGUYTOOL-Huawei/.workspace/evidence/
  20261112_main_swap_verification.json and
  20261112_main_ui_backend_smoke.json.
- Task-owned pytest temporary directories cleaned.
- Source replacement complete; packaged/distributable EXE was NOT rebuilt.
  Source inventory and QRC packaging remain at prior preserved state.

## ATHENA intermittent console window correction — 2026-11-12

Symptom: After promoting the compact Huawei source UI to ATHENA, the owner
noticed a Windows terminal/console window briefly flashing from time to time.

Evidence traced:
- Actual main backend Backend.__init__ creates a 5-second health timer.
- Every twelfth heartbeat (~60 seconds), Backend._heartbeat triggers
  _audit_runtime_wiring; it also runs once at initial startup.
- HealthAuditWorker.run used subprocess.run on the native Rust
  runtime/health/techguy_health_core.exe without CREATE_NO_WINDOW.
- The secondary ActionRegistry.run_rust_audit path likewise lacked it.
- ADB/Fastboot, PowerShell USB discovery and USB descriptor query paths
  already use CREATE_NO_WINDOW. No need to change device operations.
- The console flash itself was not captured with a PID. This is a
  source-confirmed likely cause matching the periodic timing, not proof
  that other Windows applications can never spawn their own consoles.

Changes applied **in the current ATHENA main source**:
- techguy_huawei/desktop_worker.py:
  supply creationflags=subprocess.CREATE_NO_WINDOW on Windows to periodic
  health worker subprocess.run, preserving output capture and timeout.
- techguy_huawei/action_health.py:
  same flag for the alternate audit entry point.
- tests/test_health_audit_console.py:
  add regression tests proving the hidden-window creation flag is passed
  and both workers retain successful audit output.
- No QML, terminal UI, device write commands or firmware services altered.

Proof on ATHENA:
- 22 focused tests passed, including both console regression tests,
  backend action log tests, async worker tests and terminal/read tests.
- The actual native Rust health executable launched with the no-console
  creation flag, returned exit code 0 and audited 13 actions in ~0.021s.
- Main Huawei source application was safely restarted: previous PID 19176
  closed, new pythonw PID 6720 started through approved project launcher.
- One native main Huawei window remains open at 840x525, topmost disabled,
  with no QML startup warnings. No device write action performed.
- Only task-owned pytest temporary material (~736 bytes) removed.

Rollback:
D:/projects/TECHGUYTOOL-Huawei/.workspace/recovery/
20261112_health_audit_console_fix/{desktop_worker.py,action_health.py,manifest.json}

Updated evidence in:
D:/projects/TECHGUYTOOL-Huawei/.workspace/evidence/
20261112_main_swap_verification.json

Completion classification: corrective source update + source/behavior
verification, not yet a production EXE rebuild. Main checkout remains
intentionally dirty to preserve owner's pre-existing edits.

## Pinout viewer and gear placement — ATHENA proof 2026-11-12

User clarified this is about the **tool-side pinout image UX**, not changing
the pinout site's publishing architecture. The Finder stays unchanged.

Recovered actual source:
- D:/projects/testpoints-verse, branch main, private data and images organized
  under test-points/ and isp-pinouts/; origin is GitHub.
- The project's finder/README.md establishes private GitHub source/archive,
  Firebase Hosting for base catalogue/images, Cloudflare custom-domain gateway,
  protected live additions and opaque image URLs.
- At inspection, https://pinout.thetechguyds.com/catalog.json returned a live
  Cloudflare-served ttg-pinout-finder-v1 catalogue with 3,389 records, 736
  Huawei/Honor records and ~793 KB response data.
- Direct GitHub image retrieval was rejected: it would duplicate the site
  index/credential concerns, weaken provenance controls and is not inherently
  faster. Huawei Backend -> PinoutProvider already caches its catalogue for
  six hours and only downloads selected, membership-validated WebP images,
  caching those locally for repeat opens.
- Read-only real test: query Huawei "VOG-AL00" test-point returns exact
  "P30 PRO VOG AL00", one exact and one browse-only alternative. Image
  3947433f28164c8983fcb4cd.webp, 1024x576, 73,374 bytes, fetched
  in ~0.406 seconds, Qt WebP decoder succeeded. Re-fetch from cache was
  proven with networking explicitly blocked in the test.
- QML TestpointDialog now normalizes punctuated model codes before presenting
  backend results, preserving matches like VOG-AL00 versus VOG AL00;
  a sole authoritative exact match auto-selects its verified image.
  Backend-triggered popup invokes real trusted search rather than stopping
  at a local metadata-only profile.
- New PinoutImageViewer.qml is a separate, user-enlargeable Qt window;
  real cached image can be opened by clicking its preview or ENLARGE/ZOOM.
  Features: wheel/+/− zoom, 100%-pixel size, Fit, drag-pan, maximize/restore,
  close, and multi-image PREV/NEXT in source popup.
- Removed the entire "OPERATION RESUME STATE" and "EXPECTED SERVICE
  INTERFACE" panels and all visible operating-resume messaging. Internal
  openForOperation(modelId, label) compatibility remains to prepopulate the
  model, but does not display operation-control text in this image viewer.
- Real ATHENA Backend end-to-end QtTest proof:
  search VOG-AL00 -> exact match -> image read from ProgramData local cache ->
  enlarge -> zoom factor 1.25 -> fit -> actual pixels -> drag pan ->
  maximize -> restore -> close, zero QML warnings and zero device commands.
  Evidence on ATHENA:
  .workspace/evidence/verify_pinout_zoom_live_20261112.py
  .workspace/evidence/20261112_pinout_zoom_live_report.json
  .workspace/evidence/20261112_pinout_viewer_real_image.png.
- Gear menu had previously extended ~39px outside compact right boundary.
  Corrected settings anchor to reference-canvas local point and applied actual
  UI scaling; removed offsets from About, Fix Drivers and Register dialogs.
  Geometric QML probe verified all six popups wholly inside 840x525 and
  1536x864 windows, centred dialogs and gear menu aligned to gear button
  right edge. Evidence:
  .workspace/evidence/gear_popup_geometry_probe.py
  .workspace/evidence/popup_*.png.

**Critical current status at handoff:** ATHENA Oracle node went offline after
a supplementary test for a record with multiple images stalled. Thus the
two-image carousel's live test is UNCONFIRMED, and the open Huawei process
has NOT been restarted to pick up the latest changed QML. Do not claim a
live-window deployment of this subsequent update until ATHENA reconnects,
the app safely restarts and native GUI geometry/viewer are rechecked.

Source edits reside in the existing ATHENA main source checkout only:
qml/Main.qml, qml/dialogs/AboutDialog.qml, DriverDialog.qml,
RegisterDialog.qml, TestpointDialog.qml and newly added
qml/dialogs/PinoutImageViewer.qml.
Recovery originals:
.workspace/recovery/20261112_gear_popup_geometry/
.workspace/recovery/20261112_pinout_viewer/
The owner-approved main tool's earlier backend integration is unchanged,
and no device writes were made during these image-UI tests.


## ATHENA terminal filesystem navigation — 2026-11-12

Owner requested local directory navigation inside Huawei's integrated
ADB/Fastboot terminal, preserving the approved confirmation flow.

Implementation in ATHENA main SOURCE (not packaged EXE):
- cd, cd /d "C:\firmware folder", cd .., pwd, dir, ls. Quoted
  Windows paths, spaces, other drives, parent and relative paths work.
- Directories are scoped per terminal session, never via global os.chdir.
  Builtins do not spawn cmd.exe, PowerShell or arbitrary shell commands.
- ADB/Fastboot subprocesses use the selected cwd and existing trusted
  platform tools, allowing user-selected relative firmware filenames.
- The confirmation fingerprint binds the exact working directory.
  Changing directory cancels a pending write approval. Device serial
  checks, explicit confirmation and audit logging are retained.
- Initial terminal view remains a lone dash, with cwd displayed only
  after the first command. Transcript scrollback is preserved.

Main source touched:
techguy_huawei/terminal_directory.py
techguy_huawei/backend.py
techguy_huawei/terminal_engine.py
techguy_huawei/service_dispatch.py
techguy_huawei/device_engine.py
qml/dialogs/TerminalDialog.qml
tests/test_terminal_directory.py

Verification on ATHENA:
- 49 focused tests passed, including existing terminal write,
  read-device, async worker and auditing contracts.
- Read-only adb version and fastboot --version executed from
  C:/Program Files/platform-tools; each produced a durable log
  recording the command's working directory.
- Offscreen rendered Qt test at 840x525 passed initial dash,
  cross-drive cd, directory listing, history and bounded expand,
  with zero QML warnings.
- Prepared fastboot flash was NOT executed; changing directories
  cleared pending confirmation.
- Main source application restarted, ATHENA PID 26212 at proof,
  centered 840x525 and responsive, zero startup QML errors.
- No hardware writes; distributable EXE was NOT rebuilt.

Proof files in main project's .workspace/evidence:
20261112_terminal_directory_acceptance.json
20261112_terminal_directory_real_report.json
20261112_terminal_qml_navigation.json

Recovery snapshot: .workspace/recovery/20261112_terminal_directory.
The existing pinout viewer and popup corrections remain source-level
changes on ATHENA; the pinout website/repository was not modified.


## ATHENA integrated terminal prompt and shared Builder Support — 2026-11-12

The Huawei main source was updated on ATHENA after direct owner feedback:

- Terminal now has an actual command input row **inside the same black
  output panel**. Initial view contains a single interactive dash; no
  fabricated transcript banner. Existing scrollback, directory navigation,
  guarded ADB/Fastboot execution and explicit write confirmation retained.
- Redundant native Minimize/Maximize titlebar controls removed by Dialog
  customization; tool Expand/Compact stays, bounded to the screen.
- Offscreen Qt image capture of compact terminal 370x180 completed and
  was visually reviewed; zero QML warnings. Exact capture:
  D:/projects/TECHGUYTOOL-Huawei/.workspace/evidence/
  20261112_terminal_integrated_prompt.png.
- User requested a **single shared installed Support root** at
  C:/Program Files (x86)/THETECHGUY Digital Solutions/Support, holding
  Android/platform-tools, future Drivers and manifests. This is a
  **Builder-owned installer capability**, not a Huawei-only copy.
- Huawei source platform_tools.py will consume Builder-provisioned ADB
  and Fastboot only with a valid exact SHA-256 manifest covering all
  installed files; fallback to its existing trusted runtime locations
  remains until that support package is actually installed.
- Huawei's techguy-build.json explicitly declares Android support
  version 37.0.1 with a Builder-managed dependency cache source.
- The canonical Builder source has an opt-in self-contained installer
  package flow, reuse/explicit repair, checksum checks, rollback on
  app-install failure, and no uninstall of global Support.
- On ATHENA, Builder cached the existing platform-tools 37.0.1 source
  (14 files, 17,529,398 bytes). No existing Program Files tool or
  driver was moved, deleted or overwritten, and the new Support
  directory was not installed.
- Focused tests: Builder **17 passed**; Huawei **53 passed**.
  Builder full suite from correct root: **555 passed, 9 skipped, 4
  unrelated failures** (browser installer contract, 2 Windows Git
  test fixtures, stale physical standalone receipt). No claim of
  full-green Builder proof.
- Builder review branch:
  github.com/jaydumisuni/thetechguy-software-builder/tree/
  work/shared-support-installer-20261112
  latest merged commit 36f05d1ab1b74e64794e82e4744bb1996040a4a7.
- Local source documents:
  D:/projects/THETECHGUY Software Builder/docs/
  SHARED_SUPPORT_WINDOWS_INSTALLER.md
  D:/projects/TECHGUYTOOL-Huawei/docs/
  HUAWEI_TERMINAL_AND_SHARED_SUPPORT_20261112.md.
- Rollback snapshots:
  D:/projects/TECHGUYTOOL-Huawei/.workspace/recovery/
  20261112_terminal_embedded_prompt and
  20261112_shared_support_preference.
- Current main Huawei checkout is intentionally dirty due to
  previously preserved owner edits. Do not blindly commit or stage
  unrelated files. No production Huawei EXE/Setup was rebuilt.

Release gating remains a real one-file installer build, physical Windows
UAC install/reuse/repair/uninstall validation, vendor provenance checks,
resolution/acceptance of Builder test failures and owner promotion approval.


### Final source handoff: single Builder review branch

Builder's canonical shared Support source implementation was reconciled
with the earlier review commit rather than leaving duplicate branches.
The **single** review branch is now:

  https://github.com/jaydumisuni/thetechguy-software-builder/tree/work/shared-support-installer-20261112

Verified latest merge commit:
  36f05d1ab1b74e64794e82e4744bb1996040a4a7

The merged source tree matches the tested ATHENA Builder commit exactly.
The redundant work/shared-support-windows-installer-20261112 branch
(created during reconciliation) was deleted after the merge was pushed.

Updated focused Builder support/onefile staging tests: **17 passed**.
The actual Huawei configuration staged 14 platform-tools 37.0.1 files
(17,529,398 bytes) from Builder's gitignored cache; all hashes matched.
The temporary staging was removed. An explicit administrator/UAC
packaging guard prevents a shared Program Files install through an
installer configured without admin privileges.

ATHENA correct-root Builder full regression also recorded **557 passed,
9 skipped, 2 failed** (baseline legacy browser-uninstaller contract and
historical standalone physical receipt). An earlier run recorded
555 passed / 9 skipped / 4 failed, including two transient Git fixture
failures. This is not full-green customer installer qualification.

Huawei terminal's integrated command prompt displays **only a dash**
inside the black output area; ScrollView/history and cd / pwd / dir / ls
work, tool-owned ADB/Fastboot paths remain default, and native popup
minimize/maximize controls were removed while Expand/Compact remains.
Final QML terminal smoke passed without startup warnings, and no
device write occurred. The on-demand exact-model pinout image viewer
was also validated with VOG-AL00 and Nova 3 image navigation.

Current ATHENA source documentation was updated in place:
- Huawei README.md
- Builder PROJECT_STATE.md and docs/SHARED_SUPPORT_WINDOWS_INSTALLER.md

No installed Support package, signed driver, application Setup EXE or
production distribution was created or promoted in this work.

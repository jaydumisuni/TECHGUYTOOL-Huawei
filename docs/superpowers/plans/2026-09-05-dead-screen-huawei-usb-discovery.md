# Dead-Screen Huawei USB Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect and classify a connected Huawei from Windows USB/PnP evidence without requiring a working screen, keep unrelated Android devices isolated, and publish the read-only observation through the existing Gateway contract.

**Architecture:** A pure classifier consumes normalized USB observations. A Windows collector supplies those observations through fixed PowerShell argv execution. `DeviceEngine` consults Huawei USB identity before generic ADB/Fastboot acceptance, and the existing Gateway physical-session/endpoint API records the public observation.

**Tech Stack:** Python 3.11, Windows PowerShell/PnP cmdlets, existing TTG Device Gateway JSON-lines API, pytest.

**Spec:** `docs/superpowers/specs/2026-09-05-dead-screen-huawei-usb-discovery-design.md`

## Global Constraints

- No device writes, USB control transfers, mode forcing, flashing, driver replacement, loader transfer, or partition access.
- `12D1:107E` never implies an exact Huawei model by itself.
- Raw device serials stay out of tracked source, matrix records, and Gateway payloads.
- Every discovery result keeps `device_modification="none"` and `write_authority="none"`.
- Multiple Huawei devices fail closed as guarded ambiguity.
- Reuse the existing Gateway session/endpoint contract; no parallel session architecture.
- Packaging and production enablement remain out of scope.

---

### Task 1: Pure Huawei USB classification and continuity

**Files:**
- Create: `techguy_huawei/usb_discovery.py`
- Create: `tests/test_usb_discovery.py`

**Interfaces:**
- Produces: `UsbObservation.from_mapping(value) -> UsbObservation`
- Produces: `discover_huawei_usb(observations) -> UsbDiscoveryReport`
- Produces: `UsbDiscoveryReport.to_dict() -> dict[str, object]`

- [ ] **Step 1: Write failing storage-only/privacy tests**

```python
def test_107e_storage_only_is_pre_service_without_model_inference():
    report = discover_huawei_usb(storage_only_fixture())
    assert report.state == "storage_only_pre_service"
    assert report.model == "identity_pending"
    assert report.write_authority == "none"
    assert report.screen_required is False


def test_public_payload_omits_private_serial():
    report = discover_huawei_usb(storage_only_fixture(serial="PRIVATE-SERIAL"))
    assert "PRIVATE-SERIAL" not in repr(report.to_dict())
```

- [ ] **Step 2: Run `python -m pytest -q tests/test_usb_discovery.py` and confirm RED**

Expected: module import failure.

- [ ] **Step 3: Implement immutable normalized observations/report**

```python
@dataclass(frozen=True, slots=True)
class UsbObservation:
    instance_id: str
    class_name: str
    friendly_name: str
    device_desc: str
    bus_reported_desc: str
    manufacturer: str
    hardware_ids: tuple[str, ...]
    compatible_ids: tuple[str, ...]
    container_id: str
    parent_instance_id: str

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
```

Classifier precedence: `huawei_usb_com_1_0`, `upgrade_mode`, `normal_fastboot`, `recovery`, `adb`, `mtp`, `storage_only_pre_service`, `unknown_huawei`. Group Huawei observations by container/serial continuity. Two physical Huawei groups emit `multiple_huawei_devices`.

- [ ] **Step 4: Add Redmi-isolation and ambiguity regressions**

```python
def test_redmi_adb_does_not_change_huawei_identity():
    report = discover_huawei_usb(storage_only_fixture() + redmi_adb_fixture())
    assert report.vid == "12D1"
    assert report.state == "storage_only_pre_service"


def test_two_huawei_devices_fail_closed():
    report = discover_huawei_usb(two_huawei_fixture())
    assert report.state == "multiple_huawei_devices"
```

- [ ] **Step 5: Run focused tests and commit**

Expected: PASS.  
Commit: `feat(huawei): classify dead-screen USB states`

---

### Task 2: Windows collector and proof CLI

**Files:**
- Create: `techguy_huawei/windows_usb.py`
- Create: `tools/discover_huawei_usb.py`
- Create: `tests/test_windows_usb.py`

**Interfaces:**
- Consumes: `discover_huawei_usb()`
- Produces: `collect_windows_usb_observations(*, runner=subprocess.run)`
- Produces: `discover_windows_huawei_usb(*, runner=subprocess.run)`

- [ ] **Step 1: Write failing injected-runner test**

```python
def test_collector_uses_fixed_powershell_argv_without_shell():
    calls = []
    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, fixture_json(), "")
    report = discover_windows_huawei_usb(runner=runner)
    assert report.state == "storage_only_pre_service"
    assert calls[0][1]["shell"] is False
```

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest -q tests/test_windows_usb.py`.

- [ ] **Step 3: Implement fixed PowerShell collection**

Invoke:

```python
subprocess.run(
    [powershell, "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_DISCOVERY_SCRIPT],
    shell=False,
    check=False,
    capture_output=True,
    text=True,
    timeout=15,
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
)
```

Return structured errors `USB_DISCOVERY_UNAVAILABLE` and `USB_DISCOVERY_INVALID` for execution/JSON failures.

- [ ] **Step 4: Implement `tools/discover_huawei_usb.py`**

Print sorted JSON. `--output` must resolve below repository `proof/`; reuse `validate_proof_output_path`.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest -q tests/test_windows_usb.py tests/test_usb_discovery.py`.  
Commit: `feat(huawei): collect Windows USB discovery evidence`

---

### Task 3: DeviceEngine identity anchoring

**Files:**
- Modify: `techguy_huawei/device_engine.py`
- Modify: `tests/test_device_engine.py`

**Interfaces:**
- Consumes: `discover_windows_huawei_usb()`
- Produces: `DeviceEngine.probe()` payload field `usb_discovery`

- [ ] **Step 1: Write current-live-scenario regression**

```python
def test_probe_prefers_huawei_storage_identity_over_unrelated_redmi_adb(monkeypatch, tmp_path):
    subject = engine(tmp_path)
    monkeypatch.setattr(device_engine, "discover_windows_huawei_usb", lambda: storage_report())
    monkeypatch.setattr(subject, "_run", fake_redmi_adb_run)
    result = subject.probe()
    assert result.ok is True
    assert result.payload["interface"] == "Huawei USB / Pre-service"
    assert result.payload["usb_discovery"]["state"] == "storage_only_pre_service"
```

- [ ] **Step 2: Confirm RED**

Run the exact new test.

- [ ] **Step 3: Integrate Windows Huawei discovery first**

For one storage/pre-service Huawei, return a read-only snapshot:

```text
connected=True
interface="Huawei USB / Pre-service"
platform="Huawei USB"
security="Read-only / identity pending"
model="Huawei device (identity pending)"
```

For multiple Huawei groups return `ActionState.GUARDED`. Do not accept unrelated ADB/Fastboot rows as the Huawei while Huawei PnP identity exists.

- [ ] **Step 4: Add no-Huawei arbitrary-ADB regression**

On Windows, generic ADB alone must be manufacturer-verified read-only before becoming Huawei; Redmi/other manufacturers return no-Huawei.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest -q tests/test_device_engine.py tests/test_usb_discovery.py tests/test_windows_usb.py`.  
Commit: `fix(huawei): anchor probing to Huawei USB evidence`

---

### Task 4: Gateway endpoint publication

**Files:**
- Modify: `techguy_huawei/gateway_client.py`
- Modify: `tests/test_gateway_client.py`
- Modify: `tools/discover_huawei_usb.py`

**Interfaces:**
- Produces: `GatewayClient.usb_discovery_endpoint_payload(report)`
- Produces: `GatewayClient.record_usb_discovery(report)`

- [ ] **Step 1: Write privacy/authority regression**

```python
def test_usb_discovery_gateway_payload_is_read_only_and_private():
    payload = GatewayClient.usb_discovery_endpoint_payload(storage_report().to_dict())
    assert payload["write_authority"] == "none"
    assert payload["device_modification"] == "none"
    assert "serial" not in payload
```

- [ ] **Step 2: Confirm RED**

Run exact test.

- [ ] **Step 3: Implement existing-session publication**

Use `open_physical_session(fingerprint_sha256)` then `record_endpoint(...)` with:

```text
endpoint_key="huawei-usb:<fingerprint-prefix>"
mode=<state>
transport="windows_pnp_usb"
payload=<public report>
```

- [ ] **Step 4: Add opt-in CLI publication**

`--publish-gateway` attempts publication but does not turn Gateway unavailability into a discovery failure.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest -q tests/test_gateway_client.py tests/test_windows_usb.py`.  
Commit: `feat(gateway): record Huawei USB discovery endpoints`

---

### Task 5: Certification row and recovery docs

**Files:**
- Modify: `techguy_huawei/windows_release.py`
- Modify: `manifests/phase15_physical_proof_matrix.json`
- Modify: `tests/test_windows_release.py`
- Modify: `ROADMAP.md`
- Modify: `README.md`
- Modify: `docs/PHASE_3_DEVICE_GATEWAY.md`

**Interfaces:**
- Adds matrix id: `dead_screen_pre_service_usb_discovery`

- [ ] **Step 1: Add failing matrix-row test**

```python
def test_matrix_requires_dead_screen_pre_service_usb_discovery():
    rows = {row["id"]: row for row in load_matrix()["entries"]}
    assert rows["dead_screen_pre_service_usb_discovery"]["status"] in {
        "HARDWARE_PENDING", "PHYSICAL_PASS"
    }
```

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest -q tests/test_windows_release.py -k dead_screen`.

- [ ] **Step 3: Add row and required-id authority as `HARDWARE_PENDING`**

Document that the row certifies detection/classification only and grants no model or repair authority.

- [ ] **Step 4: Update docs**

README must stop naming owner-machine proof as the next milestone. Roadmap and Phase 3 docs must record read-only live USB discovery and dead-screen routing as the current physical coverage correction.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest -q tests/test_windows_release.py tests/test_repository_contracts.py`.  
Commit: `docs(huawei): define dead-screen USB certification boundary`

---

### Task 6: Live physical proof, freeze, review, merge

**Files:**
- Ignored: `proof/physical/dead_screen_pre_service_usb_discovery/<run>/...`
- Modify after review: `manifests/phase15_physical_proof_matrix.json`
- Modify: `manifests/source_inventory.json`

- [ ] **Step 1: Run live ATHENA discovery**

Use Builder Python 3.11:

```text
tools/discover_huawei_usb.py --output proof/physical/dead_screen_pre_service_usb_discovery/<run>/discovery.json
```

Expected: `present=true`, `vid=12D1`, `pid=107E`, `state=storage_only_pre_service`, `screen_required=false`, `write_authority=none`.

- [ ] **Step 2: Prove Redmi separation**

Capture `adb devices -l` simultaneously. The Redmi serial must not appear in Huawei public discovery JSON or Gateway payload.

- [ ] **Step 3: Generate physical evidence packet**

Create ignored `subject.json` containing the raw Huawei USB identity and run `tools/record_physical_proof.py` for entry `dead_screen_pre_service_usb_discovery`, binding the live discovery and PnP capture. Confirm packet validation and confirm raw serial is absent from packet JSON.

- [ ] **Step 4: Promote only the proven row**

If evidence satisfies the spec, set only `dead_screen_pre_service_usb_discovery` to `PHYSICAL_PASS` with its evidence binding. Leave MTP/ADB/Fastboot/Recovery/Upgrade/Testpoint/repair rows unchanged.

- [ ] **Step 5: Freeze source authority**

Commit source/matrix changes, run `tools/build_source_inventory.py`, verify only `manifests/source_inventory.json` changes, run `tools/verify_source_freeze.py`, then commit the inventory child.

- [ ] **Step 6: Complete verification**

```text
python -m pytest -q
python tools/review_20_for_2.py --strict
python tools/verify_source_freeze.py
git diff --check
```

All must pass on the exact final head.

- [ ] **Step 7: PR and independent review**

Push `feature/dead-screen-usb-discovery`, open a focused PR, inspect CodeRabbit/security/source/UI checks, fix real findings, and cancel long packaging after source/Windows test proof if it starts.

- [ ] **Step 8: Merge and cleanup**

Merge only after exact-head proof. Verify merged tree identity, keep the Phase 15 package receipt `UNFROZEN`, and remove the feature worktree/branch only after ancestry is proven.

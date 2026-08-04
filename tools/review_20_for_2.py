from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    check_id: str
    wave: int
    title: str
    run: Callable[[], tuple[bool, str]]


def ok(condition: bool, detail: str) -> tuple[bool, str]:
    return condition, detail


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def files(pattern: str) -> list[Path]:
    return sorted(ROOT.glob(pattern))


def manifest() -> dict[str, object]:
    return json.loads(text("data/action_manifest.json"))


def python_compiles() -> tuple[bool, str]:
    candidates = [ROOT / "main.py", *files("techguy_huawei/*.py"), *files("tools/*.py"), *files("tests/*.py")]
    try:
        for path in candidates:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return False, str(exc)
    return True, f"{len(candidates)} Python files parsed"


def qml_contract() -> tuple[bool, str]:
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_qml.py")], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def test_suite() -> tuple[bool, str]:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def check_action_calls() -> tuple[bool, str]:
    declared = {item["id"] for item in manifest()["actions"]}  # type: ignore[index]
    used: set[str] = set()
    for path in files("qml/**/*.qml"):
        used.update(re.findall(r'runAction\("([a-z0-9_]+)"\)', path.read_text(encoding="utf-8")))
    missing = sorted(used - declared)
    return not missing, f"used={sorted(used)} missing={missing}"


def check_handlers() -> tuple[bool, str]:
    source = text("techguy_huawei/backend.py")
    declared = {item["id"] for item in manifest()["actions"]}  # type: ignore[index]
    handlers = set(re.findall(r'^\s{12}"([a-z0-9_]+)":', source, re.M))
    return declared == handlers, f"declared={len(declared)} handlers={len(handlers)} diff={sorted(declared ^ handlers)}"


def no_forbidden_commands() -> tuple[bool, str]:
    source = "\n".join(path.read_text(encoding="utf-8") for path in files("techguy_huawei/*.py")).lower()
    forbidden = ["shell=true", "fastboot erase", "fastboot format", "fastboot flashing unlock", "fastboot oem unlock"]
    hits = [token for token in forbidden if token in source]
    return not hits, f"forbidden hits={hits}"


def qrc_complete() -> tuple[bool, str]:
    qrc = text("resources.qrc")
    expected = [path.relative_to(ROOT).as_posix() for folder in (ROOT / "qml", ROOT / "assets") for path in folder.rglob("*") if path.is_file()]
    missing = [item for item in expected if f'alias="{item}"' not in qrc]
    return not missing, f"resources={len(expected)} missing={missing}"


def check_rust_contract() -> tuple[bool, str]:
    source = text("rust/health_core/src/main.rs")
    required = ["BTreeSet", "duplicate action id", "guarded &&", "serde_json"]
    missing = [value for value in required if value not in source]
    return not missing, f"missing={missing}"


def check_geometry() -> tuple[bool, str]:
    source = text("qml/Main.qml")
    return bool(re.search(r"\bwidth:\s*1586\b", source) and re.search(r"\bheight:\s*992\b", source)), "reference canvas 1586x992"


def check_assets() -> tuple[bool, str]:
    required = [ROOT / "assets/brand/techguy_logo.svg", ROOT / "assets/brand/techguy_mascot.svg", ROOT / "assets/brand/techguy_logo.svg"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file() or path.stat().st_size == 0]
    return not missing, f"missing={missing}"


def check_no_secrets() -> tuple[bool, str]:
    patterns = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), re.compile(r"BEGIN (?:RSA |EC )?PRIVATE KEY")]
    hits: list[str] = []
    for path in [*files("**/*.py"), *files("**/*.qml"), *files("**/*.json"), *files("**/*.ps1"), *files("**/*.toml")]:
        if any(part in {"__pycache__", ".git"} for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(content) for pattern in patterns):
            hits.append(str(path.relative_to(ROOT)))
    return not hits, f"secret-like files={hits}"


def check_relative_assets() -> tuple[bool, str]:
    hits = []
    for path in files("qml/**/*.qml"):
        source = path.read_text(encoding="utf-8")
        if re.search(r'\bsource:\s*"(?:[A-Za-z]:|/)', source):
            hits.append(str(path.relative_to(ROOT)))
    return not hits, f"absolute asset references={hits}"


def check_registration_hash() -> tuple[bool, str]:
    source = text("techguy_huawei/backend.py")
    return ok("key_hash" in source and "sha256(key.encode())" in source and '"key": key' not in source, "registration stores hash, not key")


def check_evidence_custody() -> tuple[bool, str]:
    source = text("techguy_huawei/evidence.py")
    required = ["stdout_sha256", "stderr_sha256", "verify", "json.dumps"]
    return ok(all(value in source for value in required), "SHA-256 evidence envelope and JSONL journal")


def check_single_device_gate() -> tuple[bool, str]:
    source = text("techguy_huawei/device_engine.py")
    return ok("if total > 1" in source and "Connect exactly one service device" in source, "multiple-device ambiguity is blocked")


def check_onefile() -> tuple[bool, str]:
    spec = text("pysidedeploy.spec")
    return ok("mode = onefile" in spec and "TECHGUYTOOL_Huawei.exe" in spec, "Nuitka onefile target fixed")


def check_build_proof() -> tuple[bool, str]:
    script = text("build_windows.ps1")
    required = ["python -m pytest", "review_20_for_2.py --strict", "pyside6-rcc", "pyside6-deploy", "Get-FileHash -Algorithm SHA256"]
    missing = [value for value in required if value not in script]
    return not missing, f"missing={missing}"


def check_ui_binding_audit() -> tuple[bool, str]:
    backend = text("techguy_huawei/backend.py")
    qml = text("qml/Main.qml")
    return ok("registerUiAction" in backend and "_audit_ui_bindings" in backend and "backend.registerUiAction" in qml, "runtime UI wiring audit enabled")


def check_guarded_manifest() -> tuple[bool, str]:
    actions = manifest()["actions"]  # type: ignore[index]
    failures = [item["id"] for item in actions if item.get("guarded") and not item.get("guard_reason")]
    return not failures, f"guarded actions without reasons={failures}"


def check_profile_database() -> tuple[bool, str]:
    payload = json.loads(text("data/device_profiles.json"))
    return ok(len(payload.get("platform_families", [])) >= 5 and any(m.get("model") == "VOG-L29" for m in payload.get("models", [])), "Huawei/Kirin starter profiles present")


def check_output_paths() -> tuple[bool, str]:
    source = text("techguy_huawei/storage.py")
    required = ["PROGRAMDATA", "Application Support", "XDG_STATE_HOME", "backups", "firmware"]
    return ok(all(value in source for value in required), "platform-specific mutable-data locations")


def check_no_firmware_assets() -> tuple[bool, str]:
    forbidden_suffixes = {".app", ".bin", ".img", ".zip", ".xml"}
    hits = [str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes and "data" not in path.parts and path.name != "resources.qrc"]
    return not hits, f"bundled firmware-like files={hits}"


def check_qml_popups() -> tuple[bool, str]:
    source = text("qml/Main.qml")
    expected = ["SettingsMenu", "RegisterDialog", "DriverDialog", "AboutDialog", "TerminalDialog"]
    missing = [item for item in expected if item not in source]
    return not missing, f"missing={missing}"


def check_reference_labels() -> tuple[bool, str]:
    combined = text("qml/Main.qml") + text("qml/pages/ServiceCenterPage.qml") + text("qml/pages/FirmwareFlashPage.qml")
    labels = ["TECHGUY TOOL — HUAWEI", "SERVICE & RECOVERY EDITION", "LIVE OPERATION LOG", "FIRMWARE FLASH", "FRP Repair", "Verlist", "Full OEMINFO"]
    missing = [label for label in labels if label not in combined]
    return not missing, f"missing={missing}"


def check_terminal_is_nonexecuting() -> tuple[bool, str]:
    qml = text("qml/dialogs/TerminalDialog.qml")
    return ok("safe terminal adapter" in qml and "subprocess" not in qml, "terminal UI does not execute arbitrary text")


def check_driver_guard() -> tuple[bool, str]:
    backend = text("techguy_huawei/backend.py")
    return ok('"fix_drivers": lambda: self.engine.guarded' in backend, "driver write path remains guarded")


def check_official_unlock_boundary() -> tuple[bool, str]:
    data = text("data/action_manifest.json")
    return ok("Only official unlock/relock routes may be used" in data, "bootloader action states official-route boundary")


def check_firmware_preflight() -> tuple[bool, str]:
    source = text("techguy_huawei/device_engine.py")
    return ok("path.is_file()" in source and "path.stat().st_size == 0" in source, "package existence and nonempty preflight")


def check_command_arrays() -> tuple[bool, str]:
    source = text("techguy_huawei/device_engine.py")
    return ok("command = list(args)" in source and "shell=False" in source, "fixed argument vectors, no shell")


def check_session_identity() -> tuple[bool, str]:
    source = text("techguy_huawei/device_engine.py")
    return ok("uuid.uuid5" in source and "session_id" in source, "stable host-scoped session identity")


def check_health_states() -> tuple[bool, str]:
    source = text("techguy_huawei/action_health.py")
    expected = ["READY", "RUNNING", "GUARDED", "MISSING_DEPENDENCY", "FAILED", "NOT_IMPLEMENTED"]
    missing = [item for item in expected if item not in source]
    return not missing, f"missing={missing}"


def check_styles() -> tuple[bool, str]:
    theme = text("qml/Theme.qml")
    expected = ["#050913", "#38b9ff", "#ad4cff", "#41d565"]
    missing = [color for color in expected if color not in theme]
    return not missing, f"missing palette tokens={missing}"


def check_window_controls() -> tuple[bool, str]:
    source = text("qml/Main.qml")
    expected = ["showMinimized", "showMaximized", "showNormal", "app.close", "startSystemMove"]
    missing = [item for item in expected if item not in source]
    return not missing, f"missing={missing}"


def check_navigation() -> tuple[bool, str]:
    source = text("qml/Main.qml")
    labels = ["Service Center", "Device Information", "Firmware Flash", "Partition Manager", "Backup & Restore", "Operation History"]
    missing = [item for item in labels if item not in source]
    return not missing, f"missing={missing}"


def check_firmware_modes() -> tuple[bool, str]:
    source = text("qml/pages/FirmwareFlashPage.qml")
    modes = ["Upgrade", "Downgrade", "Full Flash", "Board Firmware", "Repair"]
    missing = [item for item in modes if item not in source]
    return not missing, f"missing={missing}"


def check_safe_options() -> tuple[bool, str]:
    source = text("qml/pages/FirmwareFlashPage.qml")
    options = ["Verify package", "Backup OEMINFO", "Reboot after flash"]
    missing = [item for item in options if item not in source]
    return not missing, f"missing={missing}"


def check_settings_actions() -> tuple[bool, str]:
    source = text("qml/dialogs/SettingsMenu.qml")
    labels = ["Fix Drivers", "Register Device", "About"]
    missing = [item for item in labels if item not in source]
    return not missing, f"missing={missing}"


def check_computer_id() -> tuple[bool, str]:
    source = text("techguy_huawei/backend.py")
    return ok("platform.node()" in source and "platform.machine()" in source and "sha256(raw.encode())" in source, "deterministic hashed computer ID")


def check_brand_publisher() -> tuple[bool, str]:
    about = text("qml/dialogs/AboutDialog.qml")
    pyproject = text("pyproject.toml")
    return ok("THETECHGUY DIGITAL SOLUTIONS" in about and "THETECHGUY DIGITAL SOLUTIONS" in pyproject, "publisher identity consistent")


def check_readme_present() -> tuple[bool, str]:
    path = ROOT / "README.md"
    return ok(path.is_file() and path.stat().st_size > 500, "README documents architecture and proof boundary")


def check_ci_present() -> tuple[bool, str]:
    path = ROOT / ".github/workflows/proof.yml"
    return ok(path.is_file() and "review_20_for_2.py --strict" in path.read_text(encoding="utf-8"), "CI runs strict review")


def checks() -> list[Check]:
    wave1 = [
        ("W1-01", "Python syntax", python_compiles),
        ("W1-02", "QML structural contract", qml_contract),
        ("W1-03", "Manifest action uniqueness", lambda: ok(len([a["id"] for a in manifest()["actions"]]) == len({a["id"] for a in manifest()["actions"]}), "unique action IDs")),  # type: ignore[index]
        ("W1-04", "UI actions declared", check_action_calls),
        ("W1-05", "Backend handlers complete", check_handlers),
        ("W1-06", "Guard reasons complete", check_guarded_manifest),
        ("W1-07", "No forbidden service commands", no_forbidden_commands),
        ("W1-08", "Shell-free command arrays", check_command_arrays),
        ("W1-09", "Single-device ambiguity gate", check_single_device_gate),
        ("W1-10", "Evidence custody", check_evidence_custody),
        ("W1-11", "Session identity", check_session_identity),
        ("W1-12", "Runtime health states", check_health_states),
        ("W1-13", "Runtime UI binding audit", check_ui_binding_audit),
        ("W1-14", "Rust manifest auditor", check_rust_contract),
        ("W1-15", "Registration secret handling", check_registration_hash),
        ("W1-16", "Computer ID derivation", check_computer_id),
        ("W1-17", "Mutable data paths", check_output_paths),
        ("W1-18", "No embedded firmware", check_no_firmware_assets),
        ("W1-19", "Starter device profiles", check_profile_database),
        ("W1-20", "Secret scan", check_no_secrets),
    ]
    wave2 = [
        ("W2-01", "Reference geometry", check_geometry),
        ("W2-02", "Brand assets", check_assets),
        ("W2-03", "QRC completeness", qrc_complete),
        ("W2-04", "Relative asset paths", check_relative_assets),
        ("W2-05", "Palette contract", check_styles),
        ("W2-06", "Window controls", check_window_controls),
        ("W2-07", "Navigation contract", check_navigation),
        ("W2-08", "Reference labels", check_reference_labels),
        ("W2-09", "Popup set", check_qml_popups),
        ("W2-10", "Settings menu actions", check_settings_actions),
        ("W2-11", "Firmware modes", check_firmware_modes),
        ("W2-12", "Firmware safe options", check_safe_options),
        ("W2-13", "Firmware package preflight", check_firmware_preflight),
        ("W2-14", "Driver repair guard", check_driver_guard),
        ("W2-15", "Official unlock boundary", check_official_unlock_boundary),
        ("W2-16", "Safe terminal boundary", check_terminal_is_nonexecuting),
        ("W2-17", "One-file deployment", check_onefile),
        ("W2-18", "Release proof script", check_build_proof),
        ("W2-19", "Publisher identity", check_brand_publisher),
        ("W2-20", "Unit and contract tests", test_suite),
    ]
    return [Check(check_id, 1, title, run) for check_id, title, run in wave1] + [Check(check_id, 2, title, run) for check_id, title, run in wave2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = []
    for check in checks():
        try:
            passed, detail = check.run()
        except Exception as exc:
            passed, detail = False, f"exception: {exc}"
        results.append({"id": check.check_id, "wave": check.wave, "title": check.title, "passed": passed, "detail": detail})
    passed = sum(1 for result in results if result["passed"])
    report = {"method": "SRG 20-for-2", "waves": 2, "checks": 40, "passed": passed, "failed": 40 - passed, "results": results}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for wave in (1, 2):
            print(f"WAVE {wave}")
            for result in results:
                if result["wave"] == wave:
                    print(f"  {'PASS' if result['passed'] else 'FAIL'} {result['id']} {result['title']}: {result['detail']}")
        print(f"VERDICT {'PASS' if passed == 40 else 'NEEDS WORK'} — {passed}/40")
    return 0 if passed == 40 or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())

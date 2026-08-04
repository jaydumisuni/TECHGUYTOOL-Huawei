from __future__ import annotations

import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from techguy_huawei.contract_validation import validate_contract

ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = ROOT / "contracts" / "fixtures" / "valid_contracts.json"
INVALID_FIXTURES = ROOT / "contracts" / "fixtures" / "invalid_contracts.json"
DEFAULT_RUST_BINARY = (
    ROOT
    / "rust"
    / "contracts_core"
    / "target"
    / "debug"
    / ("ttg-contracts.exe" if __import__("os").name == "nt" else "ttg-contracts")
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_pointer(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {path!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _apply_mutation(document: Any, mutation: dict[str, Any]) -> None:
    parts = _decode_pointer(mutation["path"])
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    leaf = parts[-1]
    if mutation["op"] == "set":
        if isinstance(parent, list):
            parent[int(leaf)] = copy.deepcopy(mutation["value"])
        else:
            parent[leaf] = copy.deepcopy(mutation["value"])
    elif mutation["op"] == "remove":
        if isinstance(parent, list):
            del parent[int(leaf)]
        else:
            del parent[leaf]
    else:
        raise ValueError(f"unsupported mutation operation: {mutation['op']!r}")


def _python_result(document: Any, context: dict[str, Any], *, raw: bool = False) -> dict[str, Any]:
    result = validate_contract(document if raw else copy.deepcopy(document), context=context)
    return result.as_dict()


def _rust_result(
    binary: Path,
    document: Any,
    context: dict[str, Any],
    *,
    raw: bool = False,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ttg-contract-equivalence-") as temporary:
        root = Path(temporary)
        contract_path = root / "contract.json"
        context_path = root / "context.json"
        if raw:
            contract_path.write_text(str(document), encoding="utf-8")
        else:
            contract_path.write_text(
                json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                encoding="utf-8",
            )
        context_path.write_text(
            json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                str(binary),
                "validate",
                "--contract",
                str(contract_path),
                "--context",
                str(context_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(
                f"Rust validator failed with exit {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Rust validator returned invalid JSON: {completed.stdout!r}"
            ) from exc


def _codes(result: dict[str, Any]) -> list[str]:
    return sorted({error["code"] for error in result.get("errors", [])})


def _assert_equivalent(name: str, python: dict[str, Any], rust: dict[str, Any]) -> None:
    if python["ok"] != rust["ok"]:
        raise AssertionError(f"{name}: ok mismatch: Python={python['ok']} Rust={rust['ok']}")
    if _codes(python) != _codes(rust):
        raise AssertionError(
            f"{name}: error-code mismatch: Python={_codes(python)} Rust={_codes(rust)}"
        )
    if python["ok"]:
        if python.get("canonical") != rust.get("canonical"):
            raise AssertionError(f"{name}: canonical JSON mismatch")
        if python.get("sha256") != rust.get("sha256"):
            raise AssertionError(
                f"{name}: SHA-256 mismatch: Python={python.get('sha256')} Rust={rust.get('sha256')}"
            )


def prove(binary: Path) -> dict[str, Any]:
    if not binary.is_file():
        raise FileNotFoundError(f"Rust validator binary not found: {binary}")

    valid_root = _load(VALID_FIXTURES)
    invalid_root = _load(INVALID_FIXTURES)
    valid = {case["name"]: case for case in valid_root["contracts"]}
    checked_valid = 0
    checked_invalid = 0
    checked_raw = 0

    for case in valid_root["contracts"]:
        python = _python_result(case["contract"], case.get("context", {}))
        rust = _rust_result(binary, case["contract"], case.get("context", {}))
        _assert_equivalent(case["name"], python, rust)
        checked_valid += 1

    for case in invalid_root["cases"]:
        document = copy.deepcopy(valid[case["base"]]["contract"])
        for mutation in case["mutations"]:
            _apply_mutation(document, mutation)
        python = _python_result(document, case.get("context", {}))
        rust = _rust_result(binary, document, case.get("context", {}))
        _assert_equivalent(case["name"], python, rust)
        expected = sorted(case["expected_error_codes"])
        if _codes(python) != expected:
            raise AssertionError(
                f"{case['name']}: fixture expects {expected}, validator returned {_codes(python)}"
            )
        checked_invalid += 1

    for case in invalid_root["raw_cases"]:
        python = _python_result(case["raw_json"], case.get("context", {}), raw=True)
        rust = _rust_result(
            binary,
            case["raw_json"],
            case.get("context", {}),
            raw=True,
        )
        _assert_equivalent(case["name"], python, rust)
        checked_raw += 1

    return {
        "schema": "techguytool-huawei.contract-equivalence-proof.v1",
        "status": "PASS",
        "python_rust_canonical_equivalence": True,
        "valid_contracts": checked_valid,
        "invalid_contracts": checked_invalid,
        "raw_invalid_contracts": checked_raw,
        "total_cases": checked_valid + checked_invalid + checked_raw,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove exact Python/Rust TECHGUYTOOL Huawei contract equivalence"
    )
    parser.add_argument("--rust-bin", type=Path, default=DEFAULT_RUST_BINARY)
    args = parser.parse_args()
    print(json.dumps(prove(args.rust_bin.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

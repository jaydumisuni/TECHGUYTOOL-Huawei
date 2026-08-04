from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from techguy_huawei.contract_validation import validate_contract

VALID_FIXTURES = ROOT / "contracts" / "fixtures" / "valid_contracts.json"
CONTEXT_FIXTURES = ROOT / "contracts" / "fixtures" / "context_cases.json"
DEFAULT_RUST_BINARY = (
    ROOT
    / "rust"
    / "contracts_core"
    / "target"
    / "debug"
    / ("ttg-contracts.exe" if os.name == "nt" else "ttg-contracts")
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _codes(result: dict[str, Any]) -> list[str]:
    return sorted({error["code"] for error in result.get("errors", [])})


def _rust_result(binary: Path, document: Any, context: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ttg-context-equivalence-") as temporary:
        root = Path(temporary)
        contract_path = root / "contract.json"
        context_path = root / "context.json"
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
        return json.loads(completed.stdout)


def prove(binary: Path) -> dict[str, Any]:
    if not binary.is_file():
        raise FileNotFoundError(f"Rust validator binary not found: {binary}")
    valid = {case["name"]: case["contract"] for case in _load(VALID_FIXTURES)["contracts"]}
    fixtures = _load(CONTEXT_FIXTURES)
    checked = 0

    for case in fixtures["cases"]:
        document = valid[case["base"]]
        python_result = validate_contract(document, context=case["context"]).as_dict()
        rust_result = _rust_result(binary, document, case["context"])
        expected = sorted(case["expected_error_codes"])
        if python_result["ok"] != rust_result["ok"]:
            raise AssertionError(f"{case['name']}: Python/Rust validity mismatch")
        if _codes(python_result) != expected:
            raise AssertionError(
                f"{case['name']}: Python returned {_codes(python_result)}, expected {expected}"
            )
        if _codes(rust_result) != expected:
            raise AssertionError(
                f"{case['name']}: Rust returned {_codes(rust_result)}, expected {expected}"
            )
        checked += 1

    return {
        "schema": "techguytool-huawei.context-equivalence-proof.v1",
        "status": "PASS",
        "context_cases": checked,
        "python_rust_error_code_equivalence": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove Python/Rust validation-context error equivalence"
    )
    parser.add_argument("--rust-bin", type=Path, default=DEFAULT_RUST_BINARY)
    args = parser.parse_args()
    print(json.dumps(prove(args.rust_bin.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

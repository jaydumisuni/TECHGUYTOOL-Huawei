from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from techguy_huawei.contract_support import canonical_json, load_registry
from techguy_huawei.contract_validation import validate_contract

ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURES = ROOT / "contracts" / "fixtures" / "valid_contracts.json"
INVALID_FIXTURES = ROOT / "contracts" / "fixtures" / "invalid_contracts.json"
EDGE_FIXTURES = ROOT / "contracts" / "fixtures" / "review_edge_cases.json"
CONTEXT_FIXTURES = ROOT / "contracts" / "fixtures" / "context_cases.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_by_name() -> dict[str, dict[str, Any]]:
    payload = _load(VALID_FIXTURES)
    return {case["name"]: case for case in payload["contracts"]}


def _decode_pointer(path: str) -> list[str]:
    if not path.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {path!r}")
    if path == "/":
        return [""]
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _apply_mutation(document: Any, mutation: dict[str, Any]) -> None:
    parts = _decode_pointer(mutation["path"])
    parent = document
    for part in parts[:-1]:
        parent = parent[int(part)] if isinstance(parent, list) else parent[part]
    leaf = parts[-1]
    operation = mutation["op"]
    if operation == "set":
        if isinstance(parent, list):
            parent[int(leaf)] = copy.deepcopy(mutation["value"])
        else:
            parent[leaf] = copy.deepcopy(mutation["value"])
    elif operation == "remove":
        if isinstance(parent, list):
            del parent[int(leaf)]
        else:
            del parent[leaf]
    else:
        raise ValueError(f"unsupported mutation operation: {operation!r}")


def _error_codes(result: Any) -> list[str]:
    return sorted({error.code for error in result.errors})


def _mutated_contract(case: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(_valid_by_name()[case["base"]]["contract"])
    for mutation in case["mutations"]:
        _apply_mutation(document, mutation)
    return document


def test_registry_contains_all_frozen_contract_types() -> None:
    registry = load_registry()
    assert registry["schema"] == "techguytool-huawei.contract-registry.v1"
    assert registry["registry_version"] == 1
    assert len(registry["contracts"]) == 17
    assert set(registry["contracts"]) == set(
        registry["envelope"]["fields"]["contract_type"]["enum"]
    )


def test_default_registry_cannot_be_replaced_by_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    replacement = tmp_path / "replacement-registry.json"
    replacement.write_text(
        json.dumps(
            {
                "schema": "techguytool-huawei.contract-registry.v1",
                "registry_version": 999,
                "envelope": {},
                "contracts": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TTG_CONTRACT_REGISTRY", str(replacement))
    assert load_registry()["registry_version"] == 1


def test_explicit_registry_rejects_unreviewed_version(tmp_path: Path) -> None:
    replacement = copy.deepcopy(load_registry())
    replacement["registry_version"] = 2
    path = tmp_path / "registry-v2.json"
    path.write_text(json.dumps(replacement), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported contract registry version"):
        load_registry(path)

    contract = _valid_by_name()["physical_device_session"]["contract"]
    result = validate_contract(contract, registry=replacement)
    assert _error_codes(result) == ["REGISTRY_UNAVAILABLE"]


def test_registry_rejects_missing_and_unknown_members() -> None:
    contract = _valid_by_name()["physical_device_session"]["contract"]

    missing = copy.deepcopy(load_registry())
    del missing["envelope"]
    assert _error_codes(validate_contract(contract, registry=missing)) == [
        "REGISTRY_UNAVAILABLE"
    ]

    misspelled = copy.deepcopy(load_registry())
    misspelled["envelope"]["fields"]["producer"]["min_lenght"] = 1
    assert _error_codes(validate_contract(contract, registry=misspelled)) == [
        "REGISTRY_UNAVAILABLE"
    ]


def test_canonical_json_rejects_unpaired_surrogate() -> None:
    with pytest.raises(UnicodeError):
        canonical_json({"value": "\ud800"})


def test_all_valid_contract_fixtures_pass_and_canonicalize() -> None:
    fixtures = _load(VALID_FIXTURES)
    assert fixtures["schema"] == "techguytool-huawei.valid-contract-fixtures.v1"
    assert len(fixtures["contracts"]) == 17

    for case in fixtures["contracts"]:
        result = validate_contract(case["contract"], context=case.get("context"))
        assert result.ok, (case["name"], [error.as_dict() for error in result.errors])
        assert result.canonical is not None
        assert result.sha256 is not None
        assert len(result.sha256) == 64
        assert json.loads(result.canonical) == case["contract"]
        assert result.canonical == json.dumps(
            case["contract"],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )


def test_all_invalid_mutation_fixtures_fail_with_exact_codes() -> None:
    fixtures = _load(INVALID_FIXTURES)
    assert fixtures["schema"] == "techguytool-huawei.invalid-contract-fixtures.v1"
    assert len(fixtures["cases"]) == 34

    for case in fixtures["cases"]:
        result = validate_contract(_mutated_contract(case), context=case.get("context"))
        assert not result.ok, case["name"]
        assert _error_codes(result) == sorted(case["expected_error_codes"]), (
            case["name"],
            _error_codes(result),
            case["expected_error_codes"],
        )
        assert result.canonical is None
        assert result.sha256 is None


def test_review_edge_fixtures_fail_with_exact_codes() -> None:
    fixtures = _load(EDGE_FIXTURES)
    assert fixtures["schema"] == "techguytool-huawei.review-edge-contract-fixtures.v1"
    assert len(fixtures["cases"]) == 3

    for case in fixtures["cases"]:
        result = validate_contract(_mutated_contract(case), context=case.get("context"))
        assert not result.ok, case["name"]
        assert _error_codes(result) == sorted(case["expected_error_codes"])
        assert result.canonical is None
        assert result.sha256 is None


def test_all_raw_invalid_fixtures_fail_with_exact_codes() -> None:
    fixtures = _load(INVALID_FIXTURES)
    assert len(fixtures["raw_cases"]) == 1
    for case in fixtures["raw_cases"]:
        result = validate_contract(case["raw_json"], context=case.get("context"))
        assert not result.ok, case["name"]
        assert _error_codes(result) == sorted(case["expected_error_codes"])


def test_all_context_fixtures_match_expected_results() -> None:
    valid = _valid_by_name()
    fixtures = _load(CONTEXT_FIXTURES)
    assert fixtures["schema"] == "techguytool-huawei.context-contract-fixtures.v1"
    assert len(fixtures["cases"]) == 2

    for case in fixtures["cases"]:
        document = copy.deepcopy(valid[case["base"]]["contract"])
        result = validate_contract(document, context=case["context"])
        assert result.ok is case["expected_ok"], case["name"]
        assert _error_codes(result) == sorted(case["expected_error_codes"])
        if case["expected_ok"]:
            assert result.canonical == canonical_json(document)
            assert result.sha256 is not None
        else:
            assert result.canonical is None
            assert result.sha256 is None


def test_execution_lease_context_is_fail_closed() -> None:
    execution = copy.deepcopy(_valid_by_name()["execution_lease"])
    contract = execution["contract"]
    context = execution["context"]

    assert validate_contract(contract, context=context).ok

    wrong_session = dict(context)
    wrong_session["expected_physical_session_id"] = (
        "11111111-1111-4111-8111-111111111112"
    )
    assert _error_codes(validate_contract(contract, context=wrong_session)) == [
        "PHYSICAL_SESSION_MISMATCH"
    ]

    wrong_recipe = dict(context)
    wrong_recipe["expected_recipe_hash"] = "0" * 64
    assert _error_codes(validate_contract(contract, context=wrong_recipe)) == [
        "RECIPE_HASH_MISMATCH"
    ]

    wrong_artifacts = dict(context)
    wrong_artifacts["expected_artifact_hashes"] = ["a" * 64]
    assert _error_codes(validate_contract(contract, context=wrong_artifacts)) == [
        "ARTIFACT_HASH_MISMATCH"
    ]


def test_dangerous_learning_never_auto_promotes() -> None:
    proposal = copy.deepcopy(_valid_by_name()["learning_proposal"])
    proposal["contract"]["payload"]["change_kind"] = "write_target"
    proposal["contract"]["payload"]["auto_promotion_allowed"] = True
    result = validate_contract(proposal["contract"], context=proposal["context"])
    assert _error_codes(result) == ["DANGEROUS_AUTO_PROMOTION_FORBIDDEN"]

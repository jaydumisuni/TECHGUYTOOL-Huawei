use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use techguy_contracts_core::{
    canonical_json, canonical_sha256, load_registry, validate_contract, ContractError,
    ValidationContext,
};

const VALID_FIXTURES: &str = include_str!("../../../contracts/fixtures/valid_contracts.json");
const CONTEXT_FIXTURES: &str = include_str!("../../../contracts/fixtures/context_cases.json");

#[derive(Debug, Deserialize)]
struct ValidRoot {
    contracts: Vec<ValidCase>,
}

#[derive(Debug, Deserialize)]
struct ValidCase {
    name: String,
    contract: Value,
}

#[derive(Debug, Deserialize)]
struct ContextRoot {
    schema: String,
    cases: Vec<ContextCase>,
}

#[derive(Debug, Deserialize)]
struct ContextCase {
    name: String,
    base: String,
    context: ValidationContext,
    expected_ok: bool,
    expected_error_codes: Vec<String>,
}

#[test]
fn validation_contexts_match_expected_results() {
    let valid_root: ValidRoot = serde_json::from_str(VALID_FIXTURES).expect("valid fixtures");
    let context_root: ContextRoot =
        serde_json::from_str(CONTEXT_FIXTURES).expect("context fixtures");
    assert_eq!(
        context_root.schema,
        "techguytool-huawei.context-contract-fixtures.v1"
    );
    assert_eq!(context_root.cases.len(), 2);

    let valid: BTreeMap<String, Value> = valid_root
        .contracts
        .into_iter()
        .map(|case| (case.name, case.contract))
        .collect();
    let registry = load_registry().expect("registry");

    for case in context_root.cases {
        let contract = valid
            .get(&case.base)
            .unwrap_or_else(|| panic!("missing base fixture {}", case.base));
        let result = validate_contract(contract, &case.context, &registry);
        assert_eq!(result.ok, case.expected_ok, "{} validity mismatch", case.name);
        assert_eq!(
            error_codes(&result.errors),
            case.expected_error_codes.into_iter().collect(),
            "{} returned unexpected error codes",
            case.name
        );
        if case.expected_ok {
            assert_eq!(
                result.canonical.as_deref(),
                Some(canonical_json(contract).expect("canonical JSON").as_str()),
                "{} canonical JSON mismatch",
                case.name
            );
            assert_eq!(
                result.sha256.as_deref(),
                Some(canonical_sha256(contract).expect("canonical hash").as_str()),
                "{} SHA-256 mismatch",
                case.name
            );
        } else {
            assert!(result.canonical.is_none());
            assert!(result.sha256.is_none());
        }
    }
}

fn error_codes(errors: &[ContractError]) -> BTreeSet<String> {
    errors.iter().map(|error| error.code.clone()).collect()
}

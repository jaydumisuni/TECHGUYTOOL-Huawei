use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use techguy_contracts_core::{load_registry, validate_contract, ContractError, ValidationContext};

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
    expected_error_codes: Vec<String>,
}

#[test]
fn invalid_validation_contexts_fail_with_exact_codes() {
    let valid_root: ValidRoot = serde_json::from_str(VALID_FIXTURES).expect("valid fixtures");
    let context_root: ContextRoot =
        serde_json::from_str(CONTEXT_FIXTURES).expect("context fixtures");
    assert_eq!(
        context_root.schema,
        "techguytool-huawei.context-contract-fixtures.v1"
    );
    assert_eq!(context_root.cases.len(), 1);

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
        assert!(!result.ok, "{} unexpectedly passed", case.name);
        assert_eq!(
            error_codes(&result.errors),
            case.expected_error_codes.into_iter().collect(),
            "{} returned unexpected error codes",
            case.name
        );
    }
}

fn error_codes(errors: &[ContractError]) -> BTreeSet<String> {
    errors.iter().map(|error| error.code.clone()).collect()
}

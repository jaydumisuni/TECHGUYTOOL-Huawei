use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use techguy_contracts_core::{
    load_registry, validate_contract, validate_contract_json, ValidationContext,
};

const VALID_FIXTURES: &str = include_str!("../../../contracts/fixtures/valid_contracts.json");
const INVALID_FIXTURES: &str = include_str!("../../../contracts/fixtures/invalid_contracts.json");

#[derive(Debug, Deserialize)]
struct ValidFixtureRoot {
    schema: String,
    contracts: Vec<ValidCase>,
}

#[derive(Debug, Clone, Deserialize)]
struct ValidCase {
    name: String,
    contract: Value,
    #[serde(default)]
    context: ValidationContext,
}

#[derive(Debug, Deserialize)]
struct InvalidFixtureRoot {
    schema: String,
    cases: Vec<InvalidCase>,
    raw_cases: Vec<RawInvalidCase>,
}

#[derive(Debug, Deserialize)]
struct InvalidCase {
    name: String,
    base: String,
    #[serde(default)]
    context: ValidationContext,
    expected_error_codes: Vec<String>,
    mutations: Vec<Mutation>,
}

#[derive(Debug, Deserialize)]
struct RawInvalidCase {
    name: String,
    raw_json: String,
    #[serde(default)]
    context: ValidationContext,
    expected_error_codes: Vec<String>,
}

#[derive(Debug, Deserialize)]
struct Mutation {
    op: String,
    path: String,
    #[serde(default)]
    value: Value,
}

#[test]
fn all_valid_fixtures_pass_and_canonicalize() {
    let root: ValidFixtureRoot = serde_json::from_str(VALID_FIXTURES).expect("valid fixtures");
    assert_eq!(root.schema, "techguytool-huawei.valid-contract-fixtures.v1");
    assert_eq!(root.contracts.len(), 17);
    let registry = load_registry().expect("registry");

    for case in root.contracts {
        let result = validate_contract(&case.contract, &case.context, &registry);
        assert!(result.ok, "{} failed: {:?}", case.name, result.errors);
        assert!(
            result.canonical.is_some(),
            "{} has no canonical JSON",
            case.name
        );
        assert_eq!(result.sha256.as_deref().map(str::len), Some(64));
        let reparsed: Value = serde_json::from_str(result.canonical.as_deref().unwrap())
            .expect("canonical JSON must parse");
        assert_eq!(
            reparsed, case.contract,
            "{} canonical value changed",
            case.name
        );
    }
}

#[test]
fn all_invalid_mutation_fixtures_fail_with_exact_codes() {
    let valid_root: ValidFixtureRoot =
        serde_json::from_str(VALID_FIXTURES).expect("valid fixtures");
    let invalid_root: InvalidFixtureRoot =
        serde_json::from_str(INVALID_FIXTURES).expect("invalid fixtures");
    assert_eq!(
        invalid_root.schema,
        "techguytool-huawei.invalid-contract-fixtures.v1"
    );
    assert_eq!(invalid_root.cases.len(), 34);

    let valid: BTreeMap<String, ValidCase> = valid_root
        .contracts
        .into_iter()
        .map(|case| (case.name.clone(), case))
        .collect();
    let registry = load_registry().expect("registry");

    for case in invalid_root.cases {
        let mut document = valid
            .get(&case.base)
            .unwrap_or_else(|| panic!("missing base fixture {}", case.base))
            .contract
            .clone();
        for mutation in &case.mutations {
            apply_mutation(&mut document, mutation)
                .unwrap_or_else(|error| panic!("{} mutation failed: {error}", case.name));
        }
        let result = validate_contract(&document, &case.context, &registry);
        assert!(!result.ok, "{} unexpectedly passed", case.name);
        assert_eq!(
            error_codes(&result.errors),
            case.expected_error_codes.into_iter().collect(),
            "{} returned unexpected error codes",
            case.name
        );
        assert!(result.canonical.is_none());
        assert!(result.sha256.is_none());
    }
}

#[test]
fn all_raw_invalid_fixtures_fail_with_exact_codes() {
    let root: InvalidFixtureRoot =
        serde_json::from_str(INVALID_FIXTURES).expect("invalid fixtures");
    assert_eq!(root.raw_cases.len(), 1);
    let registry = load_registry().expect("registry");

    for case in root.raw_cases {
        let result = validate_contract_json(&case.raw_json, &case.context, &registry);
        assert!(!result.ok, "{} unexpectedly passed", case.name);
        assert_eq!(
            error_codes(&result.errors),
            case.expected_error_codes.into_iter().collect(),
            "{} returned unexpected error codes",
            case.name
        );
    }
}

fn error_codes(errors: &[techguy_contracts_core::ContractError]) -> BTreeSet<String> {
    errors.iter().map(|error| error.code.clone()).collect()
}

fn apply_mutation(document: &mut Value, mutation: &Mutation) -> Result<(), String> {
    let parts = decode_pointer(&mutation.path)?;
    let (leaf, parents) = parts
        .split_last()
        .ok_or_else(|| "empty JSON pointer is not supported".to_owned())?;
    let mut parent = document;
    for part in parents {
        parent = descend_mut(parent, part)?;
    }

    match mutation.op.as_str() {
        "set" => match parent {
            Value::Object(object) => {
                object.insert(leaf.clone(), mutation.value.clone());
                Ok(())
            }
            Value::Array(items) => {
                let index = parse_index(leaf, items.len())?;
                items[index] = mutation.value.clone();
                Ok(())
            }
            _ => Err("set parent is not an object or array".to_owned()),
        },
        "remove" => match parent {
            Value::Object(object) => object
                .remove(leaf)
                .map(|_| ())
                .ok_or_else(|| format!("missing object key {leaf:?}")),
            Value::Array(items) => {
                let index = parse_index(leaf, items.len())?;
                items.remove(index);
                Ok(())
            }
            _ => Err("remove parent is not an object or array".to_owned()),
        },
        other => Err(format!("unsupported mutation operation {other:?}")),
    }
}

fn descend_mut<'a>(value: &'a mut Value, part: &str) -> Result<&'a mut Value, String> {
    match value {
        Value::Object(object) => object
            .get_mut(part)
            .ok_or_else(|| format!("missing object key {part:?}")),
        Value::Array(items) => {
            let index = parse_index(part, items.len())?;
            Ok(&mut items[index])
        }
        _ => Err(format!("cannot descend through JSON scalar at {part:?}")),
    }
}

fn parse_index(value: &str, length: usize) -> Result<usize, String> {
    let index = value
        .parse::<usize>()
        .map_err(|_| format!("invalid array index {value:?}"))?;
    if index >= length {
        return Err(format!("array index {index} is outside length {length}"));
    }
    Ok(index)
}

fn decode_pointer(path: &str) -> Result<Vec<String>, String> {
    let Some(rest) = path.strip_prefix('/') else {
        return Err(format!("invalid JSON pointer {path:?}"));
    };
    Ok(rest
        .split('/')
        .map(|part| part.replace("~1", "/").replace("~0", "~"))
        .collect())
}

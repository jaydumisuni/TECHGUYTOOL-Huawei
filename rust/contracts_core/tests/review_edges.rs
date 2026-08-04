use serde::Deserialize;
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use techguy_contracts_core::{load_registry, validate_contract, ContractError, ValidationContext};

const VALID_FIXTURES: &str = include_str!("../../../contracts/fixtures/valid_contracts.json");
const EDGE_FIXTURES: &str = include_str!("../../../contracts/fixtures/review_edge_cases.json");

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
struct EdgeRoot {
    schema: String,
    cases: Vec<EdgeCase>,
}

#[derive(Debug, Deserialize)]
struct EdgeCase {
    name: String,
    base: String,
    #[serde(default)]
    context: ValidationContext,
    expected_error_codes: Vec<String>,
    mutations: Vec<Mutation>,
}

#[derive(Debug, Deserialize)]
struct Mutation {
    op: String,
    path: String,
    #[serde(default)]
    value: Value,
}

#[test]
fn review_edge_fixtures_fail_with_exact_codes() {
    let valid_root: ValidRoot = serde_json::from_str(VALID_FIXTURES).expect("valid fixtures");
    let edge_root: EdgeRoot = serde_json::from_str(EDGE_FIXTURES).expect("edge fixtures");
    assert_eq!(
        edge_root.schema,
        "techguytool-huawei.review-edge-contract-fixtures.v1"
    );
    assert_eq!(edge_root.cases.len(), 3);

    let valid: BTreeMap<String, Value> = valid_root
        .contracts
        .into_iter()
        .map(|case| (case.name, case.contract))
        .collect();
    let registry = load_registry().expect("registry");

    for case in edge_root.cases {
        let mut document = valid
            .get(&case.base)
            .unwrap_or_else(|| panic!("missing base fixture {}", case.base))
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
    }
}

fn error_codes(errors: &[ContractError]) -> BTreeSet<String> {
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
    if mutation.op != "set" {
        return Err(format!("unsupported mutation operation {:?}", mutation.op));
    }
    match parent {
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

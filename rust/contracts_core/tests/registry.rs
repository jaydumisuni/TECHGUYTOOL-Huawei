use serde_json::{json, Value};
use techguy_contracts_core::decode_registry_json;

const REGISTRY_JSON: &str = include_str!("../../../contracts/registry.json");

#[test]
fn registry_rejects_missing_and_unknown_members() {
    let mut missing: Value = serde_json::from_str(REGISTRY_JSON).expect("registry JSON");
    missing
        .as_object_mut()
        .expect("registry object")
        .remove("envelope");
    assert!(decode_registry_json(&missing.to_string()).is_err());

    let mut unknown: Value = serde_json::from_str(REGISTRY_JSON).expect("registry JSON");
    unknown
        .as_object_mut()
        .expect("registry object")
        .insert("unexpected".to_owned(), json!(true));
    assert!(decode_registry_json(&unknown.to_string()).is_err());

    let mut misspelled: Value = serde_json::from_str(REGISTRY_JSON).expect("registry JSON");
    misspelled["envelope"]["fields"]["producer"]
        .as_object_mut()
        .expect("producer spec")
        .insert("min_lenght".to_owned(), json!(1));
    assert!(decode_registry_json(&misspelled.to_string()).is_err());
}

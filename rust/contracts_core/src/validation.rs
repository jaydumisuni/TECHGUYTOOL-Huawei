use crate::canonical::{canonical_json, canonical_sha256};
use crate::field::{parse_timestamp, validate_field};
use crate::model::{
    ContractDefinition, ContractError, Registry, ValidationContext, ValidationResult,
};
use chrono::{DateTime, Utc};
use serde_json::{Map, Value};
use std::collections::BTreeSet;

const DANGEROUS_LEARNING_KINDS: &[&str] = &[
    "write_target",
    "write_offset",
    "destructive_recipe",
    "expanded_authority",
];

pub fn validate_contract_json(
    document: &str,
    context: &ValidationContext,
    registry: &Registry,
) -> ValidationResult {
    match serde_json::from_str::<Value>(document) {
        Ok(value) => validate_contract(&value, context, registry),
        Err(error) => invalid(vec![ContractError::new(
            "MALFORMED_JSON",
            "$",
            error.to_string(),
        )]),
    }
}

pub fn validate_contract(
    document: &Value,
    context: &ValidationContext,
    registry: &Registry,
) -> ValidationResult {
    let Some(object) = document.as_object() else {
        return invalid(vec![ContractError::new(
            "INVALID_DOCUMENT_TYPE",
            "$",
            "contract document must be an object",
        )]);
    };

    let mut errors = Vec::new();
    validate_envelope_shape(object, registry, &mut errors);

    let definition = object
        .get("contract_type")
        .and_then(Value::as_str)
        .and_then(|contract_type| {
            let definition = registry.contracts.get(contract_type);
            if definition.is_none() {
                errors.push(ContractError::new(
                    "UNKNOWN_CONTRACT_TYPE",
                    "$.contract_type",
                    format!("contract type {contract_type:?} is not registered"),
                ));
            }
            definition
        });

    if let Some(definition) = definition {
        validate_definition(object, definition, &mut errors);
        validate_context(object, context, &mut errors);
    }
    validate_envelope_semantics(object, context, &mut errors);

    errors.sort();
    errors.dedup();
    if !errors.is_empty() {
        return invalid(errors);
    }

    match (canonical_json(document), canonical_sha256(document)) {
        (Ok(canonical), Ok(sha256)) => ValidationResult {
            ok: true,
            errors: Vec::new(),
            canonical: Some(canonical),
            sha256: Some(sha256),
        },
        (Err(error), _) | (_, Err(error)) => invalid(vec![ContractError::new(
            "NON_CANONICAL_JSON_VALUE",
            "$",
            error,
        )]),
    }
}

fn invalid(mut errors: Vec<ContractError>) -> ValidationResult {
    errors.sort();
    errors.dedup();
    ValidationResult {
        ok: false,
        errors,
        canonical: None,
        sha256: None,
    }
}

fn validate_envelope_shape(
    object: &Map<String, Value>,
    registry: &Registry,
    errors: &mut Vec<ContractError>,
) {
    for name in &registry.envelope.required {
        if !object.contains_key(name) {
            errors.push(ContractError::new(
                "MISSING_TOP_LEVEL_FIELD",
                format!("$.{name}"),
                format!("required top-level field {name:?} is missing"),
            ));
        }
    }

    for name in object.keys() {
        if !registry.envelope.fields.contains_key(name) {
            errors.push(ContractError::new(
                "UNKNOWN_TOP_LEVEL_FIELD",
                format!("$.{name}"),
                format!("unknown top-level field {name:?}"),
            ));
        }
    }

    for name in &registry.envelope.required {
        if let (Some(value), Some(spec)) = (object.get(name), registry.envelope.fields.get(name)) {
            validate_field(value, spec, &format!("$.{name}"), errors);
        }
    }
}

fn validate_definition(
    object: &Map<String, Value>,
    definition: &ContractDefinition,
    errors: &mut Vec<ContractError>,
) {
    if object.get("authority").and_then(Value::as_str) != Some(definition.authority.as_str()) {
        errors.push(ContractError::new(
            "AUTHORITY_MISMATCH",
            "$.authority",
            format!("contract requires authority {:?}", definition.authority),
        ));
    }

    let session_present = object
        .get("physical_session_id")
        .is_some_and(|value| !value.is_null());
    match definition.physical_session.as_str() {
        "required" if !session_present => errors.push(ContractError::new(
            "PHYSICAL_SESSION_REQUIRED",
            "$.physical_session_id",
            "physical session is required",
        )),
        "forbidden" if session_present => errors.push(ContractError::new(
            "PHYSICAL_SESSION_FORBIDDEN",
            "$.physical_session_id",
            "physical session is forbidden",
        )),
        _ => {}
    }

    let expiry_present = object
        .get("expires_at")
        .is_some_and(|value| !value.is_null());
    match definition.expiry.as_str() {
        "required" if !expiry_present => errors.push(ContractError::new(
            "EXPIRY_REQUIRED",
            "$.expires_at",
            "expiry is required",
        )),
        "forbidden" if expiry_present => errors.push(ContractError::new(
            "EXPIRY_FORBIDDEN",
            "$.expires_at",
            "expiry is forbidden",
        )),
        _ => {}
    }

    if object.get("single_use").and_then(Value::as_bool) != Some(definition.single_use) {
        errors.push(ContractError::new(
            "SINGLE_USE_MISMATCH",
            "$.single_use",
            format!("contract requires single_use={}", definition.single_use),
        ));
    }

    let Some(payload) = object.get("payload").and_then(Value::as_object) else {
        return;
    };

    for name in &definition.payload_required {
        if !payload.contains_key(name) {
            errors.push(ContractError::new(
                "MISSING_PAYLOAD_FIELD",
                format!("$.payload.{name}"),
                format!("required payload field {name:?} is missing"),
            ));
        }
    }

    for name in payload.keys() {
        if !definition.payload_fields.contains_key(name) {
            errors.push(ContractError::new(
                "UNKNOWN_PAYLOAD_FIELD",
                format!("$.payload.{name}"),
                format!("unknown payload field {name:?}"),
            ));
        }
    }

    for name in &definition.payload_required {
        if let (Some(value), Some(spec)) = (payload.get(name), definition.payload_fields.get(name))
        {
            validate_field(value, spec, &format!("$.payload.{name}"), errors);
        }
    }

    for (earlier_name, later_name) in &definition.timestamp_order {
        let earlier = payload
            .get(earlier_name)
            .and_then(Value::as_str)
            .and_then(parse_timestamp);
        let later = payload
            .get(later_name)
            .and_then(Value::as_str)
            .and_then(parse_timestamp);
        if let (Some(earlier), Some(later)) = (earlier, later) {
            if later < earlier {
                errors.push(ContractError::new(
                    "TIMESTAMP_ORDER_INVALID",
                    format!("$.payload.{later_name}"),
                    format!("{later_name} must not precede {earlier_name}"),
                ));
            }
        }
    }

    if definition.dangerous_auto_promotion {
        let kind = payload.get("change_kind").and_then(Value::as_str);
        let auto_promotion = payload
            .get("auto_promotion_allowed")
            .and_then(Value::as_bool);
        if kind.is_some_and(|value| DANGEROUS_LEARNING_KINDS.contains(&value))
            && auto_promotion == Some(true)
        {
            errors.push(ContractError::new(
                "DANGEROUS_AUTO_PROMOTION_FORBIDDEN",
                "$.payload.auto_promotion_allowed",
                format!(
                    "{} can never be promoted automatically",
                    kind.unwrap_or_default()
                ),
            ));
        }
    }
}

fn validate_envelope_semantics(
    object: &Map<String, Value>,
    context: &ValidationContext,
    errors: &mut Vec<ContractError>,
) {
    let created = timestamp_field(object, "created_at");
    let expires = timestamp_field(object, "expires_at");
    let consumed = timestamp_field(object, "consumed_at");
    let now = context_now(context, errors);

    if let (Some(created), Some(now)) = (created, now) {
        if created > now {
            errors.push(ContractError::new(
                "CREATED_AT_IN_FUTURE",
                "$.created_at",
                "created_at is later than validation time",
            ));
        }
    }
    if let (Some(created), Some(expires)) = (created, expires) {
        if expires <= created {
            errors.push(ContractError::new(
                "EXPIRY_NOT_AFTER_CREATED",
                "$.expires_at",
                "expires_at must be later than created_at",
            ));
        }
    }
    if let (Some(expires), Some(now)) = (expires, now) {
        if expires <= now {
            errors.push(ContractError::new(
                "CONTRACT_EXPIRED",
                "$.expires_at",
                "contract has expired",
            ));
        }
    }

    let Some(consumed) = consumed else {
        return;
    };
    let single_use = object.get("single_use").and_then(Value::as_bool);
    if single_use != Some(true) {
        errors.push(ContractError::new(
            "CONSUMED_AT_FORBIDDEN",
            "$.consumed_at",
            "only single-use contracts may be consumed",
        ));
    }
    if let Some(created) = created {
        if consumed < created {
            errors.push(ContractError::new(
                "CONSUMED_AT_INVALID",
                "$.consumed_at",
                "consumed_at precedes created_at",
            ));
        }
    }
    if single_use == Some(true) && !context.allow_consumed {
        errors.push(ContractError::new(
            "SINGLE_USE_CONTRACT_ALREADY_CONSUMED",
            "$.consumed_at",
            "single-use contract has already been consumed",
        ));
    }
}

fn validate_context(
    object: &Map<String, Value>,
    context: &ValidationContext,
    errors: &mut Vec<ContractError>,
) {
    if let Some(expected) = &context.expected_contract_type {
        if object.get("contract_type").and_then(Value::as_str) != Some(expected.as_str()) {
            errors.push(ContractError::new(
                "CONTRACT_TYPE_MISMATCH",
                "$.contract_type",
                "contract type does not match validation context",
            ));
        }
    }
    if let Some(expected) = &context.expected_physical_session_id {
        if object.get("physical_session_id").and_then(Value::as_str) != Some(expected.as_str()) {
            errors.push(ContractError::new(
                "PHYSICAL_SESSION_MISMATCH",
                "$.physical_session_id",
                "physical session does not match validation context",
            ));
        }
    }
    if let Some(expected) = &context.expected_authority {
        if object.get("authority").and_then(Value::as_str) != Some(expected.as_str()) {
            errors.push(ContractError::new(
                "AUTHORITY_CONTEXT_MISMATCH",
                "$.authority",
                "authority does not match validation context",
            ));
        }
    }

    let Some(payload) = object.get("payload").and_then(Value::as_object) else {
        return;
    };
    if let Some(expected) = &context.expected_recipe_hash {
        if payload.get("recipe_hash").and_then(Value::as_str) != Some(expected.as_str()) {
            errors.push(ContractError::new(
                "RECIPE_HASH_MISMATCH",
                "$.payload.recipe_hash",
                "recipe hash does not match validation context",
            ));
        }
    }

    let Some(expected) = &context.expected_artifact_hashes else {
        return;
    };
    let actual = match object.get("contract_type").and_then(Value::as_str) {
        Some("execution_lease") => payload
            .get("artifact_hashes")
            .and_then(Value::as_array)
            .map(|values| {
                values
                    .iter()
                    .filter_map(Value::as_str)
                    .map(str::to_owned)
                    .collect::<Vec<_>>()
            }),
        Some("artifact_manifest") => payload
            .get("sha256")
            .and_then(Value::as_str)
            .map(|value| vec![value.to_owned()]),
        _ => None,
    };
    if actual.as_ref() != Some(expected) {
        errors.push(ContractError::new(
            "ARTIFACT_HASH_MISMATCH",
            "$.payload",
            "artifact hashes do not match validation context",
        ));
    }
}

fn context_now(
    context: &ValidationContext,
    errors: &mut Vec<ContractError>,
) -> Option<DateTime<Utc>> {
    let value = context.now.as_deref()?;
    match parse_timestamp(value) {
        Some(timestamp) => Some(timestamp),
        None => {
            errors.push(ContractError::new(
                "INVALID_VALIDATION_CONTEXT",
                "$context.now",
                "context.now must use YYYY-MM-DDTHH:MM:SSZ",
            ));
            None
        }
    }
}

fn timestamp_field(object: &Map<String, Value>, name: &str) -> Option<DateTime<Utc>> {
    object
        .get(name)
        .and_then(Value::as_str)
        .and_then(parse_timestamp)
}

#[allow(dead_code)]
fn error_codes(errors: &[ContractError]) -> BTreeSet<&str> {
    errors.iter().map(|error| error.code.as_str()).collect()
}

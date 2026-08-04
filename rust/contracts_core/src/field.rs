use crate::canonical::canonical_json;
use crate::model::{ContractError, FieldSpec};
use chrono::{DateTime, Utc};
use regex::Regex;
use serde_json::Value;
use std::collections::BTreeSet;
use uuid::Uuid;

const TIMESTAMP_PATTERN: &str = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$";
const SHA256_PATTERN: &str = r"^[0-9a-f]{64}$";
const UUID_PATTERN: &str =
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$";
const SEMVER_PATTERN: &str = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$";

pub(crate) fn validate_field(
    value: &Value,
    spec: &FieldSpec,
    path: &str,
    errors: &mut Vec<ContractError>,
) {
    if value.is_null() {
        if !spec.nullable {
            errors.push(ContractError::new(
                "INVALID_FIELD_TYPE",
                path,
                "null is not permitted",
            ));
        }
        return;
    }

    let valid_type = match spec.field_type.as_str() {
        "string" => value.is_string(),
        "integer" => value.as_i64().is_some() || value.as_u64().is_some(),
        "boolean" => value.is_boolean(),
        "array" => value.is_array(),
        "object" => value.is_object(),
        other => {
            errors.push(ContractError::new(
                "INVALID_REGISTRY_FIELD_TYPE",
                path,
                format!("unknown registry type {other:?}"),
            ));
            return;
        }
    };
    if !valid_type {
        errors.push(ContractError::new(
            "INVALID_FIELD_TYPE",
            path,
            format!("expected {}, got {}", spec.field_type, json_type(value)),
        ));
        return;
    }

    if let Some(const_value) = &spec.const_value {
        if value != const_value {
            let code = if path == "$.schema_version" {
                "UNSUPPORTED_SCHEMA_VERSION"
            } else {
                "CONST_VALUE_MISMATCH"
            };
            errors.push(ContractError::new(
                code,
                path,
                format!("value must equal {const_value}"),
            ));
        }
    }
    if let Some(enum_values) = &spec.enum_values {
        if !enum_values.contains(value) {
            errors.push(ContractError::new(
                "ENUM_VALUE_INVALID",
                path,
                format!("value {value} is not permitted"),
            ));
        }
    }

    match spec.field_type.as_str() {
        "string" => validate_string(value.as_str().expect("string checked"), spec, path, errors),
        "integer" => validate_integer(value, spec, path, errors),
        "array" => validate_array(value.as_array().expect("array checked"), spec, path, errors),
        _ => {}
    }
}

fn validate_string(value: &str, spec: &FieldSpec, path: &str, errors: &mut Vec<ContractError>) {
    let length = value.chars().count();
    if spec.min_length.is_some_and(|minimum| length < minimum)
        || spec.max_length.is_some_and(|maximum| length > maximum)
    {
        errors.push(ContractError::new(
            "STRING_LENGTH_OUT_OF_RANGE",
            path,
            format!(
                "string length must be between {:?} and {:?}",
                spec.min_length, spec.max_length
            ),
        ));
    }
    if let Some(pattern) = &spec.pattern {
        match Regex::new(&format!("^(?:{pattern})$")) {
            Ok(regex) if !regex.is_match(value) => errors.push(ContractError::new(
                "STRING_PATTERN_MISMATCH",
                path,
                "string does not match required pattern",
            )),
            Err(error) => errors.push(ContractError::new(
                "INVALID_REGISTRY_PATTERN",
                path,
                error.to_string(),
            )),
            _ => {}
        }
    }
    match spec.format.as_deref() {
        Some("uuid") if !is_canonical_uuid(value) => errors.push(ContractError::new(
            "INVALID_UUID",
            path,
            "value is not a canonical lowercase UUID",
        )),
        Some("sha256")
            if !Regex::new(SHA256_PATTERN)
                .expect("constant regex")
                .is_match(value) =>
        {
            errors.push(ContractError::new(
                "INVALID_SHA256",
                path,
                "value is not a lowercase SHA-256 digest",
            ))
        }
        Some("timestamp") if parse_timestamp(value).is_none() => errors.push(ContractError::new(
            "INVALID_TIMESTAMP",
            path,
            "timestamp must use YYYY-MM-DDTHH:MM:SSZ",
        )),
        Some("semver")
            if !Regex::new(SEMVER_PATTERN)
                .expect("constant regex")
                .is_match(value) =>
        {
            errors.push(ContractError::new(
                "INVALID_SEMVER",
                path,
                "value must use MAJOR.MINOR.PATCH",
            ))
        }
        _ => {}
    }
}

fn validate_integer(value: &Value, spec: &FieldSpec, path: &str, errors: &mut Vec<ContractError>) {
    let number = value
        .as_i64()
        .or_else(|| value.as_u64().and_then(|number| i64::try_from(number).ok()));
    let Some(number) = number else {
        errors.push(ContractError::new(
            "INTEGER_OUT_OF_RANGE",
            path,
            "integer exceeds signed 64-bit contract range",
        ));
        return;
    };
    if spec.minimum.is_some_and(|minimum| number < minimum)
        || spec.maximum.is_some_and(|maximum| number > maximum)
    {
        errors.push(ContractError::new(
            "INTEGER_OUT_OF_RANGE",
            path,
            format!(
                "integer must be between {:?} and {:?}",
                spec.minimum, spec.maximum
            ),
        ));
    }
}

fn validate_array(value: &[Value], spec: &FieldSpec, path: &str, errors: &mut Vec<ContractError>) {
    if spec.min_items.is_some_and(|minimum| value.len() < minimum)
        || spec.max_items.is_some_and(|maximum| value.len() > maximum)
    {
        errors.push(ContractError::new(
            "ARRAY_LENGTH_OUT_OF_RANGE",
            path,
            format!(
                "array length must be between {:?} and {:?}",
                spec.min_items, spec.max_items
            ),
        ));
    }
    let item_error_count = errors.len();
    if let Some(item_spec) = &spec.items {
        for (index, child) in value.iter().enumerate() {
            validate_field(child, item_spec, &format!("{path}[{index}]"), errors);
        }
    } else {
        errors.push(ContractError::new(
            "INVALID_REGISTRY_FIELD_TYPE",
            path,
            "array field specification is missing items",
        ));
        return;
    }
    if spec.sorted_unique && errors.len() == item_error_count {
        let canonical_items: Result<Vec<String>, String> =
            value.iter().map(canonical_json).collect();
        if let Ok(canonical_items) = canonical_items {
            let sorted: BTreeSet<&String> = canonical_items.iter().collect();
            let sorted_values: Vec<String> = sorted.into_iter().cloned().collect();
            if canonical_items != sorted_values {
                let code = if spec.items.as_ref().and_then(|item| item.format.as_deref())
                    == Some("sha256")
                {
                    "HASH_LIST_NOT_SORTED_UNIQUE"
                } else {
                    "ARRAY_NOT_SORTED_UNIQUE"
                };
                errors.push(ContractError::new(
                    code,
                    path,
                    "array must be lexicographically sorted and unique",
                ));
            }
        }
    }
}

pub(crate) fn parse_timestamp(value: &str) -> Option<DateTime<Utc>> {
    if !Regex::new(TIMESTAMP_PATTERN)
        .expect("constant regex")
        .is_match(value)
    {
        return None;
    }
    DateTime::parse_from_rfc3339(value)
        .ok()
        .map(|timestamp| timestamp.with_timezone(&Utc))
}

fn is_canonical_uuid(value: &str) -> bool {
    Regex::new(UUID_PATTERN)
        .expect("constant regex")
        .is_match(value)
        && Uuid::parse_str(value).is_ok()
}

fn json_type(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}

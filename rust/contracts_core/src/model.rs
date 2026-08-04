use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt;

const REGISTRY_JSON: &str = include_str!("../../../contracts/registry.json");

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Registry {
    pub schema: String,
    pub registry_version: u64,
    pub canonical_json: CanonicalJsonSpec,
    pub envelope: Envelope,
    pub contracts: BTreeMap<String, ContractDefinition>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CanonicalJsonSpec {
    pub array_order: String,
    pub encoding: String,
    pub numbers: String,
    pub object_keys: String,
    pub whitespace: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Envelope {
    pub required: Vec<String>,
    pub fields: BTreeMap<String, FieldSpec>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FieldSpec {
    #[serde(rename = "type")]
    pub field_type: String,
    #[serde(default)]
    pub nullable: bool,
    #[serde(rename = "const", default)]
    pub const_value: Option<Value>,
    #[serde(rename = "enum", default)]
    pub enum_values: Option<Vec<Value>>,
    #[serde(default)]
    pub format: Option<String>,
    #[serde(default)]
    pub pattern: Option<String>,
    #[serde(default)]
    pub minimum: Option<i64>,
    #[serde(default)]
    pub maximum: Option<i64>,
    #[serde(default)]
    pub min_length: Option<usize>,
    #[serde(default)]
    pub max_length: Option<usize>,
    #[serde(default)]
    pub min_items: Option<usize>,
    #[serde(default)]
    pub max_items: Option<usize>,
    #[serde(default)]
    pub sorted_unique: bool,
    #[serde(default)]
    pub items: Option<Box<FieldSpec>>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContractDefinition {
    pub authority: String,
    pub physical_session: String,
    pub expiry: String,
    pub single_use: bool,
    pub payload_required: Vec<String>,
    pub payload_fields: BTreeMap<String, FieldSpec>,
    #[serde(default)]
    pub timestamp_order: Vec<(String, String)>,
    #[serde(default)]
    pub dangerous_auto_promotion: bool,
}

#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ValidationContext {
    #[serde(default)]
    pub now: Option<String>,
    #[serde(default)]
    pub expected_contract_type: Option<String>,
    #[serde(default)]
    pub expected_physical_session_id: Option<String>,
    #[serde(default)]
    pub expected_recipe_hash: Option<String>,
    #[serde(default)]
    pub expected_artifact_hashes: Option<Vec<String>>,
    #[serde(default)]
    pub expected_authority: Option<String>,
    #[serde(default)]
    pub allow_consumed: bool,
}

#[derive(Debug, Clone, Eq, PartialEq, Ord, PartialOrd, Hash, Serialize, Deserialize)]
pub struct ContractError {
    pub code: String,
    pub path: String,
    pub message: String,
}

impl ContractError {
    pub(crate) fn new(code: &str, path: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.to_owned(),
            path: path.into(),
            message: message.into(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationResult {
    pub ok: bool,
    pub errors: Vec<ContractError>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub canonical: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sha256: Option<String>,
}

#[derive(Debug)]
pub enum RegistryError {
    Json(serde_json::Error),
    UnsupportedSchema(String),
    InvalidPolicy(String),
}

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(error) => write!(f, "{error}"),
            Self::UnsupportedSchema(schema) => {
                write!(f, "unsupported contract registry schema {schema:?}")
            }
            Self::InvalidPolicy(message) => write!(f, "{message}"),
        }
    }
}

impl std::error::Error for RegistryError {}

pub fn decode_registry_json(document: &str) -> Result<Registry, RegistryError> {
    let registry: Registry = serde_json::from_str(document).map_err(RegistryError::Json)?;
    validate_registry_policy(&registry)?;
    Ok(registry)
}

pub fn load_registry() -> Result<Registry, RegistryError> {
    decode_registry_json(REGISTRY_JSON)
}

fn validate_registry_policy(registry: &Registry) -> Result<(), RegistryError> {
    if registry.schema != "techguytool-huawei.contract-registry.v1"
        || registry.registry_version != 1
    {
        return Err(RegistryError::UnsupportedSchema(registry.schema.clone()));
    }
    if registry.canonical_json.array_order != "preserved"
        || registry.canonical_json.encoding != "utf-8"
        || registry.canonical_json.numbers != "json-integer-only"
        || registry.canonical_json.object_keys != "lexicographic"
        || registry.canonical_json.whitespace != "none"
    {
        return Err(RegistryError::InvalidPolicy(
            "unsupported canonical JSON policy".to_owned(),
        ));
    }
    if registry.envelope.required.is_empty() || registry.envelope.fields.is_empty() {
        return Err(RegistryError::InvalidPolicy(
            "registry envelope must define required fields".to_owned(),
        ));
    }
    for required in &registry.envelope.required {
        if !registry.envelope.fields.contains_key(required) {
            return Err(RegistryError::InvalidPolicy(format!(
                "registry envelope references undefined field {required:?}"
            )));
        }
    }
    let contract_type_values = registry
        .envelope
        .fields
        .get("contract_type")
        .and_then(|spec| spec.enum_values.as_ref())
        .ok_or_else(|| {
            RegistryError::InvalidPolicy(
                "registry contract_type field must define an enum".to_owned(),
            )
        })?;
    let enum_names = contract_type_values
        .iter()
        .map(Value::as_str)
        .collect::<Option<Vec<_>>>()
        .ok_or_else(|| {
            RegistryError::InvalidPolicy(
                "registry contract_type enum must contain strings".to_owned(),
            )
        })?;
    if enum_names.len() != registry.contracts.len()
        || enum_names
            .iter()
            .any(|name| !registry.contracts.contains_key(*name))
    {
        return Err(RegistryError::InvalidPolicy(
            "registry contract_type enum must match registered contracts".to_owned(),
        ));
    }
    for (name, definition) in &registry.contracts {
        if definition.payload_required.is_empty() || definition.payload_fields.is_empty() {
            return Err(RegistryError::InvalidPolicy(format!(
                "contract {name:?} must define payload fields"
            )));
        }
        if definition
            .payload_required
            .iter()
            .any(|field| !definition.payload_fields.contains_key(field))
        {
            return Err(RegistryError::InvalidPolicy(format!(
                "contract {name:?} references an undefined payload field"
            )));
        }
    }
    Ok(())
}

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt;

const REGISTRY_JSON: &str = include_str!("../../../contracts/registry.json");

#[derive(Debug, Clone, Deserialize)]
pub struct Registry {
    pub schema: String,
    pub registry_version: u64,
    pub envelope: Envelope,
    pub contracts: BTreeMap<String, ContractDefinition>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Envelope {
    pub required: Vec<String>,
    pub fields: BTreeMap<String, FieldSpec>,
}

#[derive(Debug, Clone, Deserialize)]
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
}

impl fmt::Display for RegistryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(error) => write!(f, "{error}"),
            Self::UnsupportedSchema(schema) => {
                write!(f, "unsupported contract registry schema {schema:?}")
            }
        }
    }
}

impl std::error::Error for RegistryError {}

pub fn load_registry() -> Result<Registry, RegistryError> {
    let registry: Registry = serde_json::from_str(REGISTRY_JSON).map_err(RegistryError::Json)?;
    if registry.schema != "techguytool-huawei.contract-registry.v1"
        || registry.registry_version != 1
    {
        return Err(RegistryError::UnsupportedSchema(registry.schema));
    }
    Ok(registry)
}

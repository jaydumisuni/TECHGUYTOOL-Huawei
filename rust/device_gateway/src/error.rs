use std::fmt;
use std::io;

#[derive(Debug)]
pub enum GatewayError {
    InvalidInput(String),
    NotFound(String),
    Conflict(String),
    PolicyDenied(String),
    ContractRejected(String),
    JournalCorrupt(String),
    Storage(String),
    Io(String),
    Json(String),
    Protocol(String),
}

impl GatewayError {
    pub fn code(&self) -> &'static str {
        match self {
            Self::InvalidInput(_) => "INVALID_INPUT",
            Self::NotFound(_) => "NOT_FOUND",
            Self::Conflict(_) => "CONFLICT",
            Self::PolicyDenied(_) => "POLICY_DENIED",
            Self::ContractRejected(_) => "CONTRACT_REJECTED",
            Self::JournalCorrupt(_) => "JOURNAL_CORRUPT",
            Self::Storage(_) => "STORAGE_ERROR",
            Self::Io(_) => "IO_ERROR",
            Self::Json(_) => "JSON_ERROR",
            Self::Protocol(_) => "PROTOCOL_ERROR",
        }
    }
}

impl fmt::Display for GatewayError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidInput(message)
            | Self::NotFound(message)
            | Self::Conflict(message)
            | Self::PolicyDenied(message)
            | Self::ContractRejected(message)
            | Self::JournalCorrupt(message)
            | Self::Storage(message)
            | Self::Io(message)
            | Self::Json(message)
            | Self::Protocol(message) => formatter.write_str(message),
        }
    }
}

impl std::error::Error for GatewayError {}

impl From<rusqlite::Error> for GatewayError {
    fn from(error: rusqlite::Error) -> Self {
        Self::Storage(error.to_string())
    }
}

impl From<io::Error> for GatewayError {
    fn from(error: io::Error) -> Self {
        Self::Io(error.to_string())
    }
}

impl From<serde_json::Error> for GatewayError {
    fn from(error: serde_json::Error) -> Self {
        Self::Json(error.to_string())
    }
}

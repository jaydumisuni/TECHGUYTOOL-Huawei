use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::env;
use std::fs;
use std::path::Path;
use std::process::ExitCode;

#[derive(Debug, Deserialize)]
struct Manifest {
    schema: u32,
    product: String,
    actions: Vec<Action>,
}

#[derive(Debug, Deserialize)]
struct Action {
    id: String,
    label: String,
    #[serde(default)]
    guarded: bool,
    #[serde(default)]
    guard_reason: String,
}

#[derive(Debug, Serialize)]
struct Audit {
    ok: bool,
    schema: u32,
    product: String,
    action_count: usize,
    errors: Vec<String>,
}

fn audit(path: &Path) -> Result<Audit, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    let manifest: Manifest = serde_json::from_str(&raw).map_err(|e| format!("invalid JSON: {e}"))?;
    let mut errors = Vec::new();
    let mut ids = BTreeSet::new();

    if manifest.schema != 1 {
        errors.push(format!("unsupported schema {}", manifest.schema));
    }
    if manifest.product.trim().is_empty() {
        errors.push("product name is empty".to_string());
    }
    if manifest.actions.is_empty() {
        errors.push("action list is empty".to_string());
    }

    for action in &manifest.actions {
        if action.id.trim().is_empty() {
            errors.push("action id is empty".to_string());
        }
        if !action
            .id
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
        {
            errors.push(format!("action id is not canonical: {}", action.id));
        }
        if !ids.insert(action.id.clone()) {
            errors.push(format!("duplicate action id: {}", action.id));
        }
        if action.label.trim().is_empty() {
            errors.push(format!("action {} has no label", action.id));
        }
        if action.guarded && action.guard_reason.trim().is_empty() {
            errors.push(format!("guarded action {} has no reason", action.id));
        }
    }

    Ok(Audit {
        ok: errors.is_empty(),
        schema: manifest.schema,
        product: manifest.product,
        action_count: manifest.actions.len(),
        errors,
    })
}

fn main() -> ExitCode {
    let Some(path) = env::args().nth(1) else {
        eprintln!("usage: techguy_health_core <action_manifest.json>");
        return ExitCode::from(2);
    };
    match audit(Path::new(&path)) {
        Ok(report) => {
            println!("{}", serde_json::to_string(&report).expect("serialize audit"));
            if report.ok { ExitCode::SUCCESS } else { ExitCode::from(1) }
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}

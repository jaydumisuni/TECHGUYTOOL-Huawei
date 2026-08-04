use serde_json::Value;
use std::env;
use std::fs;
use std::process::ExitCode;
use techguy_contracts_core::{
    canonical_json, load_registry, validate_contract_json, ValidationContext,
};

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::from(2)
        }
    }
}

fn run() -> Result<ExitCode, String> {
    let args: Vec<String> = env::args().collect();
    let command = args.get(1).map(String::as_str).unwrap_or("help");
    match command {
        "validate" => {
            let contract_path = option(&args, "--contract")?;
            let context_path = option_optional(&args, "--context");
            let contract_json =
                fs::read_to_string(contract_path).map_err(|error| error.to_string())?;
            let context = if let Some(path) = context_path {
                serde_json::from_str::<ValidationContext>(
                    &fs::read_to_string(path).map_err(|error| error.to_string())?,
                )
                .map_err(|error| error.to_string())?
            } else {
                ValidationContext::default()
            };
            let registry = load_registry().map_err(|error| error.to_string())?;
            let result = validate_contract_json(&contract_json, &context, &registry);
            println!(
                "{}",
                serde_json::to_string(&result).map_err(|error| error.to_string())?
            );
            Ok(if result.ok {
                ExitCode::SUCCESS
            } else {
                ExitCode::from(1)
            })
        }
        "canonicalize" => {
            let contract_path = option(&args, "--contract")?;
            let contract: Value = serde_json::from_str(
                &fs::read_to_string(contract_path).map_err(|error| error.to_string())?,
            )
            .map_err(|error| error.to_string())?;
            println!("{}", canonical_json(&contract)?);
            Ok(ExitCode::SUCCESS)
        }
        "help" | "--help" | "-h" => {
            println!("ttg-contracts validate --contract FILE [--context FILE]");
            println!("ttg-contracts canonicalize --contract FILE");
            Ok(ExitCode::SUCCESS)
        }
        other => Err(format!("unknown command {other:?}")),
    }
}

fn option<'a>(args: &'a [String], name: &str) -> Result<&'a str, String> {
    option_optional(args, name).ok_or_else(|| format!("missing required option {name}"))
}

fn option_optional<'a>(args: &'a [String], name: &str) -> Option<&'a str> {
    args.iter()
        .position(|value| value == name)
        .and_then(|index| args.get(index + 1))
        .map(String::as_str)
}

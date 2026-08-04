use serde_json::json;
use std::env;
use std::io::{self, Write};
use std::net::TcpListener;
use std::path::PathBuf;
use std::process;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use techguy_device_gateway::{
    run_listener, Gateway, GatewayError, DEVICE_AUTHORITY, XRAY_AUTHORITY,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("{}: {}", error.code(), error);
        process::exit(2);
    }
}

fn run() -> Result<(), GatewayError> {
    let mut arguments = env::args().skip(1);
    let command = arguments.next().unwrap_or_else(|| "help".to_owned());
    let remaining: Vec<String> = arguments.collect();
    match command.as_str() {
        "serve" => serve(&remaining),
        "doctor" => print_doctor(&remaining),
        "snapshot" => print_snapshot(&remaining),
        "help" | "--help" | "-h" => {
            print_help();
            Ok(())
        }
        other => Err(GatewayError::InvalidInput(format!(
            "unknown gateway command {other:?}"
        ))),
    }
}

fn serve(arguments: &[String]) -> Result<(), GatewayError> {
    let db = required_path(arguments, "--db")?;
    let listen =
        option_value(arguments, "--listen").unwrap_or_else(|| "127.0.0.1:49321".to_owned());
    let gateway = Arc::new(Gateway::open(db)?);
    let listener = TcpListener::bind(listen)?;
    let address = listener.local_addr()?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "device_authority": DEVICE_AUTHORITY,
            "listen": address.to_string(),
            "status": "ready",
            "xray_authority": XRAY_AUTHORITY
        }))?
    );
    io::stdout().flush()?;
    run_listener(gateway, listener, Arc::new(AtomicBool::new(false)))
}

fn print_doctor(arguments: &[String]) -> Result<(), GatewayError> {
    let gateway = Gateway::inspect(required_path(arguments, "--db")?)?;
    println!("{}", serde_json::to_string_pretty(&gateway.doctor()?)?);
    Ok(())
}

fn print_snapshot(arguments: &[String]) -> Result<(), GatewayError> {
    let gateway = Gateway::inspect(required_path(arguments, "--db")?)?;
    println!("{}", serde_json::to_string_pretty(&gateway.snapshot()?)?);
    Ok(())
}

fn required_path(arguments: &[String], name: &str) -> Result<PathBuf, GatewayError> {
    option_value(arguments, name)
        .map(PathBuf::from)
        .ok_or_else(|| GatewayError::InvalidInput(format!("missing required argument {name}")))
}

fn option_value(arguments: &[String], name: &str) -> Option<String> {
    arguments
        .iter()
        .position(|argument| argument == name)
        .and_then(|index| arguments.get(index + 1))
        .cloned()
}

fn print_help() {
    println!(
        "TECHGUYTOOL Huawei TTG Device Gateway\n\n\
         Usage:\n\
           ttg-device-gateway serve --db <path> [--listen 127.0.0.1:49321]\n\
           ttg-device-gateway doctor --db <path>\n\
           ttg-device-gateway snapshot --db <path>\n\n\
         Phase 3 is device-inert: device authority remains none."
    );
}

use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use techguy_device_gateway::{run_listener, Gateway};
use tempfile::tempdir;

#[test]
fn loopback_clients_reconnect_to_the_same_operation() {
    let root = tempdir().expect("tempdir");
    let gateway = Arc::new(Gateway::open(root.path().join("gateway.sqlite3")).expect("gateway"));
    let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
    let address = listener.local_addr().expect("address");
    let shutdown = Arc::new(AtomicBool::new(false));
    let server_gateway = Arc::clone(&gateway);
    let server_shutdown = Arc::clone(&shutdown);
    let server = thread::spawn(move || {
        run_listener(server_gateway, listener, server_shutdown).expect("server")
    });
    thread::sleep(Duration::from_millis(40));

    let session = request(
        address,
        json!({
            "request_id": "open-session",
            "command": {
                "name": "open_physical_session",
                "params": {"fingerprint_sha256": "a".repeat(64)}
            }
        }),
    );
    let session_id = session["result"]["session_id"]
        .as_str()
        .expect("session id")
        .to_owned();
    let operation = request(
        address,
        json!({
            "request_id": "open-operation",
            "command": {
                "name": "open_operation",
                "params": {
                    "physical_session_id": session_id,
                    "request_sha256": "b".repeat(64)
                }
            }
        }),
    );
    let operation_id = operation["result"]["operation_id"]
        .as_str()
        .expect("operation id")
        .to_owned();

    let recovered = request(
        address,
        json!({
            "request_id": "get-operation-from-new-client",
            "command": {
                "name": "get_operation",
                "params": {"operation_id": operation_id}
            }
        }),
    );
    assert!(recovered["ok"].as_bool().expect("ok"));
    assert_eq!(recovered["result"]["stage"], "requested");

    let shutdown_response = request(
        address,
        json!({
            "request_id": "shutdown",
            "command": {"name": "shutdown"}
        }),
    );
    assert!(shutdown_response["ok"].as_bool().expect("shutdown ok"));
    server.join().expect("join");
}

fn request(address: std::net::SocketAddr, payload: Value) -> Value {
    let mut stream = TcpStream::connect(address).expect("connect");
    stream
        .write_all(format!("{}\n", payload).as_bytes())
        .expect("write");
    stream.flush().expect("flush");
    let mut line = String::new();
    BufReader::new(stream)
        .read_line(&mut line)
        .expect("read");
    serde_json::from_str(&line).expect("response JSON")
}

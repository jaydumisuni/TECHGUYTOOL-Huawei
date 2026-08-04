use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::AtomicBool;
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::Duration;
use techguy_device_gateway::{run_listener, Gateway};
use tempfile::tempdir;

#[test]
fn loopback_clients_reconnect_to_the_same_operation() {
    let root = tempdir().expect("tempdir");
    let (address, server) = start_server(root.path().join("gateway.sqlite3"));

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

    stop_server(address, server);
}

#[test]
fn oversized_request_without_newline_is_rejected_before_unbounded_buffering() {
    let root = tempdir().expect("tempdir");
    let (address, server) = start_server(root.path().join("gateway.sqlite3"));
    let mut stream = TcpStream::connect(address).expect("connect");
    stream
        .set_write_timeout(Some(Duration::from_secs(5)))
        .expect("write timeout");
    stream
        .set_read_timeout(Some(Duration::from_secs(5)))
        .expect("read timeout");
    stream
        .write_all(&vec![b'{'; 1024 * 1024 + 1])
        .expect("write oversized request");
    stream.flush().expect("flush");
    let mut line = String::new();
    BufReader::new(stream)
        .read_line(&mut line)
        .expect("read rejection");
    let response: Value = serde_json::from_str(&line).expect("response JSON");
    assert!(!response["ok"].as_bool().expect("ok field"));
    assert_eq!(response["error"]["code"], "PROTOCOL_ERROR");
    assert!(response["error"]["message"]
        .as_str()
        .expect("message")
        .contains("one MiB"));

    stop_server(address, server);
}

fn start_server(database: std::path::PathBuf) -> (SocketAddr, JoinHandle<()>) {
    let gateway = Arc::new(Gateway::open(database).expect("gateway"));
    let listener = TcpListener::bind("127.0.0.1:0").expect("listener");
    let address = listener.local_addr().expect("address");
    let shutdown = Arc::new(AtomicBool::new(false));
    let server = thread::spawn(move || run_listener(gateway, listener, shutdown).expect("server"));
    thread::sleep(Duration::from_millis(40));
    (address, server)
}

fn stop_server(address: SocketAddr, server: JoinHandle<()>) {
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

fn request(address: SocketAddr, payload: Value) -> Value {
    let mut stream = TcpStream::connect(address).expect("connect");
    stream
        .write_all(format!("{}\n", payload).as_bytes())
        .expect("write");
    stream.flush().expect("flush");
    let mut line = String::new();
    BufReader::new(stream).read_line(&mut line).expect("read");
    serde_json::from_str(&line).expect("response JSON")
}

use crate::error::GatewayError;
use crate::gateway::Gateway;
use crate::protocol::{dispatch, GatewayRequest, GatewayResponse};
use std::io::{BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

const MAX_REQUEST_BYTES: usize = 1024 * 1024;

pub fn run_listener(
    gateway: Arc<Gateway>,
    listener: TcpListener,
    shutdown: Arc<AtomicBool>,
) -> Result<(), GatewayError> {
    listener.set_nonblocking(true)?;
    while !shutdown.load(Ordering::SeqCst) {
        match listener.accept() {
            Ok((stream, peer)) => {
                if !peer.ip().is_loopback() {
                    continue;
                }
                let gateway = Arc::clone(&gateway);
                let shutdown = Arc::clone(&shutdown);
                thread::spawn(move || {
                    let _ = handle_client(gateway, stream, peer, shutdown);
                });
            }
            Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(20));
            }
            Err(error) => return Err(error.into()),
        }
    }
    Ok(())
}

fn handle_client(
    gateway: Arc<Gateway>,
    mut stream: TcpStream,
    _peer: SocketAddr,
    shutdown: Arc<AtomicBool>,
) -> Result<(), GatewayError> {
    stream.set_read_timeout(Some(Duration::from_secs(10)))?;
    stream.set_write_timeout(Some(Duration::from_secs(10)))?;
    let reader_stream = stream.try_clone()?;
    let mut reader = BufReader::new(reader_stream);
    loop {
        let mut line = String::new();
        let read = reader.read_line(&mut line)?;
        if read == 0 {
            return Ok(());
        }
        if line.len() > MAX_REQUEST_BYTES {
            let error = GatewayError::Protocol("request exceeds one MiB".to_owned());
            write_response(
                &mut stream,
                &GatewayResponse::failure("unknown".to_owned(), &error),
            )?;
            return Ok(());
        }
        let request: GatewayRequest = match serde_json::from_str(line.trim_end()) {
            Ok(request) => request,
            Err(error) => {
                let gateway_error =
                    GatewayError::Protocol(format!("invalid request JSON: {error}"));
                write_response(
                    &mut stream,
                    &GatewayResponse::failure("unknown".to_owned(), &gateway_error),
                )?;
                continue;
            }
        };
        let should_shutdown = request.command.is_shutdown();
        let response = dispatch(&gateway, request);
        write_response(&mut stream, &response)?;
        if should_shutdown && response.ok {
            shutdown.store(true, Ordering::SeqCst);
            return Ok(());
        }
    }
}

fn write_response(stream: &mut TcpStream, response: &GatewayResponse) -> Result<(), GatewayError> {
    serde_json::to_writer(&mut *stream, response)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    Ok(())
}

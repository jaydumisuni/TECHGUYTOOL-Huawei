use crate::error::GatewayError;
use crate::gateway::Gateway;
use crate::protocol::{dispatch, GatewayRequest, GatewayResponse};
use std::io::{self, BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

const MAX_REQUEST_BYTES: usize = 1024 * 1024;
const ACCEPT_RETRY_DELAY: Duration = Duration::from_millis(100);

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
                    if let Err(error) = handle_client(gateway, stream, peer, shutdown) {
                        eprintln!("gateway client handler failed: {error}");
                    }
                });
            }
            Err(error) if error.kind() == io::ErrorKind::WouldBlock => {
                thread::sleep(Duration::from_millis(20));
            }
            Err(error) if is_transient_accept_error(&error) => {
                eprintln!("transient gateway accept error: {error}");
                thread::sleep(ACCEPT_RETRY_DELAY);
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
        let line = match read_request(&mut reader)? {
            RequestRead::Eof => return Ok(()),
            RequestRead::Oversized => {
                let error = GatewayError::Protocol("request exceeds one MiB".to_owned());
                write_response(
                    &mut stream,
                    &GatewayResponse::failure("unknown".to_owned(), &error),
                )?;
                return Ok(());
            }
            RequestRead::Incomplete => {
                let error =
                    GatewayError::Protocol("request must be terminated by a newline".to_owned());
                write_response(
                    &mut stream,
                    &GatewayResponse::failure("unknown".to_owned(), &error),
                )?;
                return Ok(());
            }
            RequestRead::Line(line) => line,
        };
        let request: GatewayRequest = match serde_json::from_slice(&line) {
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

fn read_request(reader: &mut BufReader<TcpStream>) -> io::Result<RequestRead> {
    let mut line = Vec::new();
    loop {
        let buffer = reader.fill_buf()?;
        if buffer.is_empty() {
            return Ok(if line.is_empty() {
                RequestRead::Eof
            } else {
                RequestRead::Incomplete
            });
        }
        if let Some(newline) = buffer.iter().position(|byte| *byte == b'\n') {
            if line.len() + newline > MAX_REQUEST_BYTES {
                return Ok(RequestRead::Oversized);
            }
            line.extend_from_slice(&buffer[..newline]);
            reader.consume(newline + 1);
            return Ok(RequestRead::Line(line));
        }
        let available = buffer.len();
        if line.len() + available > MAX_REQUEST_BYTES {
            return Ok(RequestRead::Oversized);
        }
        line.extend_from_slice(buffer);
        reader.consume(available);
    }
}

fn is_transient_accept_error(error: &io::Error) -> bool {
    matches!(
        error.kind(),
        io::ErrorKind::ConnectionAborted
            | io::ErrorKind::ConnectionReset
            | io::ErrorKind::Interrupted
    ) || matches!(error.raw_os_error(), Some(23 | 24 | 10024))
}

fn write_response(stream: &mut TcpStream, response: &GatewayResponse) -> Result<(), GatewayError> {
    serde_json::to_writer(&mut *stream, response)?;
    stream.write_all(b"\n")?;
    stream.flush()?;
    Ok(())
}

enum RequestRead {
    Eof,
    Incomplete,
    Line(Vec<u8>),
    Oversized,
}

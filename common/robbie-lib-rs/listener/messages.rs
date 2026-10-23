//! Message targets. --message-url picks one by its scheme (see docs/relm.md).

use std::io::Write;
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};

use anyhow::{bail, Context};

use super::irelm::Message;

pub trait Sink: Send + Sync {
    fn send(&self, message: &Message);

    /// Text being spoken, from the debug engine. Printed as "say: text" on stdout.
    fn say(&self, text: &str) {
        let mut out = std::io::stdout().lock();
        let _ = writeln!(out, "say: {text}");
        let _ = out.flush();
    }
}

/// The line form: "sub, action". A reader splits on the first comma.
pub fn line(message: &Message) -> String {
    format!("{}, {}\n", message.sub, message.action)
}

pub struct Stdout;

impl Sink for Stdout {
    fn send(&self, message: &Message) {
        let mut out = std::io::stdout().lock();
        let _ = out.write_all(line(message).as_bytes());
        let _ = out.flush();
    }
}

/// Serves the lines to every client that connects, e.g. nc host 2000.
pub struct Tcp {
    clients: Arc<Mutex<Vec<TcpStream>>>,
    pub addr: std::net::SocketAddr,
}

impl Tcp {
    pub fn bind(addr: &str) -> anyhow::Result<Self> {
        let listener =
            TcpListener::bind(addr).with_context(|| format!("cannot listen on {addr}"))?;
        let local = listener.local_addr()?;
        let clients = Arc::new(Mutex::new(Vec::new()));
        let accepted = clients.clone();
        std::thread::spawn(move || {
            for stream in listener.incoming().flatten() {
                let _ = stream.set_nodelay(true);
                accepted
                    .lock()
                    .unwrap_or_else(|e| e.into_inner())
                    .push(stream);
            }
        });
        Ok(Self {
            clients,
            addr: local,
        })
    }
}

impl Sink for Tcp {
    fn send(&self, message: &Message) {
        let text = line(message);
        let mut clients = self.clients.lock().unwrap_or_else(|e| e.into_inner());
        clients.retain_mut(|c| c.write_all(text.as_bytes()).is_ok());
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Record {
    Message(Message),
    Say(String),
}

/// Keeps everything sent, with the time, for tests and for a listener built into another program.
#[derive(Default, Clone)]
pub struct Collect {
    pub sent: Arc<Mutex<Vec<(std::time::Instant, Record)>>>,
}

impl Collect {
    fn push(&self, record: Record) {
        let mut sent = self.sent.lock().unwrap_or_else(|e| e.into_inner());
        sent.push((std::time::Instant::now(), record));
    }

    pub fn records(&self) -> Vec<Record> {
        let sent = self.sent.lock().unwrap_or_else(|e| e.into_inner());
        sent.iter().map(|(_, r)| r.clone()).collect()
    }
}

impl Sink for Collect {
    fn send(&self, message: &Message) {
        self.push(Record::Message(message.clone()));
    }

    fn say(&self, text: &str) {
        self.push(Record::Say(text.to_string()));
    }
}

pub fn open(url: &str) -> anyhow::Result<Box<dyn Sink>> {
    let (scheme, rest) = url.split_once(':').unwrap_or((url, ""));
    match scheme {
        "stdout" => Ok(Box::new(Stdout)),
        "tcp" => Ok(Box::new(Tcp::bind(rest.trim_start_matches("//"))?)),
        "mqtt" | "ros" => bail!("--message-url {scheme}: is not built yet"),
        _ => bail!(
            "--message-url {url}: unknown scheme, use stdout:, tcp://host:port, mqtt:// or ros:"
        ),
    }
}

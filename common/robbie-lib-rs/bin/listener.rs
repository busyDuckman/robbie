//! listener: IRELM in (stdin or HTTP), speech, beeps and audio out, messages to the robot.
//! See docs/relm.md for the options and the API.

use std::io::{BufRead, Read};
use std::path::PathBuf;
use std::process::exit;
use std::sync::Arc;

use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Router,
};
use clap::{Parser, ValueEnum};
use robbie_lib::listener::{
    config::Config, device, engine, irelm, marytts, messages, speaker, Listener, Settings, Vad,
};

#[derive(Clone, Copy, ValueEnum)]
enum TtsEngine {
    Marytts,
    Debug,
}

#[derive(Parser)]
#[command(
    name = "listener",
    about = "Speak IRELM and send its messages to the robot."
)]
struct Args {
    /// listener.yaml (mood and the VAD to prosody mapping)
    #[arg(long)]
    config: Option<PathBuf>,
    /// don't use marks: split speech at messages instead
    #[arg(long)]
    no_marks: bool,
    /// playback device (part of its name, "list" to see them), or a .wav file to write
    #[arg(long)]
    device: Option<String>,
    /// debug prints the text ("say: ..." on stdout) and makes silence
    #[arg(long, value_enum, default_value = "marytts")]
    tts_engine: TtsEngine,
    #[arg(long, default_value = "http://127.0.0.1:59125")]
    tts_url: String,
    /// audio files for AUDIO live here
    #[arg(long)]
    audio_dir: Option<PathBuf>,
    /// ffmpeg -af filter for beeps
    #[arg(long)]
    beep_post: Option<String>,
    /// ffmpeg -af filter for audio files
    #[arg(long)]
    play_post: Option<String>,
    /// ffmpeg -af filter for speech
    #[arg(long)]
    tts_post: Option<String>,
    /// one IRELM message per stdin line
    #[arg(long)]
    interactive: bool,
    /// serve the API on this port
    #[arg(long, value_name = "PORT")]
    serve: Option<u16>,
    /// address the API binds to
    #[arg(long, default_value = "127.0.0.1")]
    host: String,
    /// on interrupt, do not send the closes of started messages
    #[arg(long)]
    allow_message_interrupt: bool,
    /// where messages go: stdout:, tcp://host:port
    #[arg(long, default_value = "stdout:")]
    message_url: String,
    /// send messages this many ms early, to make up for latency
    #[arg(long, default_value_t = 0.0)]
    message_early: f64,
}

fn fail(message: impl std::fmt::Display) -> ! {
    eprintln!("listener: {message}");
    exit(1);
}

struct StderrLog;

impl log::Log for StderrLog {
    fn enabled(&self, metadata: &log::Metadata) -> bool {
        metadata.level() <= log::Level::Info
    }

    fn log(&self, record: &log::Record) {
        if self.enabled(record.metadata()) {
            eprintln!("listener: {}", record.args());
        }
    }

    fn flush(&self) {}
}

fn build(args: &Args) -> anyhow::Result<Listener> {
    let config = match &args.config {
        Some(path) => Config::load(path)?,
        None => Config::default(),
    };
    let settings = Settings {
        marks: !args.no_marks,
        allow_message_interrupt: args.allow_message_interrupt,
        message_early: args.message_early / 1000.0,
        audio_dir: args.audio_dir.clone(),
        beep_post: args.beep_post.clone(),
        play_post: args.play_post.clone(),
        tts_post: args.tts_post.clone(),
        config,
    };
    let engine: Box<dyn engine::Engine> = match args.tts_engine {
        TtsEngine::Debug => Box::new(engine::DebugEngine::default()),
        TtsEngine::Marytts => Box::new(marytts::MaryTts {
            url: args.tts_url.clone(),
            locale: std::env::var("LOCALE")
                .ok()
                .filter(|l| !l.is_empty())
                .unwrap_or_else(|| "en_GB".into()),
            voice: None,
            extra: Vec::new(),
            http: Box::new(marytts::Ureq),
        }),
    };
    let device: Box<dyn device::Device> = match args.device.as_deref() {
        Some(d) if d.to_lowercase().ends_with(".wav") => Box::new(device::FileDevice::create(d)?),
        name => Box::new(speaker::Speaker::open(name)?),
    };
    let sink = messages::open(&args.message_url)?;
    Ok(Listener::new(settings, engine, device, sink))
}

fn num(x: f64) -> String {
    let s = format!("{x:.3}");
    s.trim_end_matches('0').trim_end_matches('.').to_string()
}

type Reply = (StatusCode, String);

async fn say(State(l): State<Arc<Listener>>, body: String) -> Reply {
    match l.say(&body) {
        Ok(()) => (StatusCode::ACCEPTED, "queued".into()),
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()),
    }
}

async fn interrupt(State(l): State<Arc<Listener>>) -> Reply {
    l.interrupt();
    (StatusCode::OK, "ok".into())
}

async fn get_mood(State(l): State<Arc<Listener>>) -> Reply {
    let m = l.mood();
    let vad = format!(
        r#"<VAD v="{}" a="{}" d="{}"/>"#,
        num(m.v),
        num(m.a),
        num(m.d)
    );
    (StatusCode::OK, vad)
}

/// "none" (or a missing param) keeps the current value.
async fn put_mood(State(l): State<Arc<Listener>>, body: String) -> Reply {
    match irelm::parse_vad(&body) {
        Ok([v, a, d]) => {
            let m = l.mood();
            l.set_mood(Vad {
                v: v.unwrap_or(m.v),
                a: a.unwrap_or(m.a),
                d: d.unwrap_or(m.d),
            });
            (StatusCode::OK, "ok".into())
        }
        Err(e) => (StatusCode::BAD_REQUEST, e.to_string()),
    }
}

async fn status(
    State(l): State<Arc<Listener>>,
) -> (StatusCode, [(&'static str, &'static str); 1], String) {
    let s = l.status();
    let body = serde_json::json!({
        "state": if s.speaking { "speaking" } else { "idle" },
        "queued": s.queued,
    });
    (
        StatusCode::OK,
        [("content-type", "application/json")],
        body.to_string(),
    )
}

async fn shutdown_signal() {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};
        let mut term = signal(SignalKind::terminate()).unwrap_or_else(|e| fail(e));
        tokio::select! {
            _ = tokio::signal::ctrl_c() => {}
            _ = term.recv() => {}
        }
    }
    #[cfg(not(unix))]
    let _ = tokio::signal::ctrl_c().await;
}

fn serve(listener: Arc<Listener>, host: &str, port: u16) {
    let runtime = tokio::runtime::Runtime::new().unwrap_or_else(|e| fail(e));
    runtime.block_on(async {
        let app = Router::new()
            .route("/say", post(say))
            .route("/interrupt", post(interrupt))
            .route("/mood", get(get_mood).put(put_mood))
            .route("/status", get(status))
            .route("/health", get(|| async { "ok" }))
            .with_state(listener);
        let socket = tokio::net::TcpListener::bind((host, port))
            .await
            .unwrap_or_else(|e| fail(e));
        eprintln!("listener: serving on http://{host}:{port}/");
        axum::serve(socket, app)
            .with_graceful_shutdown(shutdown_signal())
            .await
            .unwrap_or_else(|e| fail(e));
        eprintln!("listener: clean shutdown");
    });
}

fn main() {
    let _ = log::set_logger(&StderrLog).map(|()| log::set_max_level(log::LevelFilter::Info));
    let args = Args::parse();
    if args.device.as_deref() == Some("list") {
        for name in speaker::device_names() {
            println!("{name}");
        }
        return;
    }
    let listener = Arc::new(build(&args).unwrap_or_else(|e| fail(format!("{e:#}"))));

    if args.interactive {
        let l = listener.clone();
        let serving = args.serve.is_some();
        let reader = std::thread::spawn(move || {
            for line in std::io::stdin().lock().lines() {
                let line = line.unwrap_or_else(|e| fail(e));
                if let Err(e) = l.say(&line) {
                    eprintln!("listener: {e}");
                }
            }
            l.wait_idle();
            if !serving {
                exit(0);
            }
        });
        if args.serve.is_none() {
            let _ = reader.join();
        }
    }
    if let Some(port) = args.serve {
        serve(listener, &args.host, port);
    } else if !args.interactive {
        let mut input = String::new();
        std::io::stdin()
            .read_to_string(&mut input)
            .unwrap_or_else(|e| fail(e));
        listener.say(&input).unwrap_or_else(|e| fail(e));
        listener.wait_idle();
    }
}

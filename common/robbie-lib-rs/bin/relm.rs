//! relm: RELM on stdin (or over HTTP) to IRELM. Port of robbie-lib-py/relm/cli.py.

use std::io::{BufRead, Read, Write};
use std::process::exit;
use std::sync::Arc;

use axum::{extract::State, http::StatusCode, routing::post, Router};
use clap::Parser;
use robbie_lib::relm::{Converter, Options, Table};

#[derive(Parser)]
#[command(name = "relm", about = "Convert RELM (LLM output) to IRELM.")]
struct Args {
    /// the RELM to IRELM table (YAML)
    #[arg(long)]
    table: String,
    /// refuse bad RELM, otherwise best effort
    #[arg(long)]
    strict: bool,
    /// emit IRELM without nesting
    #[arg(long)]
    stateless: bool,
    /// one RELM message per stdin line
    #[arg(long)]
    interactive: bool,
    /// locale for AS (default: $LOCALE, then en_GB)
    #[arg(long)]
    locale: Option<String>,
    /// serve POST / on 127.0.0.1:PORT
    #[arg(long, value_name = "PORT")]
    serve: Option<u16>,
}

fn fail(message: impl std::fmt::Display) -> ! {
    eprintln!("relm: {message}");
    exit(1);
}

type Reply = (StatusCode, [(&'static str, &'static str); 1], String);

async fn handle(State(converter): State<Arc<Converter>>, body: String) -> Reply {
    match converter.convert(&body) {
        Ok(irelm) => (
            StatusCode::OK,
            [("content-type", "application/xml; charset=utf-8")],
            irelm,
        ),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            [("content-type", "text/plain; charset=utf-8")],
            e.to_string(),
        ),
    }
}

fn serve(converter: Converter, port: u16) {
    let runtime = tokio::runtime::Runtime::new().unwrap_or_else(|e| fail(e));
    runtime.block_on(async {
        let app = Router::new()
            .route("/", post(handle))
            .with_state(Arc::new(converter));
        let listener = tokio::net::TcpListener::bind(("127.0.0.1", port))
            .await
            .unwrap_or_else(|e| fail(e));
        eprintln!("relm: serving on http://127.0.0.1:{port}/");
        axum::serve(listener, app).await.unwrap_or_else(|e| fail(e));
    });
}

fn main() {
    let args = Args::parse();
    let locale = args
        .locale
        .or_else(|| std::env::var("LOCALE").ok().filter(|l| !l.is_empty()))
        .unwrap_or_else(|| "en_GB".into());
    let options = Options {
        stateless: args.stateless,
        strict: args.strict,
        locale,
    };
    let table = Table::load(&args.table).unwrap_or_else(|e| fail(e));
    let converter = Converter::new(table, options);

    if let Some(port) = args.serve {
        serve(converter, port);
    } else if args.interactive {
        let mut stdout = std::io::stdout();
        for line in std::io::stdin().lock().lines() {
            let line = line.unwrap_or_else(|e| fail(e));
            match converter.convert(line.trim_end_matches(['\r', '\n'])) {
                Ok(irelm) => {
                    let _ = writeln!(stdout, "{irelm}");
                    let _ = stdout.flush();
                }
                Err(e) => eprintln!("relm: {e}"),
            }
        }
    } else {
        let mut input = String::new();
        std::io::stdin()
            .read_to_string(&mut input)
            .unwrap_or_else(|e| fail(e));
        println!("{}", converter.convert(&input).unwrap_or_else(|e| fail(e)));
    }
}

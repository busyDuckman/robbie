//! Runs the shared cases in robbie-lib-test/relm, which the Python library runs too.

use std::path::{Path, PathBuf};

use robbie_lib::relm::{say_as, Converter, Options, RelmError, Table};
use serde::Deserialize;

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn data() -> PathBuf {
    repo().join("common/robbie-lib-test/relm")
}

#[derive(Deserialize)]
struct Cases<T> {
    cases: Vec<T>,
}

fn cases<T: for<'de> Deserialize<'de>>(name: &str) -> Vec<T> {
    let text = std::fs::read_to_string(data().join(name)).expect("read cases");
    serde_json::from_str::<Cases<T>>(&text)
        .expect("parse cases")
        .cases
}

/// Compare a result with the expected output or error kind. Returns a failure line, if any.
fn check(
    id: &str,
    got: Result<String, RelmError>,
    output: &Option<String>,
    error: &Option<String>,
) -> Option<String> {
    match (got, output, error) {
        (Ok(got), Some(want), _) if got == *want => None,
        (Err(e), _, Some(kind)) if e.kind.as_ref() == kind => None,
        (got, _, _) => Some(format!(
            "{id}\n    want: {:?}\n    got:  {got:?}",
            output.as_ref().or(error.as_ref())
        )),
    }
}

fn report(failures: Vec<String>, total: usize) {
    assert!(
        failures.is_empty(),
        "{} of {total} cases failed:\n{}",
        failures.len(),
        failures.join("\n")
    );
}

#[derive(Deserialize)]
struct ConvertCase {
    name: String,
    #[serde(default)]
    input: String,
    inputs: Option<Vec<String>>,
    outputs: Option<Vec<String>>,
    #[serde(default)]
    options: Options,
    table: Option<String>,
    table_yaml: Option<String>,
    output: Option<String>,
    error: Option<String>,
}

#[test]
fn convert_cases() {
    let all: Vec<ConvertCase> = cases("convert_cases.json");
    let failures = all
        .iter()
        .filter_map(|c| {
            let table = match &c.table_yaml {
                Some(yaml) => Table::parse(yaml),
                None => {
                    Table::load(data().join(c.table.as_deref().unwrap_or("example_table.yaml")))
                }
            }
            .expect("table loads");
            let converter = Converter::new(table, c.options.clone());
            if let (Some(inputs), Some(outputs)) = (&c.inputs, &c.outputs) {
                let got: Result<Vec<String>, RelmError> =
                    inputs.iter().map(|i| converter.convert(i)).collect();
                return match got {
                    Ok(got) if got == *outputs => None,
                    got => Some(format!(
                        "{}\n    want: {outputs:?}\n    got:  {got:?}",
                        c.name
                    )),
                };
            }
            check(&c.name, converter.convert(&c.input), &c.output, &c.error)
        })
        .collect();
    report(failures, all.len());
}

#[derive(Deserialize)]
struct TableCase {
    name: String,
    file: Option<String>,
    yaml: Option<String>,
    ok: bool,
    names: Option<Vec<String>>,
}

#[test]
fn table_cases() {
    let all: Vec<TableCase> = cases("table_cases.json");
    let failures = all
        .iter()
        .filter_map(|c| {
            let loaded = match &c.file {
                Some(file) => Table::load(repo().join(file)),
                None => Table::parse(c.yaml.as_deref().unwrap_or("")),
            };
            match (&loaded, c.ok) {
                (Ok(t), true) if c.names.as_ref().is_none_or(|n| t.names() == *n) => None,
                (Err(e), false) if e.kind.as_ref() == "bad_table" => None,
                _ => Some(format!("{}\n    ok: {}\n    got: {loaded:?}", c.name, c.ok)),
            }
        })
        .collect();
    report(failures, all.len());
}

#[derive(Deserialize)]
struct SayAsCase {
    format: String,
    locale: String,
    input: String,
    output: Option<String>,
    error: Option<String>,
}

#[test]
fn say_as_cases() {
    let all: Vec<SayAsCase> = cases("say_as_cases.json");
    let failures = all
        .iter()
        .filter_map(|c| {
            let id = format!("{} {} {:?}", c.format, c.locale, c.input);
            check(
                &id,
                say_as::expand(&c.input, &c.format, &c.locale),
                &c.output,
                &c.error,
            )
        })
        .collect();
    report(failures, all.len());
}

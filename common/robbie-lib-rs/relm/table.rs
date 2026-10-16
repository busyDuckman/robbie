//! IRELM commands and the RELM to IRELM table (YAML: macro name -> IRELM string).
//! Port of robbie-lib-py/relm/table.py, keep the two the same.

use std::collections::HashSet;
use std::path::Path;

use super::markup::{
    escape_attr, is_number, number, scan, strip_ws, ErrorKind, RelmError, Tag, Token,
};

pub const SPANS: [&str; 4] = ["VAD", "PROSODY", "VOICE", "AS"];
pub const AS_FORMATS: [&str; 6] = [
    "datetime",
    "number",
    "digits",
    "characters",
    "unit",
    "currency",
];

/// The params of a command, in canonical (alias) form. None for an unknown command.
pub fn params(cmd: &str) -> Option<&'static [&'static str]> {
    Some(match cmd {
        "VAD" => &["v", "a", "d"],
        "PROSODY" => &["p", "s", "r", "v"],
        "VOICE" => &["voice", "locale"],
        "AS" => &["format", "locale"],
        "MESSAGE" => &["sub", "action"],
        "BEEP" => &["melody"],
        "AUDIO" => &["file_name"],
        "PAUSE" => &["duration"],
        _ => return None,
    })
}

fn alias(cmd: &str, key: &str) -> String {
    let canonical = match (cmd, key) {
        ("VAD", "valence") => "v",
        ("VAD", "arousal") => "a",
        ("VAD", "dominance") => "d",
        ("PROSODY", "pitch") => "p",
        ("PROSODY", "speed") => "s",
        ("PROSODY", "range") => "r",
        ("PROSODY", "volume") => "v",
        _ => key,
    };
    canonical.to_string()
}

fn required(cmd: &str) -> &'static [&'static str] {
    match cmd {
        "AS" => &["format"],
        "MESSAGE" => &["sub", "action"],
        "BEEP" => &["melody"],
        "AUDIO" => &["file_name"],
        "PAUSE" => &["duration"],
        _ => &[],
    }
}

fn bad_table(message: impl Into<String>) -> RelmError {
    RelmError::new(ErrorKind::BadTable, message)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Command {
    pub name: String,
    pub attrs: Vec<(String, String)>, // canonical keys, table order
}

impl Command {
    pub fn is_span(&self) -> bool {
        SPANS.contains(&self.name.as_str())
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        self.attrs
            .iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v.as_str())
    }

    pub fn xml(&self, self_closing: bool) -> String {
        tag_xml(&self.name, &self.attrs, self_closing)
    }
}

pub(crate) fn tag_xml(name: &str, attrs: &[(String, String)], self_closing: bool) -> String {
    let attrs: String = attrs
        .iter()
        .map(|(k, v)| format!(" {k}=\"{}\"", escape_attr(v)))
        .collect();
    format!("<{name}{attrs}{}>", if self_closing { "/" } else { "" })
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Macro {
    pub name: String,
    pub open: Vec<Command>,
    /// From the "/name" entry.
    pub close: Vec<Command>,
}

impl Macro {
    pub fn spans(&self) -> impl DoubleEndedIterator<Item = &Command> {
        self.open.iter().filter(|c| c.is_span())
    }

    /// Nothing to undo, so the macro is never pushed on the stack.
    pub fn instant(&self) -> bool {
        self.spans().next().is_none() && self.close.is_empty()
    }
}

/// Returns an error message, or None if the BEEP melody is valid.
pub fn check_melody(melody: &str) -> Option<String> {
    let notes: Vec<&str> = melody
        .split(';')
        .map(strip_ws)
        .filter(|n| !n.is_empty())
        .collect();
    if notes.is_empty() {
        return Some("melody is empty".into());
    }
    for item in notes {
        let parts: Vec<&str> = item.split(',').map(strip_ws).collect();
        if parts.len() != 2 {
            return Some(format!("\"{item}\" is not NOTE,DURATION"));
        }
        let (note, duration) = (parts[0], parts[1]);
        let c: Vec<char> = note.chars().collect();
        let ok = note == "R"
            || ((2..=3).contains(&c.len())
                && "ABCDEFG".contains(c[0])
                && "012345678".contains(c[c.len() - 1])
                && (c.len() == 2 || "#b".contains(c[1])));
        if !ok {
            return Some(format!("\"{note}\" is not a note (e.g. C4, C#4, Eb4 or R)"));
        }
        if !is_number(duration) || number(duration) <= 0.0 {
            return Some(format!("\"{duration}\" is not a duration in seconds"));
        }
    }
    None
}

fn check_value(cmd: &str, key: &str, value: &str) -> Option<String> {
    match cmd {
        "VAD" => (value != "none" && !(is_number(value) && (1.0..=5.0).contains(&number(value))))
            .then(|| format!("{key}=\"{value}\" must be 1 to 5 or \"none\"")),
        "PROSODY" => (value != "none" && !(is_number(value) && number(value) > 0.0))
            .then(|| format!("{key}=\"{value}\" must be a multiplier above 0 or \"none\"")),
        "PAUSE" => (!(is_number(value) && number(value) >= 0.0))
            .then(|| format!("duration=\"{value}\" must be seconds")),
        "BEEP" => check_melody(value),
        "AS" if key == "format" => (!AS_FORMATS.contains(&value))
            .then(|| format!("format=\"{value}\" must be one of {}", AS_FORMATS.join("|"))),
        "AUDIO" | "VOICE" | "AS" if strip_ws(value).is_empty() => Some(format!("{key} is empty")),
        _ => None,
    }
}

/// Validate a tag as an IRELM command.
pub fn command_from_tag(tag: &Tag) -> Result<Command, RelmError> {
    let name = tag.name.as_str();
    if tag.closing {
        return Err(bad_table(format!(
            "</{name}> is not allowed, the stack closes spans"
        )));
    }
    let Some(allowed) = params(name) else {
        return Err(bad_table(format!("unknown command <{name}>")));
    };
    let span = SPANS.contains(&name);
    if span && tag.self_closing {
        return Err(bad_table(format!(
            "<{name}> is a span, write it as an open tag"
        )));
    }
    if !span && !tag.self_closing {
        return Err(bad_table(format!(
            "<{name}> must be self-closing, e.g. <{name} .../>"
        )));
    }
    let mut attrs: Vec<(String, String)> = Vec::new();
    for (key, value) in &tag.attrs {
        let key = alias(name, key);
        if !allowed.contains(&key.as_str()) {
            return Err(bad_table(format!("<{name}> has no param {key}")));
        }
        if attrs.iter().any(|(k, _)| *k == key) {
            return Err(bad_table(format!("<{name}> has {key} twice")));
        }
        if let Some(problem) = check_value(name, &key, value) {
            return Err(bad_table(format!("<{name}> {problem}")));
        }
        attrs.push((key, value.clone()));
    }
    for key in required(name) {
        if !attrs.iter().any(|(k, _)| k == key) {
            return Err(bad_table(format!("<{name}> needs {key}")));
        }
    }
    Ok(Command {
        name: name.to_string(),
        attrs,
    })
}

fn is_macro_name(name: &str) -> bool {
    let mut chars = name.chars();
    matches!(chars.next(), Some(c) if c.is_ascii_alphabetic() || c == '_')
        && chars.all(|c| c.is_ascii_alphanumeric() || "_-.:".contains(c))
}

fn parse_entry(name: &str, value: &str, is_close: bool) -> Result<Vec<Command>, RelmError> {
    let mut commands = Vec::new();
    let mut kinds = HashSet::new();
    for item in scan(value) {
        let tag = match item {
            Token::Text(text) => {
                if !strip_ws(&text).is_empty() {
                    return Err(bad_table(format!(
                        "{name}: text \"{}\" is not allowed",
                        strip_ws(&text)
                    )));
                }
                continue;
            }
            Token::Bad(snippet) => {
                return Err(bad_table(format!("{name}: malformed tag {snippet}")))
            }
            Token::Tag(tag) => tag,
        };
        let cmd =
            command_from_tag(&tag).map_err(|e| bad_table(format!("{name}: {}", e.message)))?;
        if cmd.is_span() {
            if is_close {
                return Err(bad_table(format!(
                    "/{name}: may only hold self-closing commands"
                )));
            }
            if !kinds.insert(cmd.name.clone()) {
                return Err(bad_table(format!("{name}: <{}> appears twice", cmd.name)));
            }
        }
        commands.push(cmd);
    }
    if commands.is_empty() {
        return Err(bad_table(format!("{name}: no IRELM commands")));
    }
    Ok(commands)
}

/// The RELM to IRELM table. Each entry maps a macro name to IRELM commands; an entry
/// named "/name" holds the commands sent when that macro closes.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Table {
    pub macros: Vec<Macro>, // table order
}

impl Table {
    /// Build from (name, IRELM) entries in table order.
    pub fn from_entries<'a>(
        entries: impl IntoIterator<Item = (&'a str, &'a str)>,
    ) -> Result<Self, RelmError> {
        let mut table = Table::default();
        let mut closes: Vec<(String, Vec<Command>)> = Vec::new();
        for (name, value) in entries {
            let (is_close, base) = match name.strip_prefix('/') {
                Some(base) => (true, base),
                None => (false, name),
            };
            if !is_macro_name(base) {
                return Err(bad_table(format!("\"{name}\" is not a valid macro name")));
            }
            let commands = parse_entry(base, value, is_close)?;
            if is_close {
                closes.retain(|(n, _)| n != base);
                closes.push((base.to_string(), commands));
            } else if let Some(m) = table.macros.iter_mut().find(|m| m.name == base) {
                m.open = commands;
            } else {
                table.macros.push(Macro {
                    name: base.to_string(),
                    open: commands,
                    close: Vec::new(),
                });
            }
        }
        for (base, commands) in closes {
            let Some(m) = table.macros.iter_mut().find(|m| m.name == base) else {
                return Err(bad_table(format!("/{base} has no {base} entry")));
            };
            m.close = commands;
        }
        Ok(table)
    }

    pub fn parse(text: &str) -> Result<Self, RelmError> {
        let doc: serde_yaml_ng::Value =
            serde_yaml_ng::from_str(text).map_err(|e| bad_table(format!("not valid YAML: {e}")))?;
        let mapping = match doc {
            serde_yaml_ng::Value::Null => return Ok(Table::default()),
            serde_yaml_ng::Value::Mapping(m) => m,
            _ => return Err(bad_table("the table must be a YAML mapping of name: IRELM")),
        };
        let mut entries = Vec::new();
        for (key, value) in &mapping {
            match (key.as_str(), value.as_str()) {
                (Some(k), Some(v)) => entries.push((k, v)),
                _ => {
                    return Err(bad_table(format!(
                        "{key:?}: entries must map a name to an IRELM string"
                    )))
                }
            }
        }
        Self::from_entries(entries)
    }

    pub fn load(path: impl AsRef<Path>) -> Result<Self, RelmError> {
        let path = path.as_ref();
        let text = std::fs::read_to_string(path)
            .map_err(|e| bad_table(format!("cannot read {}: {e}", path.display())))?;
        Self::parse(&text)
    }

    /// The named expressions, for telling the LLM what it can use.
    pub fn names(&self) -> Vec<&str> {
        self.macros.iter().map(|m| m.name.as_str()).collect()
    }

    /// Exact match, or in best effort mode the first case-insensitive match.
    pub fn lookup(&self, name: &str, strict: bool) -> Option<&Macro> {
        if let Some(m) = self.macros.iter().find(|m| m.name == name) {
            return Some(m);
        }
        if strict {
            return None;
        }
        let lower = name.to_lowercase();
        self.macros.iter().find(|m| m.name.to_lowercase() == lower)
    }
}

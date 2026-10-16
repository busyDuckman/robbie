//! RELM (what the LLM writes) to IRELM, in stack or stateless mode.
//! Port of robbie-lib-py/relm/convert.py, keep the two the same.

use serde::Deserialize;

use super::markup::{
    decode_entities, escape_text, scan, strip_ws, ErrorKind, RelmError, Tag, Token, WS,
};
use super::say_as;
use super::table::{params, tag_xml, Command, Macro, Table};

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Options {
    pub stateless: bool,
    pub strict: bool,
    pub locale: String,
    pub prosody_to_ssml: bool,
    pub voice_to_ssml: bool,
    pub pause_to_ssml: bool,
    pub message_to_ssml: bool,
    pub audio_to_ssml: bool,
    pub as_to_ssml: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            stateless: false,
            strict: false,
            locale: "en_GB".into(),
            prosody_to_ssml: false,
            voice_to_ssml: false,
            pause_to_ssml: false,
            message_to_ssml: false,
            audio_to_ssml: false,
            as_to_ssml: false,
        }
    }
}

impl Options {
    pub fn check(&self) -> Result<(), RelmError> {
        let spans = [
            ("prosody_to_ssml", self.prosody_to_ssml),
            ("voice_to_ssml", self.voice_to_ssml),
            ("as_to_ssml", self.as_to_ssml),
        ];
        if let Some((flag, _)) = spans.iter().find(|(_, on)| *on).filter(|_| self.stateless) {
            return Err(RelmError::new(
                ErrorKind::BadOption,
                format!("--stateless cannot be used with --{flag}, SSML spans must nest"),
            ));
        }
        Ok(())
    }
}

fn percent(multiplier: &str) -> String {
    let x = (multiplier.parse::<f64>().unwrap_or(1.0) - 1.0) * 100.0;
    let n = (x.abs() + 0.5).floor() as i64;
    format!("{}{n}%", if x < 0.0 && n != 0 { "-" } else { "+" })
}

fn attrs(items: &[(&str, String)]) -> Vec<(String, String)> {
    items
        .iter()
        .map(|(k, v)| (k.to_string(), v.clone()))
        .collect()
}

fn ssml_say_as(format: &str) -> &'static str {
    match format {
        "datetime" => "date",
        "number" => "cardinal",
        "digits" => "digits",
        "characters" => "characters",
        "unit" => "unit",
        _ => "currency",
    }
}

pub struct Converter {
    table: Table,
    options: Options,
}

impl Converter {
    pub fn new(table: Table, options: Options) -> Result<Self, RelmError> {
        options.check()?;
        Ok(Self { table, options })
    }

    pub fn table(&self) -> &Table {
        &self.table
    }

    /// Convert one LLM reply.
    pub fn convert(&self, relm: &str) -> Result<String, RelmError> {
        Run {
            table: &self.table,
            opt: &self.options,
            stack: Vec::new(),
            out: String::new(),
        }
        .run(relm)
    }
}

pub fn convert(table: &Table, relm: &str, options: &Options) -> Result<String, RelmError> {
    options.check()?;
    Run {
        table,
        opt: options,
        stack: Vec::new(),
        out: String::new(),
    }
    .run(relm)
}

struct Run<'a> {
    table: &'a Table,
    opt: &'a Options,
    stack: Vec<&'a Macro>,
    out: String,
}

impl<'a> Run<'a> {
    fn run(mut self, relm: &str) -> Result<String, RelmError> {
        for item in scan(relm) {
            match item {
                Token::Text(text) => self.text(&decode_entities(&text))?,
                Token::Bad(snippet) => {
                    if self.opt.strict {
                        return Err(RelmError::new(
                            ErrorKind::BadTag,
                            format!("malformed tag {snippet}"),
                        ));
                    }
                }
                Token::Tag(tag) if tag.closing => self.close(&tag)?,
                Token::Tag(tag) => self.open(&tag)?,
            }
        }
        if let Some(top) = self.stack.last().filter(|_| self.opt.strict) {
            return Err(RelmError::new(
                ErrorKind::UnclosedTag,
                format!("<{}> is never closed", top.name),
            ));
        }
        while !self.stack.is_empty() {
            self.pop();
        }
        Ok(format!("<IRELM>{}</IRELM>", self.out))
    }

    // --- RELM events

    fn text(&mut self, text: &str) -> Result<(), RelmError> {
        let as_cmd = if self.opt.as_to_ssml {
            None
        } else {
            self.stack
                .iter()
                .rev()
                .flat_map(|m| m.spans().rev())
                .find(|c| c.name == "AS")
        };
        let body = strip_ws(text);
        if let (Some(cmd), false) = (as_cmd, body.is_empty()) {
            let locale = cmd.get("locale").unwrap_or(&self.opt.locale);
            match say_as::expand(body, cmd.get("format").unwrap_or(""), locale) {
                Ok(expanded) => {
                    let start = text.len() - text.trim_start_matches(WS).len();
                    let text = format!(
                        "{}{}{}",
                        &text[..start],
                        expanded,
                        &text[start + body.len()..]
                    );
                    self.out.push_str(&escape_text(&text));
                    return Ok(());
                }
                Err(e) if self.opt.strict => return Err(e),
                Err(_) => {}
            }
        }
        self.out.push_str(&escape_text(text));
        Ok(())
    }

    fn open(&mut self, tag: &Tag) -> Result<(), RelmError> {
        let Some(m) = self.table.lookup(&tag.name, self.opt.strict) else {
            if self.opt.strict {
                return Err(RelmError::new(
                    ErrorKind::UnknownTag,
                    format!("<{}> is not in the table", tag.name),
                ));
            }
            return Ok(());
        };
        if !tag.attrs.is_empty() && self.opt.strict {
            return Err(RelmError::new(
                ErrorKind::BadTag,
                format!("<{}> takes no params", tag.name),
            ));
        }
        if !m.instant() {
            self.stack.push(m);
        }
        for cmd in &m.open {
            self.emit_open(cmd);
        }
        if tag.self_closing && !m.instant() {
            self.pop();
        }
        Ok(())
    }

    fn close(&mut self, tag: &Tag) -> Result<(), RelmError> {
        let Some(m) = self.table.lookup(&tag.name, self.opt.strict) else {
            if self.opt.strict {
                return Err(RelmError::new(
                    ErrorKind::UnknownTag,
                    format!("</{}> is not in the table", tag.name),
                ));
            }
            return Ok(());
        };
        if m.instant() {
            return Ok(());
        }
        let Some(depth) = self.stack.iter().rposition(|s| std::ptr::eq(*s, m)) else {
            if self.opt.strict {
                return Err(RelmError::new(
                    ErrorKind::UnexpectedClose,
                    format!("</{}> was never opened", tag.name),
                ));
            }
            return Ok(());
        };
        if depth != self.stack.len() - 1 && self.opt.strict {
            let top = &self.stack[self.stack.len() - 1].name;
            return Err(RelmError::new(
                ErrorKind::MismatchedClose,
                format!("</{}> closes before </{top}>", tag.name),
            ));
        }
        while self.stack.len() > depth {
            self.pop();
        }
        Ok(())
    }

    fn pop(&mut self) {
        let Some(m) = self.stack.pop() else { return };
        for cmd in m.spans().rev() {
            self.emit_close(cmd);
        }
        for cmd in &m.close {
            self.emit_open(cmd);
        }
    }

    // --- output

    fn state(&self, kind: &str) -> String {
        let keys = params(kind).unwrap_or(&[]);
        let mut values: Vec<(String, String)> = keys
            .iter()
            .map(|k| (k.to_string(), "none".to_string()))
            .collect();
        for cmd in self
            .stack
            .iter()
            .flat_map(|m| m.spans())
            .filter(|c| c.name == kind)
        {
            for (k, v) in cmd.attrs.iter().filter(|(_, v)| v != "none") {
                if let Some(slot) = values.iter_mut().find(|(key, _)| key == k) {
                    slot.1 = v.clone();
                }
            }
        }
        tag_xml(kind, &values, true)
    }

    fn emit_open(&mut self, cmd: &Command) {
        let o = self.opt;
        let get = |k: &str| cmd.get(k).unwrap_or("").to_string();
        let xml = match cmd.name.as_str() {
            "AS" if o.as_to_ssml => tag_xml(
                "say-as",
                &attrs(&[("interpret-as", ssml_say_as(&get("format")).into())]),
                false,
            ),
            "AS" => return,
            _ if cmd.is_span() && o.stateless => self.state(&cmd.name),
            "PROSODY" if o.prosody_to_ssml => {
                let items: Vec<(String, String)> = cmd
                    .attrs
                    .iter()
                    .filter(|(_, v)| v != "none")
                    .map(|(k, v)| {
                        let name = match k.as_str() {
                            "p" => "pitch",
                            "s" => "rate",
                            "r" => "range",
                            _ => "volume",
                        };
                        (name.to_string(), percent(v))
                    })
                    .collect();
                tag_xml("prosody", &items, false)
            }
            "VOICE" if o.voice_to_ssml => {
                let items: Vec<(String, String)> = cmd
                    .attrs
                    .iter()
                    .filter(|(_, v)| v != "none")
                    .map(|(k, v)| match k.as_str() {
                        "locale" => ("xml:lang".to_string(), v.replace('_', "-")),
                        _ => ("name".to_string(), v.clone()),
                    })
                    .collect();
                tag_xml("voice", &items, false)
            }
            "PAUSE" if o.pause_to_ssml => tag_xml(
                "break",
                &attrs(&[("time", format!("{}s", get("duration")))]),
                true,
            ),
            "MESSAGE" if o.message_to_ssml => tag_xml(
                "mark",
                &attrs(&[("name", format!("{}:{}", get("sub"), get("action")))]),
                true,
            ),
            "AUDIO" if o.audio_to_ssml => {
                tag_xml("audio", &attrs(&[("src", get("file_name"))]), true)
            }
            _ => cmd.xml(!cmd.is_span()),
        };
        self.out.push_str(&xml);
    }

    fn emit_close(&mut self, cmd: &Command) {
        let o = self.opt;
        let xml = match cmd.name.as_str() {
            "AS" if o.as_to_ssml => "</say-as>".to_string(),
            "AS" => return,
            _ if o.stateless => self.state(&cmd.name),
            "PROSODY" if o.prosody_to_ssml => "</prosody>".to_string(),
            "VOICE" if o.voice_to_ssml => "</voice>".to_string(),
            name => format!("</{name}>"),
        };
        self.out.push_str(&xml);
    }
}

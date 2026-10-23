//! RELM (what the LLM writes) to IRELM, in stack or stateless mode.
//! Port of robbie-lib-py/relm/convert.py, keep the two the same.

use std::sync::atomic::{AtomicU64, Ordering};

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
}

impl Default for Options {
    fn default() -> Self {
        Self {
            stateless: false,
            strict: false,
            locale: "en_GB".into(),
        }
    }
}

pub struct Converter {
    table: Table,
    options: Options,
    ids: AtomicU64, // MESSAGE ids, unique for the life of the converter
}

impl Converter {
    pub fn new(table: Table, options: Options) -> Self {
        Self {
            table,
            options,
            ids: AtomicU64::new(1),
        }
    }

    pub fn table(&self) -> &Table {
        &self.table
    }

    /// Convert one LLM reply.
    pub fn convert(&self, relm: &str) -> Result<String, RelmError> {
        Run {
            table: &self.table,
            opt: &self.options,
            ids: &self.ids,
            stack: Vec::new(),
            out: String::new(),
        }
        .run(relm)
    }
}

/// Convert one reply with a fresh converter, so MESSAGE ids start at 1.
pub fn convert(table: &Table, relm: &str, options: &Options) -> Result<String, RelmError> {
    Run {
        table,
        opt: options,
        ids: &AtomicU64::new(1),
        stack: Vec::new(),
        out: String::new(),
    }
    .run(relm)
}

/// A macro on the stack, with the ids its messages were sent with.
struct Open<'a> {
    macro_: &'a Macro,
    ids: Vec<u64>,
}

struct Run<'a> {
    table: &'a Table,
    opt: &'a Options,
    ids: &'a AtomicU64,
    stack: Vec<Open<'a>>,
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
                format!("<{}> is never closed", top.macro_.name),
            ));
        }
        while !self.stack.is_empty() {
            self.pop();
        }
        if self.opt.stateless {
            return Ok(self.out);
        }
        Ok(format!("<IRELM>{}</IRELM>", self.out))
    }

    // --- RELM events

    fn text(&mut self, text: &str) -> Result<(), RelmError> {
        let as_cmd = self
            .stack
            .iter()
            .rev()
            .flat_map(|o| o.macro_.spans().rev())
            .find(|c| c.name == "AS");
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
        // A macro with a "/name" entry gives each MESSAGE an id, its closes reuse them in order.
        let ids: Vec<u64> = match m.paired() {
            true => m
                .open
                .iter()
                .filter(|c| c.name == "MESSAGE")
                .map(|_| self.ids.fetch_add(1, Ordering::Relaxed))
                .collect(),
            false => Vec::new(),
        };
        if !m.instant() {
            self.stack.push(Open {
                macro_: m,
                ids: ids.clone(),
            });
        }
        let mut sent = ids.into_iter();
        for cmd in &m.open {
            self.emit_open(cmd, &mut sent, false);
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
        let Some(depth) = self.stack.iter().rposition(|s| std::ptr::eq(s.macro_, m)) else {
            if self.opt.strict {
                return Err(RelmError::new(
                    ErrorKind::UnexpectedClose,
                    format!("</{}> was never opened", tag.name),
                ));
            }
            return Ok(());
        };
        if depth != self.stack.len() - 1 && self.opt.strict {
            let top = &self.stack[self.stack.len() - 1].macro_.name;
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
        let Some(top) = self.stack.pop() else { return };
        for cmd in top.macro_.spans().rev() {
            self.emit_close(cmd);
        }
        let mut ids = top.ids.into_iter();
        for cmd in &top.macro_.close {
            self.emit_open(cmd, &mut ids, true);
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
            .flat_map(|o| o.macro_.spans())
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

    /// ids: the ids for this macro's messages, taken in order (none if it has no "/name").
    fn emit_open(&mut self, cmd: &Command, ids: &mut impl Iterator<Item = u64>, closing: bool) {
        let xml = match cmd.name.as_str() {
            "AS" => return, // expanded here, never sent
            _ if cmd.is_span() && self.opt.stateless => self.state(&cmd.name),
            "MESSAGE" => match ids.next() {
                Some(id) => {
                    let mut extra = vec![("id".to_string(), id.to_string())];
                    if closing {
                        extra.push(("close".to_string(), "true".to_string()));
                    }
                    cmd.xml_with(true, &extra)
                }
                None => cmd.xml(true),
            },
            _ => cmd.xml(!cmd.is_span()),
        };
        self.out.push_str(&xml);
    }

    fn emit_close(&mut self, cmd: &Command) {
        let xml = match cmd.name.as_str() {
            "AS" => return,
            _ if self.opt.stateless => self.state(&cmd.name),
            name => format!("</{name}>"),
        };
        self.out.push_str(&xml);
    }
}

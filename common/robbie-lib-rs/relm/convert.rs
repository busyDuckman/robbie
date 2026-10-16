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
}

impl Converter {
    pub fn new(table: Table, options: Options) -> Self {
        Self { table, options }
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
        let as_cmd = self
            .stack
            .iter()
            .rev()
            .flat_map(|m| m.spans().rev())
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
        let xml = match cmd.name.as_str() {
            "AS" => return, // expanded here, never sent
            _ if cmd.is_span() && self.opt.stateless => self.state(&cmd.name),
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

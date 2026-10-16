//! Hand written tag scanner shared by the table and RELM parsers, plus XML escaping.
//!
//! RELM comes from an LLM, so it is not parsed as XML: anything that does not look like a
//! tag is kept as text. Port of robbie-lib-py/relm/markup.py, keep the two the same.

use strum_macros::{AsRefStr, Display, EnumString};

pub const WS: [char; 4] = [' ', '\t', '\n', '\r'];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Display, AsRefStr, EnumString)]
#[strum(serialize_all = "snake_case")]
pub enum ErrorKind {
    BadTable,
    BadTag,
    UnknownTag,
    UnexpectedClose,
    MismatchedClose,
    UnclosedTag,
    BadAs,
}

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{kind}: {message}")]
pub struct RelmError {
    pub kind: ErrorKind,
    pub message: String,
}

impl RelmError {
    pub fn new(kind: ErrorKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Tag {
    pub name: String,
    pub attrs: Vec<(String, String)>, // values decoded
    pub closing: bool,
    pub self_closing: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Token {
    /// Raw text, entities not yet decoded.
    Text(String),
    Tag(Tag),
    /// A '<' that starts like a tag but is not one. The '<' itself is kept as text.
    Bad(String),
}

fn is_name_start(c: char) -> bool {
    c.is_ascii_alphabetic() || c == '_'
}

fn is_name_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || "_-.:".contains(c)
}

pub fn strip_ws(s: &str) -> &str {
    s.trim_matches(WS)
}

fn skip_ws(s: &[char], mut i: usize) -> usize {
    while i < s.len() && WS.contains(&s[i]) {
        i += 1;
    }
    i
}

fn read_name(s: &[char], i: usize) -> (String, usize) {
    if i >= s.len() || !is_name_start(s[i]) {
        return (String::new(), i);
    }
    let mut j = i + 1;
    while j < s.len() && is_name_char(s[j]) {
        j += 1;
    }
    (s[i..j].iter().collect(), j)
}

/// Parse a tag starting at s[i] == '<'. Returns the tag and the index after it.
fn parse_tag(s: &[char], i: usize) -> Option<(Tag, usize)> {
    let n = s.len();
    let mut j = skip_ws(s, i + 1);
    let mut closing = false;
    if j < n && s[j] == '/' {
        closing = true;
        j = skip_ws(s, j + 1);
    }
    let (name, after) = read_name(s, j);
    if name.is_empty() {
        return None;
    }
    j = after;
    let mut attrs = Vec::new();
    loop {
        let mut k = skip_ws(s, j);
        if k >= n {
            return None;
        }
        match s[k] {
            '>' => {
                if closing && !attrs.is_empty() {
                    return None;
                }
                return Some((
                    Tag {
                        name,
                        attrs,
                        closing,
                        self_closing: false,
                    },
                    k + 1,
                ));
            }
            '/' => {
                let k2 = skip_ws(s, k + 1);
                if k2 < n && s[k2] == '>' && !closing {
                    return Some((
                        Tag {
                            name,
                            attrs,
                            closing: false,
                            self_closing: true,
                        },
                        k2 + 1,
                    ));
                }
                return None;
            }
            _ => {}
        }
        if k == j {
            return None; // attributes must be separated by whitespace
        }
        let (key, after) = read_name(s, k);
        if key.is_empty() {
            return None;
        }
        k = skip_ws(s, after);
        if k >= n || s[k] != '=' {
            return None;
        }
        k = skip_ws(s, k + 1);
        if k >= n || (s[k] != '"' && s[k] != '\'') {
            return None;
        }
        let quote = s[k];
        let end = (k + 1..n).find(|&e| s[e] == quote)?;
        let value: String = s[k + 1..end].iter().collect();
        if value.contains('<') {
            return None;
        }
        attrs.push((key, decode_entities(&value)));
        j = end + 1;
    }
}

/// Split s into raw text, tags and bad tags.
pub fn scan(text: &str) -> Vec<Token> {
    let s: Vec<char> = text.chars().collect();
    let n = s.len();
    let mut items = Vec::new();
    let mut buf = String::new();
    let mut i = 0;
    while i < n {
        if s[i] == '<' {
            if let Some((tag, end)) = parse_tag(&s, i) {
                if !buf.is_empty() {
                    items.push(Token::Text(std::mem::take(&mut buf)));
                }
                items.push(Token::Tag(tag));
                i = end;
                continue;
            }
            if i + 1 < n && (is_name_start(s[i + 1]) || s[i + 1] == '/') {
                if !buf.is_empty() {
                    items.push(Token::Text(std::mem::take(&mut buf)));
                }
                items.push(Token::Bad(s[i..n.min(i + 20)].iter().collect()));
            }
        }
        buf.push(s[i]);
        i += 1;
    }
    if !buf.is_empty() {
        items.push(Token::Text(buf));
    }
    items
}

fn codepoint(ent: &str) -> Option<char> {
    let (digits, radix) = if let Some(d) = ent.strip_prefix("#x").or_else(|| ent.strip_prefix("#X"))
    {
        (d, 16)
    } else if let Some(d) = ent.strip_prefix('#') {
        (d, 10)
    } else {
        return None;
    };
    if digits.is_empty() || digits.chars().count() > 8 || !digits.chars().all(|c| c.is_digit(radix))
    {
        return None;
    }
    let cp = u32::from_str_radix(digits, radix).ok()?;
    if cp == 0 {
        return None;
    }
    char::from_u32(cp) // None for surrogates and above 0x10FFFF
}

/// Decode the five XML entities and numeric character references. Anything else stays.
pub fn decode_entities(text: &str) -> String {
    let s: Vec<char> = text.chars().collect();
    let n = s.len();
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < n {
        if s[i] == '&' {
            if let Some(j) = (i + 1..n).find(|&j| s[j] == ';') {
                if j - i <= 12 {
                    let ent: String = s[i + 1..j].iter().collect();
                    let ch = match ent.as_str() {
                        "amp" => Some('&'),
                        "lt" => Some('<'),
                        "gt" => Some('>'),
                        "quot" => Some('"'),
                        "apos" => Some('\''),
                        _ => codepoint(&ent),
                    };
                    if let Some(ch) = ch {
                        out.push(ch);
                        i = j + 1;
                        continue;
                    }
                }
            }
        }
        out.push(s[i]);
        i += 1;
    }
    out
}

pub fn escape_text(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
}

pub fn escape_attr(s: &str) -> String {
    escape_text(s).replace('"', "&quot;")
}

/// [+-]? then digits with an optional fraction. No exponents, inf or nan.
pub fn is_number(s: &str) -> bool {
    let s = s.strip_prefix(['+', '-']).unwrap_or(s);
    let (whole, frac) = s.split_once('.').unwrap_or((s, ""));
    if whole.is_empty() && frac.is_empty() {
        return false;
    }
    whole
        .chars()
        .chain(frac.chars())
        .all(|c| c.is_ascii_digit())
}

/// Parse a string that passed is_number.
pub fn number(s: &str) -> f64 {
    s.parse().unwrap_or(f64::NAN)
}

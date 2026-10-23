//! IRELM to resolved events. Stack IRELM (spans that open and close) and stateless IRELM
//! (self-closing span tags that set the whole state) give the same events.

use crate::relm::markup::{decode_entities, scan, Tag, Token};
use crate::relm::table::{command_from_tag, Command, SPANS};

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("bad IRELM: {0}")]
pub struct IrelmError(pub String);

fn bad(message: impl Into<String>) -> IrelmError {
    IrelmError(message.into())
}

#[derive(Debug, Clone, PartialEq)]
pub struct Message {
    pub sub: String,
    pub action: String,
    /// Set when the message has a matching close (see docs/relm.md, MESSAGE).
    pub id: Option<u64>,
    pub close: bool,
}

/// The span state that applies to a piece of text. None is "none": nothing in the IRELM
/// constrains it, so the listener uses its own state (the mood, or the voice settings).
#[derive(Debug, Clone, Default, PartialEq)]
pub struct State {
    pub vad: [Option<f64>; 3],     // v, a, d
    pub prosody: [Option<f64>; 4], // p, s, r, v
    pub voice: Option<String>,
    pub locale: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Text(String, State),
    Message(Message),
    Beep(String),
    Audio(String),
    Pause(f64),
}

const VAD_KEYS: [&str; 3] = ["v", "a", "d"];
const PROSODY_KEYS: [&str; 4] = ["p", "s", "r", "v"];

fn number(cmd: &Command, key: &str) -> Option<f64> {
    cmd.get(key)
        .filter(|v| *v != "none")
        .and_then(|v| v.parse().ok())
}

fn text_value(cmd: &Command, key: &str) -> Option<String> {
    cmd.get(key).filter(|v| *v != "none").map(String::from)
}

/// Lay a span's values over a state. "none" leaves the value underneath.
fn apply(state: &mut State, cmd: &Command) {
    match cmd.name.as_str() {
        "VAD" => {
            for (slot, key) in state.vad.iter_mut().zip(VAD_KEYS) {
                *slot = number(cmd, key).or(*slot);
            }
        }
        "PROSODY" => {
            for (slot, key) in state.prosody.iter_mut().zip(PROSODY_KEYS) {
                *slot = number(cmd, key).or(*slot);
            }
        }
        "VOICE" => {
            state.voice = text_value(cmd, "voice").or(state.voice.take());
            state.locale = text_value(cmd, "locale").or(state.locale.take());
        }
        _ => {} // AS is expanded by relm, a listener ignores it
    }
}

/// Validate one IRELM tag as a command. MESSAGE may carry id and close, which a table may not.
fn command(tag: &Tag) -> Result<(Command, Option<u64>, bool), IrelmError> {
    let mut tag = tag.clone();
    let (mut id, mut close) = (None, false);
    if tag.name == "MESSAGE" {
        let mut rest = Vec::new();
        for (k, v) in tag.attrs.drain(..) {
            match k.as_str() {
                "id" => {
                    id = Some(
                        v.parse()
                            .map_err(|_| bad(format!("id=\"{v}\" is not a number")))?,
                    )
                }
                "close" => close = v == "true",
                _ => rest.push((k, v)),
            }
        }
        tag.attrs = rest;
        if close && id.is_none() {
            return Err(bad("a MESSAGE with close=\"true\" needs an id"));
        }
    }
    if SPANS.contains(&tag.name.as_str()) {
        tag.self_closing = false; // stateless spans are self-closing, the check wants an open tag
    }
    let cmd = command_from_tag(&tag).map_err(|e| bad(e.message))?;
    Ok((cmd, id, close))
}

/// Parse IRELM, with or without the <IRELM> wrapper.
pub fn parse(irelm: &str) -> Result<Vec<Event>, IrelmError> {
    let mut events = Vec::new();
    let mut flat = State::default(); // set by stateless span tags
    let mut stack: Vec<Command> = Vec::new();
    let state = |flat: &State, stack: &[Command]| {
        let mut s = flat.clone();
        for cmd in stack {
            apply(&mut s, cmd);
        }
        s
    };
    for token in scan(irelm) {
        let tag = match token {
            Token::Text(text) => {
                let text = decode_entities(&text);
                if !text.is_empty() {
                    events.push(Event::Text(text, state(&flat, &stack)));
                }
                continue;
            }
            Token::Bad(snippet) => return Err(bad(format!("malformed tag {snippet}"))),
            Token::Tag(tag) => tag,
        };
        if tag.name == "IRELM" {
            continue;
        }
        if tag.closing {
            match stack.pop() {
                Some(top) if top.name == tag.name => continue,
                Some(top) => {
                    return Err(bad(format!(
                        "</{}> closes before </{}>",
                        tag.name, top.name
                    )))
                }
                None => return Err(bad(format!("</{}> was never opened", tag.name))),
            }
        }
        let (cmd, id, close) = command(&tag)?;
        match cmd.name.as_str() {
            _ if cmd.is_span() && tag.self_closing => {
                // Stateless: the tag is the whole state for its kind.
                let mut fresh = State::default();
                apply(&mut fresh, &cmd);
                match cmd.name.as_str() {
                    "VAD" => flat.vad = fresh.vad,
                    "PROSODY" => flat.prosody = fresh.prosody,
                    "VOICE" => (flat.voice, flat.locale) = (fresh.voice, fresh.locale),
                    _ => {}
                }
            }
            _ if cmd.is_span() => stack.push(cmd),
            "MESSAGE" => events.push(Event::Message(Message {
                sub: cmd.get("sub").unwrap_or_default().into(),
                action: cmd.get("action").unwrap_or_default().into(),
                id,
                close,
            })),
            "BEEP" => events.push(Event::Beep(cmd.get("melody").unwrap_or_default().into())),
            "AUDIO" => events.push(Event::Audio(
                cmd.get("file_name").unwrap_or_default().into(),
            )),
            "PAUSE" => events.push(Event::Pause(
                cmd.get("duration")
                    .and_then(|d| d.parse().ok())
                    .unwrap_or(0.0),
            )),
            _ => {}
        }
    }
    Ok(events)
}

/// A mood, as one VAD tag, e.g. <VAD v="3" a="3" d="3"/>. "none" (or a missing param) is None.
pub fn parse_vad(text: &str) -> Result<[Option<f64>; 3], IrelmError> {
    let tokens: Vec<Token> = scan(text)
        .into_iter()
        .filter(|t| !matches!(t, Token::Text(s) if s.trim().is_empty()))
        .collect();
    match tokens.as_slice() {
        [Token::Tag(tag)] if tag.name == "VAD" && !tag.closing => {
            let (cmd, _, _) = command(tag)?;
            let mut state = State::default();
            apply(&mut state, &cmd);
            Ok(state.vad)
        }
        _ => Err(bad(
            "expected one VAD tag, e.g. <VAD v=\"3\" a=\"3\" d=\"3\"/>",
        )),
    }
}

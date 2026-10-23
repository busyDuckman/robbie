//! Events to chunks, the units the listener renders and plays in turn.
//!
//! Speech is split only at blocking commands (BEEP, AUDIO, PAUSE). With marks, a MESSAGE
//! inside speech stays in it as a mark and fires when that point is spoken. Without marks,
//! the speech is split at the message instead.

use super::irelm::{Event, Message, State};

#[derive(Debug, Clone, PartialEq)]
pub enum Piece {
    Text(String, State),
    Mark(Message),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Chunk {
    Speech(Vec<Piece>),
    Message(Message),
    Beep(String),
    Audio(String),
    Pause(f64),
}

impl Chunk {
    /// The messages this chunk sends, in order.
    pub fn messages(&self) -> Vec<&Message> {
        match self {
            Chunk::Speech(pieces) => pieces
                .iter()
                .filter_map(|p| match p {
                    Piece::Mark(m) => Some(m),
                    Piece::Text(..) => None,
                })
                .collect(),
            Chunk::Message(m) => vec![m],
            _ => Vec::new(),
        }
    }
}

fn has_words(pieces: &[Piece]) -> bool {
    pieces
        .iter()
        .any(|p| matches!(p, Piece::Text(t, _) if !t.trim().is_empty()))
}

fn flush(speech: &mut Vec<Piece>, chunks: &mut Vec<Chunk>) {
    let pieces = std::mem::take(speech);
    if has_words(&pieces) {
        chunks.push(Chunk::Speech(pieces));
    } else {
        // Only whitespace to say: the marks are sent as plain messages.
        for piece in pieces {
            if let Piece::Mark(m) = piece {
                chunks.push(Chunk::Message(m));
            }
        }
    }
}

pub fn chunk(events: Vec<Event>, marks: bool) -> Vec<Chunk> {
    let mut chunks = Vec::new();
    let mut speech: Vec<Piece> = Vec::new();
    for event in events {
        match event {
            Event::Text(text, state) => match speech.last_mut() {
                Some(Piece::Text(last, s)) if *s == state => last.push_str(&text),
                _ => speech.push(Piece::Text(text, state)),
            },
            Event::Message(m) if marks => speech.push(Piece::Mark(m)),
            Event::Message(m) => {
                flush(&mut speech, &mut chunks);
                chunks.push(Chunk::Message(m));
            }
            blocking => {
                flush(&mut speech, &mut chunks);
                chunks.push(match blocking {
                    Event::Beep(melody) => Chunk::Beep(melody),
                    Event::Audio(file) => Chunk::Audio(file),
                    Event::Pause(secs) => Chunk::Pause(secs),
                    _ => unreachable!("text and messages are handled above"),
                });
            }
        }
    }
    flush(&mut speech, &mut chunks);
    chunks
}

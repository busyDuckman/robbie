//! TTS engines: speech pieces in, a clip with its marks placed out.

use super::audio::{Clip, ClipEvent};
use super::chunk::Piece;
use super::config::{Config, Vad};
use super::irelm::State;

/// A state with every "none" filled in: VAD from the mood, PROSODY as 1.0 (the voice's own
/// settings), VOICE as None (the engine's default voice).
#[derive(Debug, Clone, PartialEq)]
pub struct Resolved {
    pub vad: [f64; 3],
    pub prosody: [f64; 4],
    pub voice: Option<String>,
    pub locale: Option<String>,
}

impl Resolved {
    pub fn new(state: &State, mood: Vad) -> Self {
        let mood = mood.as_array();
        Self {
            vad: std::array::from_fn(|i| state.vad[i].unwrap_or(mood[i])),
            prosody: state.prosody.map(|p| p.unwrap_or(1.0)),
            voice: state.voice.clone(),
            locale: state.locale.clone(),
        }
    }

    /// PROSODY times the VAD mapping: what an engine without VAD should use (p, s, r, v).
    pub fn delivery(&self, config: &Config) -> [f64; 4] {
        let from_vad = config.vad_to_prosody(self.vad);
        std::array::from_fn(|i| self.prosody[i] * from_vad[i])
    }
}

/// What an engine needs besides the speech.
pub struct Context<'a> {
    pub mood: Vad,
    pub config: &'a Config,
}

pub trait Engine: Send + Sync {
    /// Render speech. Marks become ClipEvent::Message at the time they are reached.
    fn render(&self, speech: &[Piece], ctx: &Context) -> anyhow::Result<Clip>;
}

/// Makes no audio: silence as long as the text would take, with a Say event per text
/// piece so tests can see what was said, with what state, and when.
pub struct DebugEngine {
    pub secs_per_char: f64,
}

impl Default for DebugEngine {
    fn default() -> Self {
        Self {
            secs_per_char: 0.02,
        }
    }
}

fn num(x: f64) -> String {
    let s = format!("{:.2}", x);
    s.trim_end_matches('0').trim_end_matches('.').to_string()
}

/// e.g. "hello [vad 4,4,3 prosody 1,1,1,1 voice -]".
pub fn describe(text: &str, r: &Resolved) -> String {
    let join = |v: &[f64]| v.iter().map(|x| num(*x)).collect::<Vec<_>>().join(",");
    format!(
        "{} [vad {} prosody {} voice {}]",
        text.trim(),
        join(&r.vad),
        join(&r.prosody),
        r.voice.as_deref().unwrap_or("-")
    )
}

impl Engine for DebugEngine {
    fn render(&self, speech: &[Piece], ctx: &Context) -> anyhow::Result<Clip> {
        const RATE: u32 = 16000;
        let mut t = 0.0;
        let mut events = Vec::new();
        for piece in speech {
            match piece {
                Piece::Text(text, state) => {
                    if !text.trim().is_empty() {
                        let r = Resolved::new(state, ctx.mood);
                        events.push((t, ClipEvent::Say(describe(text, &r))));
                    }
                    t += text.chars().count() as f64 * self.secs_per_char;
                }
                Piece::Mark(m) => events.push((t, ClipEvent::Message(m.clone()))),
            }
        }
        let mut clip = Clip::silence(RATE, t);
        clip.events = events;
        Ok(clip)
    }
}

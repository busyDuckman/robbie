//! listener.yaml: the starting mood and the VAD to prosody mapping.

use std::path::Path;

use anyhow::Context;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Vad {
    pub v: f64,
    pub a: f64,
    pub d: f64,
}

impl Default for Vad {
    fn default() -> Self {
        Self {
            v: 3.0,
            a: 3.0,
            d: 3.0,
        }
    }
}

impl Vad {
    pub fn as_array(&self) -> [f64; 3] {
        [self.v, self.a, self.d]
    }
}

/// Prosody change per VAD step away from neutral (3). e.g. p: 0.05 raises pitch 5% per step.
#[derive(Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Change {
    pub p: f64,
    pub s: f64,
    pub r: f64,
    pub v: f64,
}

impl Change {
    fn as_array(&self) -> [f64; 4] {
        [self.p, self.s, self.r, self.v]
    }
}

/// One row per VAD param. A row left out of listener.yaml keeps its default.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct VadProsody {
    pub v: Change,
    pub a: Change,
    pub d: Change,
}

/// The default mapping, also written out in listener/listener.yaml (a test keeps them the same).
/// A starting point, not tuned: arousal moves everything most, valence lifts pitch and range,
/// dominance is louder, a little lower and slower.
impl Default for VadProsody {
    fn default() -> Self {
        let change = |p, s, r, v| Change { p, s, r, v };
        Self {
            v: change(0.03, 0.02, 0.08, 0.0),
            a: change(0.06, 0.08, 0.10, 0.06),
            d: change(-0.03, -0.02, 0.0, 0.06),
        }
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Config {
    /// The mood until one is set over the API. "none" VAD falls back to it.
    pub mood: Vad,
    pub vad_prosody: VadProsody,
}

impl Config {
    pub fn parse(text: &str) -> anyhow::Result<Self> {
        Ok(serde_yaml_ng::from_str::<Option<Self>>(text)?.unwrap_or_default())
    }

    pub fn load(path: impl AsRef<Path>) -> anyhow::Result<Self> {
        let path = path.as_ref();
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("cannot read {}", path.display()))?;
        Self::parse(&text).with_context(|| path.display().to_string())
    }

    /// Prosody multipliers (p, s, r, v) for a VAD, from the mapping.
    pub fn vad_to_prosody(&self, vad: [f64; 3]) -> [f64; 4] {
        let rows = [self.vad_prosody.v, self.vad_prosody.a, self.vad_prosody.d];
        let mut out = [1.0; 4];
        for (value, row) in vad.iter().zip(rows) {
            for (o, change) in out.iter_mut().zip(row.as_array()) {
                *o += (value - 3.0) * change;
            }
        }
        out.map(|m| m.clamp(0.2, 4.0))
    }
}

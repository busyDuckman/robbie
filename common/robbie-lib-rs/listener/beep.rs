//! BEEP: render a melody, "NOTE,DURATION; ..." (see docs/relm.md), to a clip.

use anyhow::bail;

use super::audio::Clip;
use crate::relm::table::check_melody;

pub const RATE: u32 = 22050;
const VOLUME: f32 = 0.5;
const FADE: f64 = 0.005; // seconds, so notes start and stop without a click

/// Equal temperament, A4 = 440 Hz. "C#4", "Eb4" etc. None for a rest (R) or a bad note.
pub fn note_to_frequency(note: &str) -> Option<f64> {
    let c: Vec<char> = note.chars().collect();
    if c.len() < 2 || c.len() > 3 {
        return None;
    }
    let semitone = match c[0] {
        'C' => -9,
        'D' => -7,
        'E' => -5,
        'F' => -4,
        'G' => -2,
        'A' => 0,
        'B' => 2,
        _ => return None,
    };
    let shift = match (c.len(), c[1]) {
        (2, _) => 0,
        (3, '#') => 1,
        (3, 'b') => -1,
        _ => return None,
    };
    let octave = c[c.len() - 1].to_digit(10)? as i32;
    let n = semitone + shift + (octave - 4) * 12;
    Some(440.0 * 2f64.powf(n as f64 / 12.0))
}

/// (frequency, seconds) per note, None frequency for a rest.
pub fn parse_melody(melody: &str) -> anyhow::Result<Vec<(Option<f64>, f64)>> {
    if let Some(problem) = check_melody(melody) {
        bail!("bad melody: {problem}");
    }
    Ok(melody
        .split(';')
        .map(str::trim)
        .filter(|n| !n.is_empty())
        .map(|item| {
            let (note, secs) = item.split_once(',').unwrap_or((item, "0"));
            let (note, secs) = (note.trim(), secs.trim().parse().unwrap_or(0.0));
            (
                if note == "R" {
                    None
                } else {
                    note_to_frequency(note)
                },
                secs,
            )
        })
        .collect())
}

pub fn render(melody: &str) -> anyhow::Result<Clip> {
    let mut samples = Vec::new();
    for (freq, secs) in parse_melody(melody)? {
        let n = (secs * RATE as f64).round() as usize;
        let Some(freq) = freq else {
            samples.extend(std::iter::repeat_n(0.0, n));
            continue;
        };
        let fade = ((FADE * RATE as f64) as usize).min(n / 2).max(1);
        samples.extend((0..n).map(|i| {
            let t = i as f64 / RATE as f64;
            let edge = (i.min(n - 1 - i) as f32 / fade as f32).min(1.0);
            VOLUME * edge * (2.0 * std::f64::consts::PI * freq * t).sin() as f32
        }));
    }
    Ok(Clip {
        rate: RATE,
        samples,
        events: Vec::new(),
    })
}

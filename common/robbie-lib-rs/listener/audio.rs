//! Clips (mono audio plus timed events), and PCM WAV read and write.

use anyhow::{bail, Context};

use super::irelm::Message;

#[derive(Debug, Clone, PartialEq)]
pub enum ClipEvent {
    Message(Message),
    /// Text being spoken, from the debug engine, for tests.
    Say(String),
}

/// A rendered chunk: mono samples, and events at times (seconds) into it.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Clip {
    pub rate: u32,
    pub samples: Vec<f32>,
    pub events: Vec<(f64, ClipEvent)>,
}

impl Clip {
    pub fn silence(rate: u32, secs: f64) -> Self {
        Self {
            rate,
            samples: vec![0.0; (secs.max(0.0) * rate as f64).round() as usize],
            events: Vec::new(),
        }
    }

    /// A clip that only sends messages, at once.
    pub fn messages<'a>(messages: impl IntoIterator<Item = &'a Message>) -> Self {
        Self {
            rate: 16000,
            samples: Vec::new(),
            events: messages
                .into_iter()
                .map(|m| (0.0, ClipEvent::Message(m.clone())))
                .collect(),
        }
    }

    pub fn duration(&self) -> f64 {
        if self.rate == 0 {
            return 0.0;
        }
        self.samples.len() as f64 / self.rate as f64
    }

    /// The same audio at another sample rate (linear interpolation).
    pub fn resampled(&self, rate: u32) -> Vec<f32> {
        if rate == self.rate || self.samples.is_empty() || self.rate == 0 {
            return self.samples.clone();
        }
        let n = (self.samples.len() as u64 * rate as u64 / self.rate as u64) as usize;
        let step = self.rate as f64 / rate as f64;
        (0..n)
            .map(|i| {
                let x = i as f64 * step;
                let j = x as usize;
                let frac = (x - j as f64) as f32;
                let a = self.samples[j.min(self.samples.len() - 1)];
                let b = self.samples[(j + 1).min(self.samples.len() - 1)];
                a + (b - a) * frac
            })
            .collect()
    }
}

fn u16_at(b: &[u8], i: usize) -> u16 {
    u16::from_le_bytes([b[i], b[i + 1]])
}

fn u32_at(b: &[u8], i: usize) -> u32 {
    u32::from_le_bytes([b[i], b[i + 1], b[i + 2], b[i + 3]])
}

/// Read a PCM WAV (8, 16, 24 or 32 bit integer, or 32 bit float), mixed down to mono.
/// A data size too big for the file (as ffmpeg writes to a pipe) means "to the end".
pub fn read_wav(bytes: &[u8]) -> anyhow::Result<(u32, Vec<f32>)> {
    if bytes.len() < 12 || &bytes[0..4] != b"RIFF" || &bytes[8..12] != b"WAVE" {
        bail!("not a WAV file");
    }
    let (mut format, mut channels, mut rate, mut bits) = (0u16, 0u16, 0u32, 0u16);
    let mut i = 12;
    while i + 8 <= bytes.len() {
        let id = &bytes[i..i + 4];
        let size = u32_at(bytes, i + 4) as usize;
        let body = i + 8;
        if id == b"fmt " {
            if body + 16 > bytes.len() {
                bail!("short fmt chunk");
            }
            format = u16_at(bytes, body);
            channels = u16_at(bytes, body + 2);
            rate = u32_at(bytes, body + 4);
            bits = u16_at(bytes, body + 14);
            if format == 0xfffe && size >= 26 {
                format = u16_at(bytes, body + 24); // WAVE_FORMAT_EXTENSIBLE: the sub format
            }
        } else if id == b"data" {
            if channels == 0 || rate == 0 {
                bail!("data before fmt");
            }
            let end = body.saturating_add(size).min(bytes.len());
            let data = &bytes[body..end];
            let width = (bits / 8) as usize;
            let frame = width * channels as usize;
            if frame == 0 {
                bail!("bad sample size");
            }
            let sample = |s: &[u8]| -> anyhow::Result<f32> {
                Ok(match (format, bits) {
                    (1, 8) => (s[0] as f32 - 128.0) / 128.0,
                    (1, 16) => i16::from_le_bytes([s[0], s[1]]) as f32 / 32768.0,
                    (1, 24) => (i32::from_le_bytes([0, s[0], s[1], s[2]]) >> 8) as f32 / 8388608.0,
                    (1, 32) => i32::from_le_bytes([s[0], s[1], s[2], s[3]]) as f32 / 2147483648.0,
                    (3, 32) => f32::from_le_bytes([s[0], s[1], s[2], s[3]]),
                    _ => bail!("unsupported WAV format {format} with {bits} bits"),
                })
            };
            let mut samples = Vec::with_capacity(data.len() / frame);
            for f in data.chunks_exact(frame) {
                let mut sum = 0.0;
                for c in f.chunks_exact(width) {
                    sum += sample(c)?;
                }
                samples.push(sum / channels as f32);
            }
            return Ok((rate, samples));
        }
        i = body.saturating_add(size + (size & 1));
    }
    bail!("WAV has no data")
}

/// A 16 bit mono WAV header for n samples.
pub fn wav_header(rate: u32, n: usize) -> [u8; 44] {
    let data = (n * 2) as u32;
    let mut h = [0u8; 44];
    h[0..4].copy_from_slice(b"RIFF");
    h[4..8].copy_from_slice(&(36 + data).to_le_bytes());
    h[8..16].copy_from_slice(b"WAVEfmt ");
    h[16..20].copy_from_slice(&16u32.to_le_bytes());
    h[20..22].copy_from_slice(&1u16.to_le_bytes()); // PCM
    h[22..24].copy_from_slice(&1u16.to_le_bytes()); // mono
    h[24..28].copy_from_slice(&rate.to_le_bytes());
    h[28..32].copy_from_slice(&(rate * 2).to_le_bytes());
    h[32..34].copy_from_slice(&2u16.to_le_bytes());
    h[34..36].copy_from_slice(&16u16.to_le_bytes());
    h[36..40].copy_from_slice(b"data");
    h[40..44].copy_from_slice(&data.to_le_bytes());
    h
}

pub fn pcm16(samples: &[f32]) -> Vec<u8> {
    samples
        .iter()
        .flat_map(|s| ((s.clamp(-1.0, 1.0) * 32767.0).round() as i16).to_le_bytes())
        .collect()
}

pub fn write_wav(rate: u32, samples: &[f32]) -> Vec<u8> {
    let mut out = wav_header(rate, samples.len()).to_vec();
    out.extend(pcm16(samples));
    out
}

pub fn load_wav_file(path: &std::path::Path) -> anyhow::Result<(u32, Vec<f32>)> {
    let bytes = std::fs::read(path).with_context(|| format!("cannot read {}", path.display()))?;
    read_wav(&bytes).with_context(|| path.display().to_string())
}

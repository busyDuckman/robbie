//! Playback through a sound card, with kira, and kira's decoders for AUDIO files.

use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

use anyhow::{anyhow, Context};
use kira::backend::cpal::cpal::traits::{DeviceTrait, HostTrait};
use kira::backend::cpal::{cpal, CpalBackend, CpalBackendSettings};
use kira::sound::static_sound::{StaticSoundData, StaticSoundSettings};
use kira::sound::PlaybackState;
use kira::{AudioManager, AudioManagerSettings, Frame, Tween};

use super::audio::Clip;
use super::device::{Device, TICK};

/// Output device names, for --device.
pub fn device_names() -> Vec<String> {
    cpal::default_host()
        .output_devices()
        .map(|devices| devices.map(|d| d.to_string()).collect())
        .unwrap_or_default()
}

fn find(name: &str) -> anyhow::Result<cpal::Device> {
    let want = name.to_lowercase();
    cpal::default_host()
        .output_devices()?
        .find(|d| d.to_string().to_lowercase().contains(&want))
        .ok_or_else(|| {
            anyhow!(
                "no output device matches {name:?}, there are: {}",
                device_names().join(", ")
            )
        })
}

/// Frames per audio callback. ALSA's default is far too small for some outputs (e.g. the
/// PulseAudio plugin to WSLg), which then plays only fragments.
const BUFFER: u32 = 2048;

pub struct Speaker {
    manager: AudioManager<CpalBackend>,
}

impl Speaker {
    /// None for the default output device, or part of a device's name.
    pub fn open(name: Option<&str>) -> anyhow::Result<Self> {
        let device = match name {
            Some(name) => find(name)?,
            None => cpal::default_host()
                .default_output_device()
                .context("no default output device")?,
        };
        let supported = device
            .default_output_config()
            .context("cannot read the output device's config")?;
        let mut config = supported.config();
        config.buffer_size = cpal::BufferSize::Fixed(match supported.buffer_size() {
            cpal::SupportedBufferSize::Range { min, max } => BUFFER.clamp(*min, *max),
            cpal::SupportedBufferSize::Unknown => BUFFER,
        });
        let settings = AudioManagerSettings {
            backend_settings: CpalBackendSettings {
                device: Some(device),
                config: Some(config),
            },
            ..AudioManagerSettings::default()
        };
        let manager = AudioManager::new(settings).context("cannot open the audio device")?;
        Ok(Self { manager })
    }
}

impl Device for Speaker {
    fn play(&mut self, clip: &Clip, tick: &mut dyn FnMut(f64) -> bool) -> anyhow::Result<()> {
        if clip.samples.is_empty() {
            tick(0.0);
            return Ok(());
        }
        let frames: Arc<[Frame]> = clip.samples.iter().map(|s| Frame::from_mono(*s)).collect();
        let data = StaticSoundData {
            sample_rate: clip.rate,
            frames,
            settings: StaticSoundSettings::default(),
            slice: None,
        };
        let mut handle = self.manager.play(data)?;
        loop {
            if handle.state() == PlaybackState::Stopped {
                tick(clip.duration());
                return Ok(());
            }
            if !tick(handle.position()) {
                handle.stop(Tween {
                    duration: Duration::from_millis(10),
                    ..Tween::default()
                });
                return Ok(());
            }
            std::thread::sleep(TICK);
        }
    }
}

/// Decode an audio file (wav, ogg, mp3, flac) to a mono clip.
pub fn load(path: &Path) -> anyhow::Result<Clip> {
    let data = StaticSoundData::from_file(path)
        .with_context(|| format!("cannot read {}", path.display()))?;
    Ok(Clip {
        rate: data.sample_rate,
        samples: data
            .frames
            .iter()
            .map(|f| (f.left + f.right) / 2.0)
            .collect(),
        events: Vec::new(),
    })
}

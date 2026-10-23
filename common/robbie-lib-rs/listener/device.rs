//! Playback devices. A device plays one clip at a time, calling tick with the position
//! (seconds) as it goes; tick returns false to stop early.

use std::fs::File;
use std::io::{Seek, SeekFrom, Write};
use std::path::PathBuf;
use std::time::{Duration, Instant};

use anyhow::Context;

use super::audio::{pcm16, wav_header, Clip};

pub trait Device: Send {
    /// Returns once the clip has played, or tick said stop.
    fn play(&mut self, clip: &Clip, tick: &mut dyn FnMut(f64) -> bool) -> anyhow::Result<()>;
}

pub const TICK: Duration = Duration::from_millis(5);

/// Writes what is played to a WAV file, in real time, so a file behaves like a speaker
/// (interrupt, /status and message timing are the same). Interrupted clips are cut short.
pub struct FileDevice {
    file: File,
    pub path: PathBuf,
    pub rate: u32,
    written: usize,
}

impl FileDevice {
    pub fn create(path: impl Into<PathBuf>) -> anyhow::Result<Self> {
        let path = path.into();
        let mut file =
            File::create(&path).with_context(|| format!("cannot write {}", path.display()))?;
        let rate = 22050;
        file.write_all(&wav_header(rate, 0))?;
        Ok(Self {
            file,
            path,
            rate,
            written: 0,
        })
    }

    fn append(&mut self, samples: &[f32]) -> anyhow::Result<()> {
        if samples.is_empty() {
            return Ok(());
        }
        self.file.seek(SeekFrom::End(0))?;
        self.file.write_all(&pcm16(samples))?;
        self.written += samples.len();
        // Keep the header right, so the file is a valid WAV at any time.
        self.file.seek(SeekFrom::Start(0))?;
        self.file.write_all(&wav_header(self.rate, self.written))?;
        self.file.flush()?;
        Ok(())
    }
}

impl Device for FileDevice {
    fn play(&mut self, clip: &Clip, tick: &mut dyn FnMut(f64) -> bool) -> anyhow::Result<()> {
        let duration = clip.duration();
        let start = Instant::now();
        let mut played = duration;
        loop {
            let pos = start.elapsed().as_secs_f64().min(duration);
            if !tick(pos) {
                played = pos;
                break;
            }
            if pos >= duration {
                break;
            }
            std::thread::sleep(TICK.min(Duration::from_secs_f64(duration - pos)));
        }
        let samples = clip.resampled(self.rate);
        let n = ((played / duration.max(f64::MIN_POSITIVE)) * samples.len() as f64) as usize;
        self.append(&samples[..n.min(samples.len())])
    }
}

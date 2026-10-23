//! Audio post-processing: the clip is piped through ffmpeg -af "<filter>" (see docs/relm.md).

use std::io::{Read, Write};
use std::process::{Command, Stdio};

use anyhow::{bail, Context};

use super::audio::{read_wav, write_wav, Clip};

pub fn ffmpeg(clip: &Clip, filter: &str) -> anyhow::Result<Clip> {
    if clip.samples.is_empty() {
        return Ok(clip.clone());
    }
    let mut child = Command::new("ffmpeg")
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-af",
            filter,
        ])
        .args(["-c:a", "pcm_s16le", "-f", "wav", "pipe:1"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .context("cannot run ffmpeg (post-processing needs ffmpeg on the PATH)")?;
    let wav = write_wav(clip.rate, &clip.samples);
    let mut stdin = child.stdin.take().context("ffmpeg stdin")?;
    let writer = std::thread::spawn(move || stdin.write_all(&wav));
    let mut out = Vec::new();
    child
        .stdout
        .take()
        .context("ffmpeg stdout")?
        .read_to_end(&mut out)?;
    let _ = writer.join();
    let mut err = String::new();
    if let Some(mut stderr) = child.stderr.take() {
        let _ = stderr.read_to_string(&mut err);
    }
    if !child.wait()?.success() {
        bail!("ffmpeg -af {filter:?} failed: {}", err.trim());
    }
    let (rate, samples) = read_wav(&out).context("ffmpeg output")?;
    Ok(Clip {
        rate,
        samples,
        events: clip.events.clone(),
    })
}

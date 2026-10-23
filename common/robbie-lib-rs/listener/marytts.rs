//! The marytts engine. Speech goes to MaryTTS as one MaryXML document (INPUT_TYPE
//! RAWMARYXML): prosody per piece of text, <voice> for VOICE, <mark> for marks. Mark times
//! come from the same document rendered as ACOUSTPARAMS.

use anyhow::Context as _;

use super::audio::{read_wav, Clip, ClipEvent};
use super::chunk::Piece;
use super::engine::{Context, Engine, Resolved};
use super::irelm::Message;
use crate::relm::markup::{escape_attr, escape_text, scan, Token};

/// POST a form, return the body. The HTTP client is kept behind this so the engine does not
/// depend on one.
pub trait Http: Send + Sync {
    fn post_form(&self, url: &str, form: &[(String, String)]) -> anyhow::Result<Vec<u8>>;
}

/// The real client.
pub struct Ureq;

impl Http for Ureq {
    fn post_form(&self, url: &str, form: &[(String, String)]) -> anyhow::Result<Vec<u8>> {
        let mut reply =
            ureq::post(url).send_form(form.iter().map(|(k, v)| (k.as_str(), v.as_str())))?;
        Ok(reply
            .body_mut()
            .with_config()
            .limit(200 * 1024 * 1024)
            .read_to_vec()?)
    }
}

pub struct MaryTts {
    pub url: String,
    /// e.g. en_GB. Also the document language.
    pub locale: String,
    /// None for MaryTTS's default voice for the locale.
    pub voice: Option<String>,
    /// More request params, e.g. effect_robot_selected=on.
    pub extra: Vec<(String, String)>,
    pub http: Box<dyn Http>,
}

const MARYXML: &str = "http://mary.dfki.de/2002/MaryXML";

/// A multiplier as a MaryXML percentage change, e.g. 1.1 is "+10%".
fn percent(m: f64) -> String {
    format!("{:+}%", ((m - 1.0) * 100.0).round() as i64)
}

/// The MaryXML document for some speech, and the messages its marks (m0, m1, ...) stand for.
pub fn maryxml(speech: &[Piece], ctx: &Context, locale: &str) -> (String, Vec<Message>) {
    let mut body = String::new();
    let mut marks = Vec::new();
    for piece in speech {
        match piece {
            Piece::Text(text, state) => {
                let r = Resolved::new(state, ctx.mood);
                let [p, s, range, v] = r.delivery(ctx.config);
                let prosody = format!(
                    r#"<prosody pitch="{}" rate="{}" range="{}" volume="{}">{}</prosody>"#,
                    percent(p),
                    percent(s),
                    percent(range),
                    percent(v),
                    escape_text(text)
                );
                match &r.voice {
                    Some(voice) => {
                        body +=
                            &format!(r#"<voice name="{}">{prosody}</voice>"#, escape_attr(voice))
                    }
                    None => body += &prosody,
                }
            }
            Piece::Mark(m) => {
                body += &format!(r#"<mark name="m{}"/>"#, marks.len());
                marks.push(m.clone());
            }
        }
    }
    let lang = locale.replace('_', "-");
    let doc = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?><maryxml xmlns="{MARYXML}" version="0.5" xml:lang="{lang}">{body}</maryxml>"#
    );
    (doc, marks)
}

/// Mark times (seconds) from ACOUSTPARAMS. A phone's end is its time from the start
/// (boundaries before it included); a boundary adds its duration.
pub fn mark_times(acoustparams: &str) -> Vec<(String, f64)> {
    let mut t = 0.0;
    let mut out = Vec::new();
    for token in scan(acoustparams) {
        let Token::Tag(tag) = token else { continue };
        if tag.closing {
            continue;
        }
        let attr = |k: &str| {
            tag.attrs
                .iter()
                .find(|(key, _)| key == k)
                .and_then(|(_, v)| v.parse::<f64>().ok())
        };
        match tag.name.as_str() {
            "ph" => match (attr("end"), attr("d")) {
                (Some(end), _) => t = end,
                (None, Some(ms)) => t += ms / 1000.0,
                _ => {}
            },
            "boundary" => t += attr("duration").unwrap_or(0.0) / 1000.0,
            "mark" => {
                if let Some((_, name)) = tag.attrs.iter().find(|(k, _)| k == "name") {
                    out.push((name.clone(), t));
                }
            }
            _ => {}
        }
    }
    out
}

impl MaryTts {
    fn request(&self, doc: &str, output: &str) -> anyhow::Result<Vec<u8>> {
        let mut form: Vec<(String, String)> = vec![
            ("INPUT_TYPE".into(), "RAWMARYXML".into()),
            ("OUTPUT_TYPE".into(), output.into()),
            ("AUDIO".into(), "WAVE_FILE".into()),
            ("LOCALE".into(), self.locale.clone()),
            ("INPUT_TEXT".into(), doc.into()),
        ];
        if let Some(voice) = &self.voice {
            form.push(("VOICE".into(), voice.clone()));
        }
        form.extend(self.extra.iter().cloned());
        let url = format!("{}/process", self.url.trim_end_matches('/'));
        self.http
            .post_form(&url, &form)
            .with_context(|| format!("MaryTTS {output} at {url}"))
    }
}

impl Engine for MaryTts {
    fn render(&self, speech: &[Piece], ctx: &Context) -> anyhow::Result<Clip> {
        let (doc, marks) = maryxml(speech, ctx, &self.locale);
        let (rate, samples) = read_wav(&self.request(&doc, "AUDIO")?)?;
        let mut clip = Clip {
            rate,
            samples,
            events: Vec::new(),
        };
        if !marks.is_empty() {
            let times = mark_times(&String::from_utf8_lossy(
                &self.request(&doc, "ACOUSTPARAMS")?,
            ));
            let end = clip.duration();
            for (i, m) in marks.into_iter().enumerate() {
                let name = format!("m{i}");
                let t = times.iter().find(|(n, _)| *n == name).map(|(_, t)| *t);
                clip.events
                    .push((t.unwrap_or(end).min(end), ClipEvent::Message(m)));
            }
        }
        Ok(clip)
    }
}

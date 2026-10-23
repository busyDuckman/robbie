//! The listener: queues IRELM, renders the next chunk while the current one plays, plays
//! the clips in order and sends their messages on time.

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex, MutexGuard};
use std::thread::JoinHandle;

use super::audio::{Clip, ClipEvent};
use super::beep;
use super::chunk::{chunk, Chunk};
use super::config::{Config, Vad};
use super::device::Device;
use super::engine::{Context, Engine};
use super::irelm::{parse, IrelmError, Message};
use super::messages::Sink;
use super::post::ffmpeg;
use super::speaker;

#[derive(Debug, Clone, Default)]
pub struct Settings {
    /// MESSAGE inside speech fires on time as a mark (otherwise speech is split there).
    pub marks: bool,
    /// On interrupt, drop the closes of started messages too.
    pub allow_message_interrupt: bool,
    /// Send messages this many seconds early, to make up for latency.
    pub message_early: f64,
    pub audio_dir: Option<PathBuf>,
    /// ffmpeg -af filters.
    pub beep_post: Option<String>,
    pub play_post: Option<String>,
    pub tts_post: Option<String>,
    pub config: Config,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub struct Status {
    pub speaking: bool,
    /// Utterances (/say bodies) waiting behind the one playing.
    pub queued: usize,
}

struct Job {
    gen: u64,
    utt: u64,
    chunk: Chunk,
}

struct Ready {
    gen: u64,
    utt: u64,
    clip: Clip,
}

struct Inner {
    pending: VecDeque<Job>,
    ready: Option<Ready>,
    /// (generation, utterance) of the chunk being rendered, and of the clip playing.
    rendering: Option<(u64, u64)>,
    playing: Option<(u64, u64)>,
    /// Ids of messages sent whose close has not been sent, in the order they started.
    started: Vec<u64>,
    /// The close message for each id, from the IRELM as it was queued.
    closes: HashMap<u64, Message>,
    mood: Vad,
    next_utt: u64,
    quit: bool,
}

impl Inner {
    /// Nothing left to play. Work from before an interrupt (gen) does not count, it is
    /// being dropped.
    fn idle(&self, gen: u64) -> bool {
        let current = |w: Option<(u64, u64)>| w.is_some_and(|(g, _)| g == gen);
        self.pending.is_empty()
            && self.ready.is_none()
            && !current(self.rendering)
            && !current(self.playing)
    }
}

struct Shared {
    inner: Mutex<Inner>,
    changed: Condvar,
    /// Bumped by interrupt. Work from an older generation is dropped.
    gen: AtomicU64,
    settings: Settings,
    engine: Box<dyn Engine>,
    sink: Box<dyn Sink>,
}

impl Shared {
    fn lock(&self) -> MutexGuard<'_, Inner> {
        self.inner.lock().unwrap_or_else(|e| e.into_inner())
    }

    fn wait<'a>(&self, guard: MutexGuard<'a, Inner>) -> MutexGuard<'a, Inner> {
        self.changed.wait(guard).unwrap_or_else(|e| e.into_inner())
    }

    fn post(&self, clip: Clip, filter: &Option<String>) -> Clip {
        match filter {
            Some(f) => ffmpeg(&clip, f).unwrap_or_else(|e| {
                log::warn!("{e:#}");
                clip
            }),
            None => clip,
        }
    }

    fn render(&self, chunk: &Chunk, mood: Vad) -> Clip {
        let s = &self.settings;
        let rendered = match chunk {
            Chunk::Speech(pieces) => self
                .engine
                .render(
                    pieces,
                    &Context {
                        mood,
                        config: &s.config,
                    },
                )
                .map(|c| self.post(c, &s.tts_post)),
            Chunk::Message(m) => Ok(Clip::messages([m])),
            Chunk::Beep(melody) => beep::render(melody).map(|c| self.post(c, &s.beep_post)),
            Chunk::Audio(file) => {
                let path = s.audio_dir.clone().unwrap_or_default().join(file);
                speaker::load(&path).map(|clip| self.post(clip, &s.play_post))
            }
            Chunk::Pause(secs) => Ok(Clip::silence(16000, *secs)),
        };
        rendered.unwrap_or_else(|e| {
            // Still send the messages, so the robot is not left waiting on a close.
            log::warn!("{e:#}");
            Clip::messages(chunk.messages())
        })
    }

    fn fire(&self, event: &ClipEvent, gen: u64) {
        let mut inner = self.lock();
        if self.gen.load(Ordering::SeqCst) != gen {
            return;
        }
        match event {
            ClipEvent::Say(text) => self.sink.say(text),
            ClipEvent::Message(m) => {
                if let Some(id) = m.id {
                    if m.close {
                        inner.started.retain(|s| *s != id);
                        inner.closes.remove(&id);
                    } else {
                        inner.started.push(id);
                    }
                }
                self.sink.send(m);
            }
        }
    }

    fn render_loop(&self) {
        loop {
            let (job, mood) = {
                let mut inner = self.lock();
                loop {
                    if inner.quit {
                        return;
                    }
                    if inner.ready.is_none() && !inner.pending.is_empty() {
                        break;
                    }
                    inner = self.wait(inner);
                }
                let job = inner.pending.pop_front().expect("pending is not empty");
                inner.rendering = Some((job.gen, job.utt));
                (job, inner.mood)
            };
            let clip = self.render(&job.chunk, mood);
            let mut inner = self.lock();
            inner.rendering = None;
            if job.gen == self.gen.load(Ordering::SeqCst) {
                inner.ready = Some(Ready {
                    gen: job.gen,
                    utt: job.utt,
                    clip,
                });
            }
            self.changed.notify_all();
        }
    }

    fn play_loop(&self, mut device: Box<dyn Device>) {
        loop {
            let ready = {
                let mut inner = self.lock();
                loop {
                    if inner.quit {
                        return;
                    }
                    if let Some(ready) = inner.ready.take() {
                        inner.playing = Some((ready.gen, ready.utt));
                        self.changed.notify_all();
                        break ready;
                    }
                    inner = self.wait(inner);
                }
            };
            self.play(&mut *device, ready);
            self.lock().playing = None;
            self.changed.notify_all();
        }
    }

    fn play(&self, device: &mut dyn Device, ready: Ready) {
        let gen = ready.gen;
        let early = self.settings.message_early;
        let due = |(t, e): &(f64, ClipEvent)| match e {
            ClipEvent::Message(_) => (t - early).max(0.0),
            ClipEvent::Say(_) => *t,
        };
        let mut events = ready.clip.events.clone();
        events.sort_by(|a, b| due(a).total_cmp(&due(b)));
        let mut next = 0;
        let mut tick = |pos: f64| {
            if self.gen.load(Ordering::SeqCst) != gen {
                return false;
            }
            while next < events.len() && due(&events[next]) <= pos {
                self.fire(&events[next].1, gen);
                next += 1;
            }
            true
        };
        if let Err(e) = device.play(&ready.clip, &mut tick) {
            log::warn!("playback: {e:#}");
        }
        // Events at (or past) the very end, and any the device did not reach.
        for (_, event) in &events[next..] {
            self.fire(event, gen);
        }
    }
}

pub struct Listener {
    shared: Arc<Shared>,
    threads: Vec<JoinHandle<()>>,
}

impl Listener {
    pub fn new(
        settings: Settings,
        engine: Box<dyn Engine>,
        device: Box<dyn Device>,
        sink: Box<dyn Sink>,
    ) -> Self {
        let mood = settings.config.mood;
        let shared = Arc::new(Shared {
            inner: Mutex::new(Inner {
                pending: VecDeque::new(),
                ready: None,
                rendering: None,
                playing: None,
                started: Vec::new(),
                closes: HashMap::new(),
                mood,
                next_utt: 0,
                quit: false,
            }),
            changed: Condvar::new(),
            gen: AtomicU64::new(0),
            settings,
            engine,
            sink,
        });
        let render = shared.clone();
        let play = shared.clone();
        let threads = vec![
            std::thread::spawn(move || render.render_loop()),
            std::thread::spawn(move || play.play_loop(device)),
        ];
        Self { shared, threads }
    }

    /// Queue IRELM behind anything already playing.
    pub fn say(&self, irelm: &str) -> Result<(), IrelmError> {
        let chunks = chunk(parse(irelm)?, self.shared.settings.marks);
        let mut inner = self.shared.lock();
        let gen = self.shared.gen.load(Ordering::SeqCst);
        let utt = inner.next_utt;
        inner.next_utt += 1;
        for c in chunks {
            for m in c.messages() {
                if let (Some(id), true) = (m.id, m.close) {
                    inner.closes.insert(id, m.clone());
                }
            }
            inner.pending.push_back(Job { gen, utt, chunk: c });
        }
        self.shared.changed.notify_all();
        Ok(())
    }

    /// Stop the audio and clear the queue. The closes of started messages are sent at
    /// once, unless allow_message_interrupt.
    pub fn interrupt(&self) {
        let s = &self.shared;
        let mut inner = s.lock();
        s.gen.fetch_add(1, Ordering::SeqCst);
        inner.pending.clear();
        inner.ready = None;
        let started = std::mem::take(&mut inner.started);
        let mut closes = std::mem::take(&mut inner.closes);
        if !s.settings.allow_message_interrupt {
            for id in started {
                if let Some(m) = closes.remove(&id) {
                    s.sink.send(&m);
                }
            }
        }
        s.changed.notify_all();
    }

    pub fn mood(&self) -> Vad {
        self.shared.lock().mood
    }

    /// Applies to speech rendered from now on.
    pub fn set_mood(&self, mood: Vad) {
        self.shared.lock().mood = mood;
    }

    pub fn status(&self) -> Status {
        let inner = self.shared.lock();
        let mut waiting: HashSet<u64> = inner.pending.iter().map(|j| j.utt).collect();
        waiting.extend(inner.ready.as_ref().map(|r| r.utt));
        let gen = self.shared.gen.load(Ordering::SeqCst);
        let current = |w: Option<(u64, u64)>| w.filter(|(g, _)| *g == gen).map(|(_, u)| u);
        waiting.extend(current(inner.rendering));
        if let Some(utt) = current(inner.playing) {
            waiting.remove(&utt);
        }
        Status {
            speaking: !inner.idle(gen),
            queued: waiting.len(),
        }
    }

    /// Block until everything queued has played.
    pub fn wait_idle(&self) {
        let mut inner = self.shared.lock();
        while !inner.idle(self.shared.gen.load(Ordering::SeqCst)) {
            inner = self.shared.wait(inner);
        }
    }
}

impl Drop for Listener {
    fn drop(&mut self) {
        self.shared.gen.fetch_add(1, Ordering::SeqCst);
        self.shared.lock().quit = true;
        self.shared.changed.notify_all();
        for t in self.threads.drain(..) {
            let _ = t.join();
        }
    }
}

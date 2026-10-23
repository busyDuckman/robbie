//! Listener tests: IRELM parsing and chunking, beeps, and whole runs with the debug engine,
//! a file device and a collecting message sink. The last tests run the listener CLI.

#![cfg(feature = "listener")]

use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use robbie_lib::listener::audio::{load_wav_file, read_wav, write_wav};
use robbie_lib::listener::beep::{note_to_frequency, render};
use robbie_lib::listener::chunk::{chunk, Chunk, Piece};
use robbie_lib::listener::config::Config;
use robbie_lib::listener::device::FileDevice;
use robbie_lib::listener::engine::DebugEngine;
use robbie_lib::listener::irelm::{parse, parse_vad, Event, Message, State};
use robbie_lib::listener::messages::{Collect, Record, Tcp};
use robbie_lib::listener::{Listener, Settings, Vad};
use robbie_lib::relm::{Converter, Options, Table};

fn data() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../robbie-lib-test/relm")
}

fn temp(name: &str) -> PathBuf {
    std::env::temp_dir().join(format!("robbie-listener-{}-{name}", std::process::id()))
}

fn relm(input: &str, stateless: bool) -> String {
    let table = Table::load(data().join("example_table.yaml")).expect("table");
    let options = Options {
        stateless,
        ..Options::default()
    };
    Converter::new(table, options).convert(input).expect("relm")
}

fn msg(sub: &str, action: &str, id: Option<u64>, close: bool) -> Message {
    Message {
        sub: sub.into(),
        action: action.into(),
        id,
        close,
    }
}

// --- parsing

#[test]
fn stack_and_stateless_give_the_same_events() {
    for input in [
        "<happy> She asked me to buy <widen_eyes><emphasis>roses</emphasis></widen_eyes></happy>",
        "<happy> I won <ecstatic>the lottery</ecstatic> but lost the ticket </happy>",
        "<pirate>arr <whisper>matey</whisper></pirate><p/>done",
        "<happy><excited>wow</excited></happy><fanfare/>",
    ] {
        let stack = parse(&relm(input, false)).expect("stack parses");
        let stateless = parse(&relm(input, true)).expect("stateless parses");
        assert_eq!(stack, stateless, "{input}");
    }
}

#[test]
fn nested_spans_resolve_none_to_the_enclosing_value() {
    let events = parse(r#"<VAD v="4" a="4" d="3">a<VAD a="5">b</VAD></VAD>c"#).unwrap();
    let state = |vad: [Option<f64>; 3]| State {
        vad,
        ..State::default()
    };
    assert_eq!(
        events,
        vec![
            Event::Text("a".into(), state([Some(4.0), Some(4.0), Some(3.0)])),
            Event::Text("b".into(), state([Some(4.0), Some(5.0), Some(3.0)])),
            Event::Text("c".into(), State::default()),
        ]
    );
}

#[test]
fn message_ids_and_closes() {
    let events = parse(&relm("<widen_eyes>x</widen_eyes>", false)).unwrap();
    assert_eq!(
        events[0],
        Event::Message(msg("eyes", "widen(0.8)", Some(1), false))
    );
    assert_eq!(
        events[2],
        Event::Message(msg("eyes", "widen(None)", Some(1), true))
    );
}

#[test]
fn bad_irelm_is_refused() {
    for bad in [
        r#"<VAD v="4">a</PROSODY>"#,
        "a</VAD>",
        r#"<VAD v="9">a</VAD>"#,
        r#"<MESSAGE sub="a" action="b" close="true"/>"#,
        r#"<MESSAGE sub="a" action="b" id="x"/>"#,
        r#"<SMILE/>"#,
        r#"<PAUSE duration="1">"#,
        "<VAD v=4>",
    ] {
        assert!(parse(bad).is_err(), "{bad}");
    }
}

#[test]
fn entities_are_decoded() {
    assert_eq!(
        parse("<IRELM>fish &amp; chips</IRELM>").unwrap(),
        vec![Event::Text("fish & chips".into(), State::default())]
    );
}

#[test]
fn mood_tag() {
    assert_eq!(
        parse_vad(r#"<VAD v="4" a="none"/>"#).unwrap(),
        [Some(4.0), None, None]
    );
    assert!(parse_vad("hello").is_err());
    assert!(parse_vad(r#"<VAD v="6"/>"#).is_err());
}

// --- chunking

#[test]
fn speech_splits_only_at_blocking_commands() {
    let events = parse(&relm(
        "hi <widen_eyes>there</widen_eyes><p/>bye<wink/>",
        false,
    ))
    .unwrap();
    let chunks = chunk(events.clone(), true);
    let kinds: Vec<&str> = chunks
        .iter()
        .map(|c| match c {
            Chunk::Speech(_) => "speech",
            Chunk::Message(_) => "message",
            Chunk::Pause(_) => "pause",
            _ => "other",
        })
        .collect();
    // The wink comes after the last words, so it is a mark at the end of "bye".
    assert_eq!(kinds, ["speech", "pause", "speech", "pause"]);
    match &chunks[0] {
        Chunk::Speech(p) => {
            assert!(matches!(p[1], Piece::Mark(_)) && matches!(p[3], Piece::Mark(_)))
        }
        _ => unreachable!(),
    }

    let chunks = chunk(events, false);
    let n = |want: fn(&Chunk) -> bool| chunks.iter().filter(|c| want(c)).count();
    assert_eq!(n(|c| matches!(c, Chunk::Message(_))), 3);
    assert_eq!(n(|c| matches!(c, Chunk::Speech(_))), 3);
}

#[test]
fn messages_with_no_words_are_plain_messages() {
    let chunks = chunk(parse(&relm("<wink/> <fanfare/>", false)).unwrap(), true);
    assert!(matches!(chunks[0], Chunk::Message(_)));
    assert!(matches!(chunks[1], Chunk::Pause(_)));
    assert!(matches!(chunks[2], Chunk::Beep(_)));
}

// --- audio

#[test]
fn notes() {
    let f = |n| note_to_frequency(n).unwrap();
    assert!((f("A4") - 440.0).abs() < 1e-9);
    assert!((f("A5") - 880.0).abs() < 1e-9);
    assert!((f("C4") - 261.6256).abs() < 1e-3);
    assert!((f("C#4") - f("Db4")).abs() < 1e-9);
    assert!((f("Eb4") - 311.1270).abs() < 1e-3);
    assert_eq!(note_to_frequency("H4"), None);
}

#[test]
fn melody_length_includes_rests() {
    let clip = render("C4,0.1; R,0.05; Eb5,0.2").unwrap();
    assert!((clip.duration() - 0.35).abs() < 1e-3);
    assert!(render("C4").is_err());
}

#[test]
fn wav_round_trip() {
    let samples: Vec<f32> = (0..100).map(|i| (i as f32 / 100.0) - 0.5).collect();
    let (rate, back) = read_wav(&write_wav(16000, &samples)).unwrap();
    assert_eq!(rate, 16000);
    assert_eq!(back.len(), 100);
    assert!(back.iter().zip(&samples).all(|(a, b)| (a - b).abs() < 1e-3));
}

#[test]
fn vad_mapping() {
    let config = Config::parse("vad_prosody:\n  a: {p: 0.1, s: 0.05}\n").unwrap();
    let p = config.vad_to_prosody([3.0, 5.0, 3.0]);
    assert!((p[0] - 1.2).abs() < 1e-9 && (p[1] - 1.1).abs() < 1e-9 && p[2] == 1.0);
    assert!(Config::parse("bogus: 1\n").is_err());
}

// --- whole runs

fn listener(name: &str, settings: Settings) -> (Listener, Collect, PathBuf) {
    let path = temp(name);
    let sink = Collect::default();
    let device = FileDevice::create(&path).unwrap();
    let l = Listener::new(
        settings,
        Box::new(DebugEngine::default()),
        Box::new(device),
        Box::new(sink.clone()),
    );
    (l, sink, path)
}

fn marks() -> Settings {
    Settings {
        marks: true,
        ..Settings::default()
    }
}

#[test]
fn plays_in_order_with_marks_on_time() {
    let (l, sink, wav) = listener("order.wav", marks());
    let start = Instant::now();
    l.say(&relm(
        "<happy>one two <widen_eyes>three</widen_eyes></happy><p/>four",
        false,
    ))
    .unwrap();
    l.wait_idle();
    let took = start.elapsed().as_secs_f64();
    let records = sink.records();
    assert_eq!(
        records,
        vec![
            Record::Say("one two [vad 4,4,3 prosody 1,1,1,1 voice -]".into()),
            Record::Message(msg("eyes", "widen(0.8)", Some(1), false)),
            Record::Say("three [vad 4,4,3 prosody 1,1,1,1 voice -]".into()),
            Record::Message(msg("eyes", "widen(None)", Some(1), true)),
            Record::Say("four [vad 3,3,3 prosody 1,1,1,1 voice -]".into()),
        ]
    );
    // The mark fires after "one two " is spoken: 8 chars at 0.02 s.
    let sent = sink.sent.lock().unwrap().clone();
    let gap = sent[1].0.duration_since(sent[0].0).as_secs_f64();
    assert!((0.12..0.4).contains(&gap), "mark after {gap}s");
    // "one two three" (13 chars), the 0.5 s pause, "four" (4 chars): 0.84 s of audio.
    assert!((0.8..2.0).contains(&took), "took {took}s");
    drop(l);
    let (rate, samples) = load_wav_file(&wav).unwrap();
    let secs = samples.len() as f64 / rate as f64;
    assert!((secs - 0.84).abs() < 0.02, "wav is {secs}s");
    let _ = std::fs::remove_file(wav);
}

#[test]
fn none_falls_back_to_the_mood() {
    let (l, sink, wav) = listener("mood.wav", marks());
    l.set_mood(Vad {
        v: 2.0,
        a: 1.0,
        d: 4.0,
    });
    l.say(r#"<VAD a="5">hi</VAD>"#).unwrap();
    l.wait_idle();
    assert_eq!(
        sink.records(),
        vec![Record::Say("hi [vad 2,5,4 prosody 1,1,1,1 voice -]".into())]
    );
    drop(l);
    let _ = std::fs::remove_file(wav);
}

#[test]
fn queued_utterances_play_one_after_another() {
    let (l, sink, wav) = listener("queue.wav", marks());
    l.say(r#"<PAUSE duration="0.2"/>"#).unwrap();
    l.say("one").unwrap();
    l.say("two").unwrap();
    std::thread::sleep(Duration::from_millis(50));
    let status = l.status();
    assert!(status.speaking);
    assert_eq!(status.queued, 2);
    l.wait_idle();
    assert!(!l.status().speaking);
    let says: Vec<Record> = sink.records();
    assert_eq!(says.len(), 2);
    assert!(matches!(&says[0], Record::Say(s) if s.starts_with("one")));
    drop(l);
    let _ = std::fs::remove_file(wav);
}

const LONG: &str = "<widen_eyes>this sentence takes a good while to say out loud</widen_eyes>\
                    <surprise>never</surprise>";

#[test]
fn interrupt_sends_the_closes_of_started_messages() {
    let (l, sink, wav) = listener("interrupt.wav", marks());
    l.say(&relm(LONG, false)).unwrap();
    std::thread::sleep(Duration::from_millis(200));
    l.interrupt();
    assert!(!l.status().speaking, "idle at once after an interrupt");
    l.wait_idle();
    let messages: Vec<Record> = sink
        .records()
        .into_iter()
        .filter(|r| matches!(r, Record::Message(_)))
        .collect();
    assert_eq!(
        messages,
        vec![
            Record::Message(msg("eyes", "widen(0.8)", Some(1), false)),
            Record::Message(msg("eyes", "widen(None)", Some(1), true)),
        ]
    );
    // Nothing more is said after the interrupt, and the queue is empty.
    let n = sink.records().len();
    l.say("after").unwrap();
    l.wait_idle();
    assert_eq!(sink.records().len(), n + 1);
    drop(l);
    let (rate, samples) = load_wav_file(&wav).unwrap();
    assert!(
        (samples.len() as f64 / rate as f64) < 0.5,
        "the clip was cut short"
    );
    let _ = std::fs::remove_file(wav);
}

#[test]
fn allow_message_interrupt_drops_the_closes() {
    let settings = Settings {
        allow_message_interrupt: true,
        ..marks()
    };
    let (l, sink, wav) = listener("allow.wav", settings);
    l.say(&relm(LONG, false)).unwrap();
    std::thread::sleep(Duration::from_millis(200));
    l.interrupt();
    l.wait_idle();
    let messages: Vec<Record> = sink
        .records()
        .into_iter()
        .filter(|r| matches!(r, Record::Message(_)))
        .collect();
    assert_eq!(
        messages,
        vec![Record::Message(msg("eyes", "widen(0.8)", Some(1), false))]
    );
    drop(l);
    let _ = std::fs::remove_file(wav);
}

#[test]
fn messages_go_early() {
    let settings = Settings {
        message_early: 0.1,
        ..marks()
    };
    let (l, sink, wav) = listener("early.wav", settings);
    // The wink is a mark after 0.2 s of speech, so it goes at 0.1 s.
    l.say(&relm("0123456789<wink/>abcdefghij", false)).unwrap();
    l.wait_idle();
    let sent = sink.sent.lock().unwrap().clone();
    let gap = sent[1].0.duration_since(sent[0].0).as_secs_f64();
    assert!((0.07..0.17).contains(&gap), "message after {gap}s");
    drop(l);
    let _ = std::fs::remove_file(wav);
}

#[test]
fn tcp_target() {
    let tcp = Tcp::bind("127.0.0.1:0").unwrap();
    let addr = tcp.addr;
    let client = std::net::TcpStream::connect(addr).unwrap();
    std::thread::sleep(Duration::from_millis(50));
    let path = temp("tcp.wav");
    let l = Listener::new(
        marks(),
        Box::new(DebugEngine::default()),
        Box::new(FileDevice::create(&path).unwrap()),
        Box::new(tcp),
    );
    l.say(r#"<MESSAGE sub="head" action="nod(1, 2)"/>"#)
        .unwrap();
    l.wait_idle();
    let mut line = String::new();
    BufReader::new(client).read_line(&mut line).unwrap();
    assert_eq!(line, "head, nod(1, 2)\n");
    drop(l);
    let _ = std::fs::remove_file(path);
}

// --- the CLI

fn cli(args: &[&str], stdin: &str) -> (bool, String, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_listener"))
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(stdin.as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    (
        out.status.success(),
        String::from_utf8_lossy(&out.stdout).into(),
        String::from_utf8_lossy(&out.stderr).into(),
    )
}

#[test]
fn cli_plays_stdin() {
    let wav = temp("cli.wav");
    let w = wav.to_string_lossy().to_string();
    let irelm = relm("<widen_eyes>hello</widen_eyes><fanfare/>bye", false);
    let (ok, out, err) = cli(&["--tts-engine", "debug", "--device", &w], &irelm);
    assert!(ok, "{err}");
    assert_eq!(
        out,
        "eyes, widen(0.8)\nsay: hello [vad 3,3,3 prosody 1,1,1,1 voice -]\neyes, widen(None)\n\
         say: bye [vad 3,3,3 prosody 1,1,1,1 voice -]\n"
    );
    let (rate, samples) = load_wav_file(&wav).unwrap();
    // hello and bye (0.16 s) plus the fanfare (0.8 s).
    let secs = samples.len() as f64 / rate as f64;
    assert!((secs - 0.96).abs() < 0.03, "wav is {secs}s");
    let _ = std::fs::remove_file(wav);
}

#[test]
fn cli_no_marks_splits_speech() {
    let wav = temp("cli-nomarks.wav");
    let w = wav.to_string_lossy().to_string();
    let irelm = relm("a b<wink/>c d", false);
    let (ok, out, err) = cli(
        &["--tts-engine", "debug", "--device", &w, "--no-marks"],
        &irelm,
    );
    assert!(ok, "{err}");
    assert_eq!(
        out,
        "say: a b [vad 3,3,3 prosody 1,1,1,1 voice -]\neyes, wink(right)\n\
         say: c d [vad 3,3,3 prosody 1,1,1,1 voice -]\n"
    );
    let _ = std::fs::remove_file(wav);
}

#[test]
fn cli_refuses_bad_irelm() {
    let wav = temp("cli-bad.wav");
    let w = wav.to_string_lossy().to_string();
    let (ok, _, err) = cli(
        &["--tts-engine", "debug", "--device", &w],
        "<VAD v=\"9\">x</VAD>",
    );
    assert!(!ok);
    assert!(err.contains("bad IRELM"), "{err}");
    let _ = std::fs::remove_file(wav);
}

#[test]
fn post_processing_pipes_through_ffmpeg() {
    if Command::new("ffmpeg").arg("-version").output().is_err() {
        eprintln!("skipped: no ffmpeg on the PATH");
        return;
    }
    let clip = render("A4,0.2").unwrap();
    let quiet = robbie_lib::listener::post::ffmpeg(&clip, "volume=0.5").unwrap();
    let peak = |s: &[f32]| s.iter().fold(0f32, |m, x| m.max(x.abs()));
    assert_eq!(quiet.rate, clip.rate);
    assert!((quiet.duration() - 0.2).abs() < 0.01);
    assert!((peak(&quiet.samples) - peak(&clip.samples) / 2.0).abs() < 0.02);
    assert!(robbie_lib::listener::post::ffmpeg(&clip, "nosuchfilter").is_err());
}

// --- marytts (no server: the HTTP client is faked)

mod marytts {
    use super::*;
    use robbie_lib::listener::audio::ClipEvent;
    use robbie_lib::listener::engine::{Context, Engine};
    use robbie_lib::listener::marytts::{mark_times, maryxml, Http, MaryTts};
    use std::sync::{Arc, Mutex};

    fn sample() -> String {
        std::fs::read_to_string(data().join("../listener/acoustparams_marks.xml")).unwrap()
    }

    #[test]
    fn mark_times_count_phones_and_boundaries() {
        let times = mark_times(&sample());
        let names: Vec<&str> = times.iter().map(|(n, _)| n.as_str()).collect();
        assert_eq!(names, ["m0", "m1", "m2", "m3"]);
        for ((_, got), want) in times.iter().zip([0.3555, 1.399, 2.199, 3.849]) {
            assert!((got - want).abs() < 1e-6, "{got} vs {want}");
        }
    }

    #[test]
    fn document_has_prosody_voice_and_marks() {
        let config = Config::parse("vad_prosody:\n  a: {s: 0.1}\n").unwrap();
        let ctx = Context {
            mood: Vad::default(),
            config: &config,
        };
        let irelm = relm(
            "<excited>a &amp; b</excited><widen_eyes><pirate>arr</pirate></widen_eyes>",
            false,
        );
        let speech = match &chunk(parse(&irelm).unwrap(), true)[0] {
            Chunk::Speech(p) => p.clone(),
            other => panic!("{other:?}"),
        };
        let (doc, marks) = maryxml(&speech, &ctx, "en_GB");
        assert!(doc.contains(r#"xml:lang="en-GB""#), "{doc}");
        // excited: a=5 (+20% rate from the mapping) times PROSODY s=1.2, p=1.1.
        assert!(
            doc.contains(
                r#"<prosody pitch="+10%" rate="+44%" range="+0%" volume="+0%">a &amp; b</prosody>"#
            ),
            "{doc}"
        );
        assert!(
            doc.contains(r#"<mark name="m0"/><voice name="cmu-bdl-hsmm"><prosody"#),
            "{doc}"
        );
        assert!(
            doc.contains(r#"arr</prosody></voice><mark name="m1"/>"#),
            "{doc}"
        );
        assert_eq!(marks.len(), 2);
        assert!(marks[1].close);
    }

    type Form = Vec<(String, String)>;

    struct Fake {
        calls: Arc<Mutex<Vec<Form>>>,
    }

    impl Http for Fake {
        fn post_form(&self, url: &str, form: &[(String, String)]) -> anyhow::Result<Vec<u8>> {
            assert_eq!(url, "http://mary:59125/process");
            self.calls.lock().unwrap().push(form.to_vec());
            let output = form
                .iter()
                .find(|(k, _)| k == "OUTPUT_TYPE")
                .unwrap()
                .1
                .clone();
            Ok(match output.as_str() {
                "AUDIO" => write_wav(16000, &vec![0.0; 16000 * 4]),
                _ => sample().into_bytes(),
            })
        }
    }

    #[test]
    fn engine_places_marks_from_acoustparams() {
        let calls = Arc::new(Mutex::new(Vec::new()));
        let engine = MaryTts {
            url: "http://mary:59125/".into(),
            locale: "en_GB".into(),
            voice: Some("dfki-obadiah-hsmm".into()),
            extra: vec![("effect_robot_selected".into(), "on".into())],
            http: Box::new(Fake {
                calls: calls.clone(),
            }),
        };
        let config = Config::default();
        let ctx = Context {
            mood: Vad::default(),
            config: &config,
        };
        let speech = match &chunk(
            parse(&relm("I won <widen_eyes>the lottery</widen_eyes>", false)).unwrap(),
            true,
        )[0]
        {
            Chunk::Speech(p) => p.clone(),
            other => panic!("{other:?}"),
        };
        let clip = engine.render(&speech, &ctx).unwrap();
        assert_eq!(clip.rate, 16000);
        let times: Vec<f64> = clip.events.iter().map(|(t, _)| *t).collect();
        assert_eq!(times, [0.3555, 1.399]);
        assert!(matches!(&clip.events[1].1, ClipEvent::Message(m) if m.close));
        let calls = calls.lock().unwrap();
        assert_eq!(calls.len(), 2);
        let get = |k: &str| {
            calls[0]
                .iter()
                .find(|(key, _)| key == k)
                .map(|(_, v)| v.clone())
        };
        assert_eq!(get("INPUT_TYPE").as_deref(), Some("RAWMARYXML"));
        assert_eq!(get("VOICE").as_deref(), Some("dfki-obadiah-hsmm"));
        assert_eq!(get("effect_robot_selected").as_deref(), Some("on"));
    }
}

#[test]
fn listener_yaml_is_the_default() {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("listener/listener.yaml");
    assert_eq!(Config::load(path).unwrap(), Config::default());
    let happy = Config::default().vad_to_prosody([4.0, 4.0, 3.0]);
    assert!((happy[0] - 1.09).abs() < 1e-9 && (happy[1] - 1.10).abs() < 1e-9);
}

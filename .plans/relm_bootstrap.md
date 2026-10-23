# RELM bootstrap plan

Everything left to get RELM working end to end on Robbie, after milestone 1.
Out of scope: the LLM side (getting the LLM to write RELM, telling it the macro names). That is in flight elsewhere.
docs/relm.md is the spec. This file tracks the work.

Pipeline:

    RELM -> relm (lib/cli) -> IRELM -> listener (rust) -> TTS audio + messages to the robot

Design it as if it were its own repo: self contained, logical services. Robbie gets a listener
service configured for it.


## Done

Milestone 1:
  - relm in common/robbie-lib-py and the Rust port in common/robbie-lib-rs.
  - Shared cases in common/robbie-lib-test/relm (convert, table, AS). Both ports pass all of them.
  - CLI: --table --strict --stateless --interactive --locale --serve.
  - AS expansion, English only. Seconds are read out unless zero.
  - just test runs both suites. just vet also loads config/relm_table.yaml with both CLIs.
  - The *_to_ssml flags were built, then removed. The in-memory listener replaces them (no relm export).

A (2026-10-17): MESSAGE ids and close="true", the pairing check, no <IRELM> wrapper in stateless
output, currency codes in AS (e.g. "12.50 AUD"), LOCALE reaches just chat (uv --env-file, chat --locale).

B so far (2026-10-17), in common/robbie-lib-rs/listener and bin/listener.rs (feature listener):
  - IRELM parsing (stack and stateless give the same events), chunking with and without marks.
  - Render ahead and play threads, interrupt (closes of started messages), mood, status, the API.
  - BEEP rendering (equal temperament, A4 = 440 Hz, flats and rests), PAUSE, AUDIO (WAV only).
  - Devices: a .wav file (written in real time) or a sound card with kira (--device list).
  - AUDIO decodes wav, ogg, mp3 and flac with kira. Messages: stdout: and tcp://. ffmpeg post filters.
  - Engines: debug, and marytts (MaryXML via ureq, mark times from ACOUSTPARAMS). Tried end to end
    against MaryTTS: marks fire on time, and the default VAD to prosody mapping changes the speech.
  - Default VAD to prosody mapping built in, written out in listener/listener.yaml. Not tuned.
  - Tests in tests/listener.rs, run by just test.

C (2026-10-17): services/listener, in deploy/compose.local.yaml on 127.0.0.1:8110. Plays through
WSLg's PulseAudio (the image carries the ALSA pulse plugin). Messages to stdout (docker logs).
Robbie's settings in config/robbie_services/listener.yaml. just relm "<happy>hi</happy>" speaks RELM.
Pi audio notes in docs/pi_setp.md. Voice settings still MaryTTS defaults (question 1).

MaryTTS 5.2 probes (WAVs in .temp/emotionml):
  - EmotionML works: categories (happy, sad, angry) and pad-dimensions both change pitch and rate.
  - EmotionML and SSML do not mix. <emotion> inside SSML is ignored. SSML inside EmotionML is an HTTP 500.
  - Several <emotion> elements in one EmotionML document work. Each becomes its own paragraph.
  - MaryTTS turns EmotionML into MaryXML <prosody> (e.g. happy pitch +6% rate +10%, sad pitch -18% rate -30%).
    These are a starting point for the VAD to prosody config.
  - MaryXML (INPUT_TYPE RAWMARYXML) takes it all in one document: nested <prosody>,
    <boundary duration="800"/> for pauses, <voice name=...> mid document, <mark name=...>, <t accent="L+H*">.
    Not yet confirmed by ear: that the voice change is audible.
  - Marks survive into ACOUSTPARAMS in sequence with the phone durations, so mark times can be computed.
    Not yet written or proven.


## Decisions (from the 2026-10-16 planning session)

  - The listener is Rust only. relm stays Python and Rust.
  - Chunking lives inside the listener, as an array. It is not a file format.
  - Marks are on by default: a MESSAGE inside speech stays in the speech as a mark and fires on time.
    --no-marks splits the speech into separate utterances instead.
  - The listener copes with several speech formats (MaryXML for marytts).
  - MESSAGE does not block. SPEECH, BEEP and AUDIO are done when played. PAUSE is done when its time has passed.
  - Playback uses kira. --device can be a file.
  - Audio post-processing is an ffmpeg -af filter string, piped (no temp file).
  - listener.yaml holds the VAD to prosody mapping and the starting mood.
  - API: POST /say, POST /interrupt, PUT and GET /mood, GET /status, GET /health (see docs/relm.md).
  - Interrupt sends the closes of started messages, unless --allow-message-interrupt.
  - Messages go to --message-url, where the scheme picks the protocol (stdout:, tcp://, mqtt://, ros:).
    Robbie's Zenoh or NATS becomes a scheme once chosen.
  - ROS uses a custom RelmMessage (header stamp, sub, action), one topic per sub. It is an optional extra.
  - MESSAGE ids:
    - relm makes them with a running counter, kept across replies for the life of a relm instance.
    - Every id has exactly one open and one close.
    - The close message carries the same id and close="true".
    - In a macro with several messages, the nth MESSAGE in name pairs with the nth in /name.
      The counts must match, or the table fails to load. e.g.
          surprise opens:   widen(0.8)  -> id 1      tilt(0.3)  -> id 2
          /surprise closes: widen(None) -> id 1      tilt(None) -> id 2
    - Messages in a macro without a /name entry get no id.
  - Stateless output has no <IRELM> wrapper.
  - The VAD to prosody mapping is a config.
  - Robbie's relm runs in agent/llm, which already uses the Python lib (chat.py, llm.py).
  - The Robbie listener service is its own container in services/.
  - Vetted crates: kira, rust-mqtt, rclrs (in the common/robbie-lib-rs/Cargo.toml menu).
  - Milestone 1 behaviour is confirmed as built ("whatever is reasonable"; --strict is for tests and evals,
    best effort for normal running):
       - best effort (not --strict):
         - an unknown tag is dropped and its text kept;
         - a stray close is ignored;
         - closing an outer tag closes the inner ones;
         - unclosed tags close at the end;
         - a malformed tag stays as escaped text;
         - params on a macro are ignored;
         - macro names match case-insensitively.
       - a macro with no span and no /name (e.g. p) is never stacked: <p>, <p/> and a stray </p> are all fine.
         A span macro written <happy/> opens and closes at once.
       - close order: spans close (in reverse), then the /name commands run. The order is not visible.
       - text in RELM has its entities decoded, then is escaped again. Long param names become the aliases.
       - AS:
         - English only, default locale en_GB;
         - US style for a US region, British style for every other;
         - "at" joins a date and a time;
         - currency defaults to pounds for GB, euros for IE, otherwise dollars.
       - relm --serve binds to 127.0.0.1 only.


## Open questions

  1. TTS engine settings (voice, locale, rate, MaryTTS effects such as robot): how the listener gets them.
     Deferred.
  2. Hearing kira in WSL: ALSA there has no card, only null.


## Work

### A. relm changes (py and rs, shared cases)
  - MESSAGE ids and close="true" (as decided above). Table check for the pairing rule.
  - Stateless output without the <IRELM> wrapper.
  - Update the shared cases to match. Check agent/llm still works (it imports relm.convert, relm.table).

### B. listener_lib and listener CLI (rust)
  - Parse IRELM (stack or stateless) into resolved events, so both look the same.
  - Chunk into an array: speech, BEEP, AUDIO, PAUSE, MESSAGE.
    - Speech is split only at blocking commands.
    - With marks, a MESSAGE inside speech becomes a mark.
  - Keep the list of started messages awaiting a close (by id), for interrupt.
  - TTS engines:
    - debug: prints text, makes no audio. For tests.
    - marytts: MaryXML. VAD becomes prosody via listener.yaml. Mark times come from ACOUSTPARAMS.
  - BEEP: render the melody. Port note_to_frequency from robbie_restoration audio/music.py,
    adding flats and rests (R).
  - AUDIO: play from --audio-dir.
  - Render ahead (fetch the next chunk's WAV while the current one plays) to avoid stutter.
  - Message targets, stdout: and tcp:// first. --message-early.
  - API (--serve <port>), --interactive, --device (file or playback device), the post options.
  - Tests: unit tests, plus tests that run the listener CLI with the debug engine and a file device.

### C. Robbie listener service (a container in services/)
  - A container running listener --serve with Robbie's listener.yaml and voice settings (question 1).
  - The message target is a stub (stdout or tcp) until the messaging layer exists.
  - "none" falls back to the mood (the starting mood until a mood service sets it).

### D. Integration tests (testing/integration_tests/relm, run by just vet)
Sample RELM, then relm, then IRELM, then the listener, then MaryTTS, then checks on the output.
Needs the docker stack up. Checks use MaryTTS ALLOPHONES and ACOUSTPARAMS and the WAV written
by --device=file, not listening:
  - an emphasised word gets a higher pitch peak or longer duration than when unmarked;
  - AS text is spoken as the expected words;
  - a VOICE span changes the voice for that part;
  - PAUSE and BEEP add the expected time;
  - messages arrive in order, at about the right times (via stdout: or tcp://);
  - interrupt sends the closes of started messages;
  - a happy and a sad version of one line differ in the expected direction.

### E. Small extras
  - A just recipe to hear a RELM line end to end, like just say, e.g. just relm "<happy>hi</happy>".
  - The relm --serve bind address, if relm ends up in a container.


## Suggested order

  1. Answer the open questions, then A.
  2. B with the debug engine and its tests, then the marytts engine.
  3. C, then D.

# RELM bootstrap plan

Everything left to get RELM working end to end on Robbie, after milestone 1.
Out of scope: the LLM side (getting the LLM to write RELM, telling it the macro names). That is in flight elsewhere.

Pipeline:

    RELM -> relm (lib/cli) -> IRELM -> listener -> MaryTTS speech + messages to the robot


## Done (milestone 1)

  - relm in common/robbie-lib-py and the Rust port in common/robbie-lib-rs.
  - Shared cases in common/robbie-lib-test/relm (convert, table, AS). Both ports pass all of them.
  - CLI: --table --strict --stateless --interactive --locale --serve.
  - Simple SSML flags: prosody, voice, pause, message, audio, as.
  - AS expansion, English only.
  - just test runs both suites. just vet also loads config/relm_table.yaml with both CLIs.


## Open questions (need a decision)

  1. Output shape with the *_to_ssml flags. Today SSML is mixed into IRELM inside <IRELM>.
     Options: keep it mixed, or have the flags produce a full SSML <speak> document (then VAD,
     MESSAGE etc. need a home, e.g. <mark>). This also decides what the docs/relm.md pipeline
     line should say.

    I have the wrong shape

    lets do 
    
     relm export --format=SSML --selected_tokens=
     relm export --format=MARYXML --selected_tokens=
     relm export --format=EMOTIONML --selected_tokens=
    

  2. VAD to prosody numbers for --vad_to_ssml (e.g. arousal drives rate and pitch, valence drives
     pitch range, dominance drives volume). Needs your call on the mapping and its strength.

    use a config

  3. VAD to EmotionML for --vad_to_emotionml. Proposal: the pad-dimensions vocabulary
     (pleasure, arousal, dominance), with 1-5 scaled to 0-1 as (x - 1) / 4.
  4. Where the Robbie listener lives: inside the voice service, or as its own container next to it.
  5. How MESSAGE reaches the robot. ros_bridge and the message bus (proto/) do not exist yet,
     so the first cut needs a stub (log or stdout) and a decided interface to swap in later.
  6. Where audio plays. Today /say returns a WAV and the caller plays it (just say uses ffplay).
     Timing MESSAGE to the speech needs the listener to know where in the audio each mark falls.
  7. Where the "none" fallback comes from. "none" means the listener's own state (a mood).
     There is no mood service yet, so it is probably neutral (3, 3, 3) from config for now.
  8. Getting robbie-lib-py into the voice container. The build context is services/voice, so
     common/ is not visible. Options: build from the repo root, or copy the lib in with a just
     recipe.
  9. Milestone 1 choices to confirm, listed in chat at the end of milestone 1 (best effort rules,
     instant macros, close order, AS details, SSML mappings, --serve on 127.0.0.1).
  10. docs/relm.md fixes:
      - the stateless example on line 54 leaves out r="none";
      - the second "expands to (llm side)" label;
      - the listener CLI options are empty.


## Unknowns to check first (MaryTTS 5.2)

Probe these with small scripts run in the voice container, as was done for emphasis and say-as.

  - Does it accept EmotionML input (INPUT_TYPE EMOTIONML), and with which vocabularies?
  - Does <voice> switch voices mid document?
  - Does <break time="0.5s"/> work?
  - Does <audio> do anything? It is probably ignored.
  - Does pitch/rate/volume/range on <prosody> work, in percent?
  - Can it report where a <mark> falls in the audio (REALISED_DURATIONS, ACOUSTPARAMS)?

The answers decide which SSML flags are worth using with MaryTTS, and how MESSAGE gets timed.


## Work

### A. Spec cleanup
Update docs/relm.md with the decisions above. Fill in the listener section.

### B. Remaining relm flags (py and rs, shared cases)
  - --vad_to_emotionml and --vad_to_ssml, once questions 1 to 3 are decided.
    When --vad_to_ssml and --prosody_to_ssml are used together, resolve them to the effective prosody.
  - --beep_to_ssml: render a melody to a temporary WAV.
    - Port note_to_frequency from robbie_restoration audio/music.py, adding flats and rests (R).
    - Shared tests check the parsed notes, frequencies and durations, plus the WAV length.
      Sample bytes may differ between ports in the last float bit, so they are not compared.

### C. listener_lib (py and rs, shared cases)
A library that makes a listener easy to write.
  - Parse IRELM (real XML) into an event stream: text, command, span open, span close.
  - Resolve the stack, so every text chunk carries its full state (VAD, PROSODY, VOICE).
    Stack and stateless input then look the same to a listener.
  - Split into segments at the blocking commands (BEEP, AUDIO, PAUSE). MESSAGE does not block.
  - Helpers:
    - parse a melody;
    - fill "none" from a fallback state (mood);
    - combine nested PROSODY multipliers.
  - Shared cases in robbie-lib-test/relm/listener_cases.json.
    A strong check: for every convert case, the stack and stateless output must give identical
    resolved events.

### D. Sample listener CLI (py and rs)
  - Reads IRELM on stdin and prints the resolved timeline as JSON lines, one event per line.
  - Good for debugging a table, and a template for writing a real listener.
  - Tests call the CLI, both ports, and compare against the shared expected output.

### E. Robbie listener and dispatch (voice service, or beside it per question 4)
  - New endpoint, e.g. POST /irelm. It returns audio, or plays it, per question 6.
  - For each speech segment, build MaryTTS SSML:
    - VAD and PROSODY become prosody;
    - VOICE becomes the voice;
    - text is passed through, already expanded by AS.
  - BEEP becomes a rendered WAV, PAUSE becomes silence, AUDIO plays a file from data/audio
    (by key or name).
  - Join the segments into one WAV, or play them in order.
  - MESSAGE goes to a dispatcher, a stub for now (question 5), timed to the speech where
    MaryTTS allows it.
  - "none" falls back to a configured mood (question 7).
  - Settings live in config/robbie_services/voice.yaml, e.g. VAD mapping strengths and the fallback mood.

### F. Integration tests (testing/integration_tests/relm, run by just vet)
Sample RELM, then relm, then IRELM, then the listener, then MaryTTS, then checks on the output.
Needs the docker stack up. Checks use MaryTTS ALLOPHONES and ACOUSTPARAMS output, not listening:
  - an emphasised word gets a higher pitch peak or longer duration than when unmarked;
  - AS text is spoken as the expected words (the token list);
  - a VOICE span changes the voice (or locale) for that part;
  - PAUSE and BEEP add the expected time;
  - MESSAGE stubs are called, in order;
  - a happy and a sad version of one line differ in the expected direction
    (once the VAD mapping exists);
  - EmotionML input is accepted, if MaryTTS supports it.

### G. Small extras
  - A just recipe to hear a RELM line end to end, like just say, e.g. just relm "<happy>hi</happy>".
  - The relm --serve bind address, if the converter ends up in a container.


## Suggested order

  1. Probe the MaryTTS unknowns, answer the open questions, then do A.
  2. C and D (listener_lib, sample listener and their tests). These need no decisions about Robbie.
  3. E with stubs, then F.
  4. B (the hard flags). They matter less if the Robbie listener talks to MaryTTS itself,
     so do them last, or drop any MaryTTS cannot use.

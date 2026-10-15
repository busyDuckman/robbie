# Build Plan

Status: Draft

Related: [character brief](robbie_agent.md), [ethics and privacy design](../docs/ethics_and_privacy_design.md), [architecture decisions](../docs/adr_listing.md), [Layer B to Layer C interface](../docs/interfaces/layer_b_c_interface.md).

## Goals

- Robbie's character, as described in the brief: emotive, self-actuated, character-driven and open source.
- A low-cost robot for group situations such as stores, social events and meetings, available under the MIT licence.
- Built using current professional practices for AI agents and typical .

## Tech stack

- Three layers: A (the LLM), B (the harness) and C (robot control). See ADR 1.
- This repo covers A and B. Layer C is a separate ROS 2 repo. See ADR 2.
- Custom ROS 2 messages for the B to C interface live in a `robbie_interfaces` package in this repo, so anyone with a robot can implement it and make it a Robbie.
- Languages: Python, Rust and C++ are fine. If rust vs c++ is a choice on equal footing, use rust. Minimise, but don't ban, use of Java. C# is permissible, if needed, but only .NET v5 onward.
- The 'backend' refers to a PC or cloud compute service to run the parts of robbie too intensive to fit on a Pi. Which parts of B run on the Pi and which on the backend: see [Layer B: the harness](../docs/layer_b_harness.md).
  - Minimum system requirements of 16Gb VRAM and 32GB RAM.
    - 16GB VRAM is deliberate, not an oversight: it's the GPU that's affordable now, and keeping to it makes Robbie accessible to more people. It is known to be tight, since the LLM, speech recognition, any neural TTS, embeddings and eval judge models all share it. Work within it rather than raising it.
    - Components that can run on the CPU or the Pi help the budget. For example, MaryTTS can run on the Pi.
  - Docker
- use justfiles where sensible

## Proposed approach 

**Agent design**
1. Mood and relationships are held as explicit state in code, for example a mood that decays over time and a per-person affinity score. They are given to the LLM as context rather than left to the prompt, so they can be tested.

2. B decides when to call the LLM (when Robbie is addressed, a new person arrives, the conversation lulls, or it gets bored). The LLM then decides whether to speak or act. This is how Robbie can start conversations on its own.

3. A policy gate in B checks every action the LLM proposes against an allow-list and limits before it runs, because prompts aren't a reliable security boundary.

4. B's capabilities (eyes, sounds, motion, memory) are exposed to the LLM as MCP servers.

5. The LLM is accessed through a small interface, with a local server behind it. llama.cpp is the default.
    - vLLM will be tried later as a comparison exercise (benchmarked against llama.cpp). Already discussed (2026-10-14): vLLM's advantage is throughput across many simultaneous requests, so it brings little for a single user, and by default it reserves most of the GPU's memory.

6. The agent loop hopefully based on Python AI. Its possible the novelty of the task may require a hand-written loop instead.
    - Already discussed (2026-10-14): heavier frameworks (LangChain, CrewAI) were ruled out because they want to own memory and state, which live in B here.
    - The LLM's structured output is defined in [LLM structured output](../docs/interfaces/llm_structured_output.md).

7. Persona fine-tuning: a QLoRA fine-tune (Unsloth or Hugging Face PEFT) on synthetic dialogue, which fits within 16GB VRAM.

**Quality**
7. Evals act as a CI gate. They cover persona consistency, mood behaviour, tool use, the policy gate, privacy and prompt injection, and they use only synthetic data.
    - Eval harness: Inspect AI.
    - Scenarios will be created for every part of the ethics and privacy design and added to the tests. They live in the tests, not in the design doc.
    - Red-teaming for prompt injection and jailbreaks: garak or PyRIT. TODO: decide which.
    - Guard models: Llama Guard or ShieldGemma, small local classifiers that check the LLM's inputs and outputs in B. TODO: decide which.
    - Memory retrieval evals: Ragas.
    - Prompts live in files, versioned by git. Every eval run records the prompt version (git commit) and the model used, so runs can be compared. Prompts are tested with multiple metrics.
    - Eval runs, model versions and prompt versions are tracked in a self-hosted MLflow.
8. Tracing uses OpenTelemetry, sent to a self-hosted Langfuse or Phoenix, and records timings and tool calls but not conversation content.
9. Tooling: `uv`, `ruff`, `pyright`, `pre-commit`, pytest, and Docker. GitHub Actions written but disabled at first.
    - The NVIDIA Container Toolkit for GPU access in Docker (via WSL2 on Windows).
    - Already discussed (2026-10-15): dev containers were dropped. Linux or WSL 2 (ADR 4) plus `just setup` covers the need, and dev containers make GPU, mic, webcam and Docker access awkward.
    - `just test` runs the basic unit tests. `just vet` runs full testing including model evals, which needs a GPU, so it runs manually or on a self-hosted runner rather than on hosted CI.
    - Already discussed (2026-10-14): MkDocs Material for published docs was rejected.

**Documentation**
- A system card for Robbie: intended use, limitations, and that it isn't yet for public settings.
- A lightweight Data Protection Impact Assessment (DPIA). The ethics and privacy design already covers most of it.

**Components**
10. TTS: Marry TTS amy be the go. Piper/Kokoro lack the emotional expression and I'm OK with robbie sounding old. Mary TTS has a great robot setting I tuned in once. This needs a review of latest tech.
    - Already compared (2026-10-14): MaryTTS has emotion control (EmotionML, SSML prosody) and built-in robot effects, but it's Java and largely unmaintained. Piper and Kokoro sound better but have no emotion control. Emotion-capable neural options to review: Chatterbox, Orpheus, Parler-TTS, StyleTTS2 (all need GPU, so they cost VRAM). The robotic sound could also be audio post-processing in B, independent of the TTS engine.
11. Speech recognition: Silero VAD, faster-whisper. "The new one Nvidia just put out" (tm).
    - Who said what is a hard requirement (see the ethics and privacy design).
    - Microphone: probably a ReSpeaker array.
    - Candidates for who said what, including NVIDIA Nemotron 3 Diarization: see [who said what](../docs/backend/who_said_what.md).
11. Vision: MediaPipe. 
12. Memory: SQLite with SQLCipher and sqlite-vec.
13. Redaction: Microsoft Presidio plus a local classifier.
14. Simulation and visualisation: Rerun, It looks cool and avoids JavaScript.
15. A fake Layer C in this repo, so A and B can be tested without hardware. (KEEP IT SIMPLE)

## Proposed milestones

1. **Foundations:** repo setup, CI, event schemas, the bridge interface and the fake Layer C.
2. **Text-only character:** LLM interface, agent loop, persona, mood and the policy gate, with evals.
3. **Privacy and memory:** redaction, compartmented storage, deletion and an audit log.
4. **Expression:** MCP servers, gaze targets and eye expression sent to the fake Layer C, and a visualisation.
5. **Voice:** streaming speech in and out, with turn-taking in groups.
6. **Perception and identity:** faces, attention and opt-in identity.
7. **Observability:** tracing and published eval results.
8. **Layer C integration:** agree the interface details and run the evals with Robbie's real Layer C.
9. **Public mode** robbie has been tested has a minimal feature set for public use (explicitly of the table for quite a while). Includes implementing the encrypted network traffic setting.

# Notes:
  - First deployments are NOT DESIGNED FOR USE IN PUBLIC SETTINGS. The persona and security will need time to be tested and made suitable. 
  - B's internal messaging has to work across languages. Zenoh / NATS
    - Already discussed (2026-10-14): GraphQL was considered and rejected; it suits client-facing request/response APIs, not low-latency event messaging.
    - Messages are defined as Protobuf schemas, checked with `buf`.
    - Note: `rmw_zenoh` lets Zenoh talk to ROS 2 directly, which could make the B to C bridge node very thin.
  - Parts of B written in different languages are containerised and talk to each other over the messaging layer. Embedding Rust in Python (PyO3 / maturin) is only for if it ever becomes necessary.

## Settings file

A settings file will be needed. It is JSON or a similar standard format, not a DSL, and is validated against a schema (for example with Pydantic Settings). Known settings so far:
  - Public space mode.
  - Which persona.
  - Location (country and region), so Robbie knows which laws apply.
  - Encrypt network traffic, for example when a backend node is in the cloud and not on a VPN. Not implemented until milestone 9.

## Open questions

1. Which local model, and is its licence compatible with the MIT goal?
4. How far should the persona go in public settings, compared to non public settings?
5. Should Robbie listen continuously so it can join conversations, or wait for a wake word?
7. Which parts of the closed-source predecessor projects will be brought in.

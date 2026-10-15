# Who Said What

Status: Draft. Notes from research on 2026-10-14; nothing chosen yet.

Robbie has to know who said what, and who was present, throughout a session. This is a hard requirement from the [ethics and privacy design](../ethics_and_privacy_design.md). For example, Robbie must not repeat something a couple said privately once a salesperson joins the conversation.

## Hardware

Probably a ReSpeaker microphone array. As well as audio, it reports the direction a voice comes from, which could help match a voice to a face.

## Candidate: NVIDIA Nemotron 3 Diarization

This is the main candidate. It's a speaker diarisation model, meaning it works out which voice is speaking when. It was released in September 2026, succeeds NVIDIA's Streaming Sortformer v2.1, and has streaming (live) and offline modes. It reportedly handles up to eight speakers. It is available on Hugging Face and through NVIDIA's NeMo framework, and is reported to be released under the OpenMDW 1.1 licence, which allows commercial use.

To check:
- The licence on NVIDIA's own model card, against the MIT goal.
- VRAM use, within the 16GB budget.

## Other candidates

- **NVIDIA Streaming Sortformer v2 / v2.1.** The predecessor to Nemotron 3 Diarization. Open, runs locally and streams, but limited to four speakers. parakeet-rs already supports it.
- **pyannote Community-1.** The open pipeline in pyannote.audio 4.0, the most widely used open-source diarisation toolkit. The code is MIT and the model weights are CC-BY-4.0, both compatible with the MIT goal given attribution. It is mainly built for recorded audio rather than live streaming. pyannote also sells a commercial model (Precision-2), which isn't an option here.
- **diart.** A streaming diarisation library built on pyannote models. Its current maintenance status and licence weren't confirmed.
- **WhisperX.** Combines Whisper transcription with pyannote diarisation. Popular, but it works on recorded audio rather than live, so it's more useful as a comparison or for testing than for Robbie's live use.

Not checked: DiariZen, and any head-to-head comparison of these models on live, multi-person audio.

## Pairing it with speech recognition

Diarisation only says who spoke when; a speech recognition model provides the words. One option is NVIDIA's multitalker-parakeet-streaming-0.6b-v1. It produces speaker-attributed transcripts using diarisation output as its input, and needs no enrolment audio. It runs one instance per speaker, so compute grows with the number of people. Its licence is the NVIDIA Open Model License.

The Rust library parakeet-rs supports speaker-attributed transcription with multitalker Parakeet and Sortformer.

## Limitation

These models tell voices apart, but not who a person is. Linking a voice to a known person still needs face or identity matching in Layer B, which could use the ReSpeaker's direction data.

## Sources

- [Nemotron 3 Diarization overview (HackerNoon)](https://hackernoon.com/nemotron-3-diarization-heres-what-you-need-to-know)
- [Nemotron 3 Diarization licence report (Crypto Briefing)](https://cryptobriefing.com/nvidia-nemotron-3-speaker-diarization/)
- [Streaming Sortformer v2 model card](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/blob/main/README.md)
- [multitalker-parakeet-streaming-0.6b-v1 model card](https://huggingface.co/nvidia/multitalker-parakeet-streaming-0.6b-v1/blob/main/README.md)
- [parakeet-rs](https://docsearch.algolia.com/mcp/docs/repo/altunenes/parakeet-rs)
- [Nemotron 3 Diarization listing (gradually.ai)](https://www.gradually.ai/en/ai-models/nemotron-3-diarization/)
- [Top speaker diarisation models in 2026 (pyannoteAI, a vendor)](https://www.pyannote.ai/blog/top-7-speaker-diarization-apis-and-models-in-2026)
- [Speaker diarisation models guide (Kili Technology)](https://kili-technology.com/blog/speaker-diarization-models-guide-benchmarks-and-failure-modes-2026)

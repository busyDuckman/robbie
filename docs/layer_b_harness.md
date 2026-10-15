# Layer B: The Harness

This **DRAFT** describes how Layer B  is put together.

is split between the Pi on the robot and the backend (a PC or cloud compute with at least 16GB VRAM, see ADR 3). Only obvious placements are assigned; everything else is undecided.

## What runs where

The split between the Pi on the robot, and on the backend (a PC or cloud compute with at least 16GB VRAM, see ADR 3).

Pi side (on the robot):
  - camera capture
  - microphone capture (probably a ReSpeaker array)
  - speaker playback

Backend side:
  - the LLM (Layer A)
  - speaker diarisation (who said what), for example Nemotron 3 Diarization; see [who said what](backend/who_said_what.md)

Undecided:
  - voice activity detection
  - speech recognition
  - TTS (MaryTTS can run on the Pi)
  - beeps and audio effects
  - face detection and identification
  - attention and gaze target selection
  - mood, relationships and other state
  - the policy gate
  - memory, redaction and the audit log
  - the ROS 2 bridge node to Layer C
  - the messaging layer (Zenoh or NATS) setup

Whatever isn't processed on the Pi has to be sent to the backend over the network. The robot revolves 360deg, and has limited real-estate for a cable harness, so networking will be wifi (version to be confirmed).
 
 # Architecture

 TLDR; Containerised services that talk to each other.

 # Security
 If camera and audio processing happen on the backend, raw audio and video cross that link. The settings file's encrypt network traffic option (milestone 9) covers this.

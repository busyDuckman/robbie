# Architecture Decisions

Decisions are recorded here once they are agreed. Proposals that haven't been agreed yet live in the build plan. To reverse a decision, add a new entry that supersedes the old one rather than deleting it.

## ADR 1: Three layers: LLM, harness, robot control

Status: Accepted

Robbie is built in three layers:

- **A, the LLM.** Decides when to speak or take an action.
- **B, the harness.** State, behaviour, people present, attention target, mood, relationships, beeps and TTS. It also owns the camera, microphone and speakers.
- **C, robot control.** Drives the motors and reads the encoders. It also runs look_around and draws and displays the eyes.

This repo covers layers A and B. The boundary between B and C is described in the [interface document](interfaces/layer_b_c_interface.md).

## ADR 2: Layer C is a separate ROS 2 system

Status: Accepted

Layer C lives in its own repository and is built on ROS 2. Ideally, any robot can be connected in place of Robbie's own Layer C and become Robbie. B talks to C through a single ROS 2 bridge node, and the rest of B doesn't import ROS. Standard ROS 2 message types are used wherever possible, so another ROS 2 robot could be connected by remapping topics.


## ADR 3: Computation Backend Ram Usage

Status: Accepted

The backend for the system (layer A and parts of B too heave to run on a PI) will be docker containers and be operational for VRAM of 16Gb and RAM of 32GB.

## ADR 4: Development is done on Linux or WSL 2

Status: Accepted

Development is done on Linux, or on Windows inside WSL 2. Native Windows is not supported for development. On WSL 2, the repo should live in the WSL filesystem (for example under `/home`), not on a Windows drive under `/mnt/c`.

## ADR 5: The ROS 2 bridge node runs on the Pi

Status: Accepted

The ROS 2 bridge node (see ADR 2) is part of Layer B and is launched by B. It runs on the Pi.

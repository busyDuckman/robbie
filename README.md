# robbie
Open Source Agentic Robot.

This project will combine the different parts of robbie that have been built, as separate projects, into a whole. Some of these projects have not been made open-source, but the ones that have include:
  - 3D printable parts and assembly (https://github.com/busyDuckman/robbie_openscad)
  - Eye graphics rendering, other bits and pieces (https://github.com/busyDuckman/robbie_restoration).
  - Look around behaviour (https://github.com/busyDuckman/look_around)

The goal is to achieve a low cost agentic robot for interaction in group situations (stores, social events, meetings) and have it available under the MIT licence (the last part not easy).

New work for this repo:
  - **Robbie's personalty and agentic framework** is old (started when transformers were a novel thing) and predates modern established practices. This project will modernise that framework.

  - **Inverse-Kinematics and controller re-write.** (planned) The previous system used the camera to establish the system pose. That may sound ill-advised, but was something I wanted to try, just to push and see what was possible (it's my hobby project so I indulged my curiosity). That was abandoned, the new system puts a magnetic rotary sensor on each motor.

# Status

TRL 2, "technology concept formulated".


# Architecture  

Robbie is composed of 3 layers.

  - A) The LLM: Decides when to speak, or take an action.
  - B) The harness: State, behaviour, people present, attention target, mood, relationships. beeps, TTS. This layer is a collection of software components written in different languages. Manage mic, camera.
  - C) Robot Control: Drive motors, read sensors (encoders, home sw). ROS 2 based. Look-around, eye graphics.


This repo only covers layers A and B. Layer C is in a separate repo [TODO].
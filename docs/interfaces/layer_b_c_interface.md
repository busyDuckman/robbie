# Layer B to Layer C Interface

This **DRAFT** describes how the harness (Layer B) talks to robot control (Layer C, a separate repo). 

Layer C is a ROS 2 system. This document doesn't design Layer C. It covers the defined interface and specifies what still needs to be agreed.

## What lives on what side

Harness side (layer B):
  - camera, microphone, speakers
  - deciding where Robbie looks and how (attention, gaze style)
  - states that are behaviour related (mood, expression).

ROS side (layer C):
  - [look_around](https://github.com/busyDuckman/look_around)
  - motors and joint encoders
  - joint limits and safety, including the e-stop
  - eye drawing and the eye display

Because the camera, mic and speakers are on B's side, no camera or audio data crosses this interface.


## How they connect

B has a single ROS 2 bridge node. The rest of B doesn't import ROS. 
  - We should use standard ROS 2 message types wherever possible, so another ROS 2 robot could be connected by remapping topics.
  - Custom messages (such as gaze parameters and eye expression state) live in a `robbie_interfaces` ROS 2 package in this repo, so anyone with a robot can implement the interface and make it a Robbie.

## What B sends to C

A gaze target. This is a point to look at, or "neutral". C turns it into motion using [look_around](https://github.com/busyDuckman/look_around).

The target comes with a few expressive parameters, because how Robbie looks at things is part of its character, and that belongs in B. The parameters would primarily alter the expression used in the eyebrows, though could involve dilating pupils to show surprise. The exact set is to be agreed.

B also sends the expression state the eyes should show (e.g. mood, blinks, lid position).

Heartbeat signal, so C knows if B has stopped.

request to home the robot.

## What C sends to B

- The pose (position and orientation) of the camera, timestamped, in the same frame as gaze targets. B uses this to turn a detected face into a gaze target, without knowing the robot's joints or structure.
- Whether the current gaze target is reachable (look_around's `reachable()`). B's attention logic can then choose something else instead of straining towards it.
- Status, such as faults or the e-stop being engaged.
- Heartbeat signal, so B knows if C has stopped.

## What B relies on C to do

- Enforce its own joint limits and safety.
- Stop safely if B goes silent.

How C does these things is up to C.

## Testing without hardware

The fake Layer C in this repo uses the Python look_around library, so gaze behaves realistically in tests and simulation.

## Open questions

1. The set of expressive gaze parameters, and how they map onto look_around settings.
2. How the gaze target's coordinate frame is defined (e.g. relative to the robot's base or head).
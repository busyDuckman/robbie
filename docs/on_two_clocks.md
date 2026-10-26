# On Two Clocks

Status: Agreed on 2026-10-24.

The [B to C interface](interfaces/layer_b_c_interface.md) has C send B a timestamped camera pose.
The camera is on B's side and the pose comes from the Pi (C), so a timestamp from C is only meaningful if the two clocks are synced.

## Decision

- C sends the standard `PoseStamped`.
- B ignores C's stamp and uses the last known pose.
- If tracking during motion turns out to be visibly bad, B stamps each pose with its own clock on arrival, keeps a short history, and matches frames to poses. No clock sync is needed.

## Why

The timestamp only matters while the head is moving. Pairing a frame with a pose from a different moment puts the gaze target off by roughly turn speed times the age gap (e.g. 60 deg/s and 100 ms gives 6 degrees), and can make tracking overshoot or wobble.

That is unlikely to matter here:

- look_around moves in saccade-then-hold steps, so the head is still most of the time.
- B decides attention at a fairly slow rate. It is not a tight visual-servo loop.
- Ignoring face detections while the head is moving is a simple fix if needed.

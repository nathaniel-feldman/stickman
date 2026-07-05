# stickman

A minimalist artificial-life toy. A lone white stick figure lives on a pure black
canvas and reacts to the only thing in his world: your mouse cursor.

No sprites, no keyframes, no UI. Every pose is drawn procedurally each frame from a
physics-driven skeleton — steering forces move him, and the walk cycle, body lean,
and stumbles all fall out of his velocity and acceleration.

## Demo

- **Leave the cursor alone** and he wanders: slow meandering strolls, the occasional
  pause to stand and sway, breathing.
- **Bring the cursor close, slowly**, and he gets curious — approaching in cautious
  little bursts, stopping a polite distance away to stand and watch it, head
  tracking your every move.
- **Jerk the cursor at him** and he startles: a stumble, then a flat-out sprint away
  before he slows, turns, and eyes the cursor warily.
- Ignore him long enough and he loses interest and goes back to wandering.

## Running it

Requires Python 3.10+ and [pygame](https://www.pygame.org/).

```sh
pip install pygame
python stickman.py
```

A 900×600 window opens at 60 FPS. Close the window (or press Esc) to quit.

## How it works

- **Locomotion** is Reynolds-style steering: seek, flee, and wander forces with max
  speed / max force limits, plus a soft edge-avoidance force so he never leaves the
  window.
- **Animation** is derived entirely from physics state. Leg swing phase advances
  with distance traveled (not time), so stride visibly matches speed; arms
  counter-swing; the torso leans into acceleration; a spring recovers over-lean
  after a startle, which reads as a stumble.
- **Behavior** is a small state machine (wander / approach / watch / flee) driven by
  cursor distance and smoothed cursor speed, with steering forces blended over
  ~0.5 s on transitions so nothing snaps.

Everything lives in a single file, `stickman.py`, using pygame and the standard
library only. Tunable constants are grouped at the top of the file.

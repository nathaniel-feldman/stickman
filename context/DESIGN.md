# stickman — design vision and behavior spec

A single-file Python program (pygame) called `stickman.py`: a minimalist
artificial-life toy where a white stick figure on a pure black background reacts to
the user's mouse cursor.

## Visual style

- Pure black background (#000000), pure white lines (#FFFFFF), nothing else. No UI,
  no text, no cursor trail.
- The man is a procedurally drawn stick figure (~60px tall): head (circle outline),
  spine, two arms, two legs. Drawn with pygame lines/circles every frame from a
  skeleton model — no sprites, no images.
- Window 900x600, 60 FPS.

## Movement (the core of the project — most effort goes here)

- Physics-based locomotion: position, velocity, acceleration; moved by steering
  forces (Reynolds-style seek / flee / wander) with max speed and max force limits —
  smooth, never teleporting.
- Procedural walk cycle: legs swing with phase driven by distance traveled (not
  time), arms counter-swing. Idle = standing with subtle sway/breathing (slow sine
  bob of head and shoulders).
- Body lean: torso tilts into acceleration. Running = stronger lean, larger stride.
  Sudden flee = brief stumble (over-lean recovered by a spring).
- All animation driven by physics state. No canned keyframes.
- Soft edge-avoidance force near window bounds (turns away, never clips or bounces).

## Behavior (cursor reactions)

The cursor is the only stimulus. Track its position and smoothed speed (~10-frame
average).

- Cursor far (>250px): wander — an unhurried stroll that holds a heading (picked
  per walk segment, turned toward smoothly) with only gentle drift; occasional
  1–3s idle pauses. No Brownian back-and-forth pacing.
- Cursor newly near (<250px), moving slowly (<200 px/s): alert — freeze for
  ~0.5–1s, face it, recoil a half-step, size it up. Then the cautious approach in
  short bursts (move, pause, move), stopping ~50px away, standing and facing it,
  head tracking the cursor.
- Cursor fast (>700 px/s) within 300px: startle — flee at max speed with stumble,
  decelerate ~350px away, turn back to look warily.
- Cursor idle long enough for the curiosity arc to play out (~9s) while he's
  engaged: lose interest and stroll away from it (not pace beside it); he ignores
  it until it moves again.
- Blend steering forces over ~0.5s on state transitions — no snapping.

## Emotional expression

Two slow-moving internal scalars shape the whole body; all pose changes are
smoothly blended (~0.25s), never snapped.

- **Fear** (0–1): spikes to 1 on a startle, creeps up while a moderately fast
  cursor prowls nearby, decays over ~5s of calm. High fear = crouched stance,
  torso leaning away from the cursor, no reaching; it also blocks re-approaching
  until it has faded.
- **Curiosity** (0–1): builds over a few seconds of watching a calm cursor,
  collapses the moment the cursor moves. High curiosity = torso leaning in toward
  the cursor, head cocked side to side, and — when close and confident — the near
  hand slowly reaching out toward it.
- **Panic** (during flee): both arms come up beside the head, slight crouch,
  glancing back at the cursor mid-sprint.
- Alert stance: upright, leaning slightly away, locked gaze — "what is that?"

## Code structure

- One file, pygame + stdlib only.
- Classes: `Skeleton` (draws figure from physics state), `Man` (physics + steering +
  state machine), main loop.
- Tunable constants grouped at top. ~300–400 lines, commented where animation math
  is non-obvious.

## Definition of done

`python stickman.py` runs. He wanders naturally; slow nearby cursor → cautious
approach and watching; jerked cursor → stumble and flee. Never leaves the window,
never jitters, walk visibly matches speed.

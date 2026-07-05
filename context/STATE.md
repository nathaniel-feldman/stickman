# Current state

_Last updated: 2026-07-05_

## Status

v1 built, tested headlessly, committed, and pushed. `python stickman.py` runs the
full toy per DESIGN.md.

## What works

- Steering-force locomotion (wander / approach / watch / flee) with per-state max
  speed and max force; velocity is capped globally and zeroed below a threshold so
  he never jitters while standing.
- Distance-driven walk cycle: leg swing phase advances with px traveled, arms
  counter-swing, stride amplitude scales with speed, feet lift on the forward swing.
- Torso lean from smoothed acceleration + velocity; startle kicks an underdamped
  lean spring that reads as a stumble.
- Behavior state machine: wander with 1–3s pauses; cautious burst approach that
  settles ~50px from a slow nearby cursor and watches it (head tracks); startle →
  flee past 350px then turn back and watch; 5s cursor idle → lose interest.
- Soft edge avoidance (inward velocity bias inside a 90px margin) plus a hard
  safety clamp; headless chase tests never push him off screen.
- Transitions blend via ~0.5s exponential steering smoothing — no snapping.
- Wander holds a per-segment heading (smooth arcs, no Brownian back-and-forth);
  on losing interest he strolls away from the cursor and ignores it until it
  moves again — fixes the pacing-beside-a-still-cursor bug (user feedback).
- Emotion layer: fear (spikes on startle, creeps near a prowling cursor, ~3s
  half-life) and curiosity (builds while calmly watching, collapses on cursor
  motion) drive crouch, toward/away torso lean, side-to-side head cock, a
  reaching near hand (<110px, high curiosity), and arms-up guard during flee.
- ALERT state: on first noticing the cursor he recoils a half-step, freezes
  0.5–1.1s facing it, then starts the cautious approach. High fear blocks
  re-approaching from watch until it decays.

Verified with a headless harness (state transitions incl. alert, curiosity/
fear arcs, reach, bored walk-off, wander reversal rate, bounds, NaN checks)
and zoomed pose contact sheets; all pass/read correctly.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.

## What's broken

- Nothing known. The emotion layer is new and only verified headlessly — its
  feel (lean/crouch amounts, curiosity ramp speed, alert length) needs a live
  viewing pass.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Watch the emotion arc live (notice → alert → creep up → peer/reach → stroll
  off; jerk → panic flee) and feel-tune the emotion constants.
- Possible polish (would need a DECISIONS entry first): shadow dot under feet,
  window icon.

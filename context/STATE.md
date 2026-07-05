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

Verified with a headless harness (state transitions, stop distances, window
bounds, NaN checks) and rendered pose contact sheets; both pass/look correct.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.

## What's broken

- Nothing known. Not yet eyeballed in a live window (verified headlessly only), so
  feel-tuning (speeds, stumble strength, breathing amplitude) may want a pass after
  human viewing.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Watch it live and feel-tune constants (stride, lean, flee speed, pause pacing).
- Possible polish (would need a DECISIONS entry first): shadow dot under feet,
  window icon.

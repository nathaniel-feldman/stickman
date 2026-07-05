# Current state

_Last updated: 2026-07-05_

## Status

v1 complete. v2 (internal state & world interaction, DESIGN.md phases A–F) in
progress: **Phase A (debug bars) done**; **EMOTION PROTOCOL (continuous
valence-arousal) implemented**, awaiting playtest/feel-tuning before Phase B.
`python stickman.py` runs the full toy per DESIGN.md.

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
- EMOTION PROTOCOL: continuous valence (-1..1, ~30s half-life mood) +
  arousal (0..1, ~7s half-life weather) on `Man`, per DESIGN.md. Inputs:
  impulses (startle -0.4v/+0.6a; novelty on entering ALERT +0.1v/+0.3a;
  completed inspection — bored walk-off after curiosity peaked — +0.15v) and
  pressures (fast cursor prowling near drifts v down / a up; calm cursor near
  drifts v up gated by a smooth trust ramp — inert until Phase F). Outputs
  are pure modulation via four smooth corner weights (afraid/excited/
  content/dejected = ±v × a products, no branches): arousal scales all
  speeds/forces/step-rate/head-cock-rate; valence scales walk-bob bounce vs.
  slump (hunch lean, shoulder sag, shorter stride); afraid widens flee
  distance, lowers the startle threshold, lengthens hesitation, blocks
  re-approach; excited lengthens bursts and shrinks stop distance; content
  slows wandering, lengthens pauses, adds idle weight-shift; dejected shrinks
  the notice radius. Emotion never selects behaviors — flee still always wins.
- Old discrete fear scalar removed: "fear" is now the low-valence/high-arousal
  corner weight. Curiosity remains a drive; its gain rate scales with valence.
- Emotion pose layer (crouch, toward/away lean, head cock, reach <110px,
  arms-up guard in flee) unchanged, now driven by the afraid weight.
- ALERT state: on first noticing the cursor he recoils a half-step, freezes
  0.5–1.1s facing it, then starts the cautious approach.
- Debug overlay: D toggles it (default ON); live bars for speed, valence
  (centered fill: right = positive, left = negative, with a zero tick),
  arousal, curiosity, trust, plus a debug-only "mood:" region label
  (afraid/excited/content/dejected/neutral) below the bars. State text row
  removed and bar fills sit flush against their outlines (user request).
  Adding a bar = one (label, getter, centered) line in `DebugOverlay.bars`.

Verified with a headless harness: double-startle spikes arousal to 1.0 and it
decays below 0.45 within ~12s while valence stays low (-0.59) and recovers
by ~2min; speed gain 1.56 and startle threshold 454 px/s while afraid; a
gentle drifting cursor for 3 minutes lands him at valence +0.63 / arousal
0.33 = "content"; overlay + skeleton draw in all four mood corners; bounds
and NaN checks pass.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.

## What's broken

- Nothing known. The valence-arousal layer is only verified headlessly — the
  numbers hit the spec's definition of done, but the *feel* (slump depth,
  bounce, twitchiness, content sway) needs a live viewing pass.
- Contentment currently comes only from novelty/inspection impulses: the
  calm-company valence drift is gated behind trust >~0.5 and trust is still
  the 0.2 placeholder, so it does nothing until Phase F.
- Emotion inputs for systems that don't exist yet (energy, resting, erasure,
  trust milestones, enclosure) have constants defined but nothing wired;
  they land with phases C/D/E/F.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Playtest the emotion protocol live per its definition of done: startle him
  twice (watch arousal spike/decay and the twitchy-slumped window), then a
  gentle cursor for 3 minutes (watch him settle into content) — with the
  overlay on, then off.
- Then Phase B: head tracking (±60° clamped cursor gaze, body turn after 1s,
  wander glances — glance frequency already spec'd to scale with arousal).
- Possible polish (would need a DECISIONS entry first): shadow dot under feet,
  window icon.

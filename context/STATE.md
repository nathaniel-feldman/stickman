# Current state

_Last updated: 2026-07-06_

## Status

v1 complete. v2 Phase A (debug bars) done. The EMOTION PROTOCOL has been
superseded by the **Emotion & Behavior Architecture (v1.5)** (see DESIGN.md),
built in 6 phases: phases 1 (substrate + modulation, playtested "feels ok")
and 2 (full appraisal layer) done; **Phase 3 (prediction layer) done**,
awaiting playtest before Phase 4 (relationship ledger + soul.json).
`python stickman.py` runs the full toy.

## What works

- Steering-force locomotion (wander / approach / watch / flee) with per-state max
  speed and max force; velocity is capped globally and zeroed below a threshold so
  he never jitters while standing.
- Distance-driven walk cycle: leg swing phase advances with px traveled, arms
  counter-swing, stride amplitude scales with speed, feet lift on the forward swing.
- Torso lean from smoothed acceleration + velocity; startle kicks an underdamped
  lean spring that reads as a stumble.
- Behavior state machine: wander with pauses; ALERT freeze → cautious burst
  approach settling ~50px from a slow nearby cursor → watch (head tracks);
  startle → flee past 350px then turn back; 9s cursor idle → lose interest and
  stroll off. Soft edge avoidance + hard clamp; ~0.5s steering blend on
  transitions; wander holds a per-segment heading.
- **v1.5 Layer 1 — substrate**: valence (-1..1, 30s half-life mood) and arousal
  (0..1, 7s half-life weather) on `Man`, always decaying toward baseline
  (0 / 0.2). Only `_appraise` bumps them.
- **v1.5 Layer 2 — appraisal layer (full)**: one `APPRAISALS` table (event →
  need affected, Δvalence, Δarousal) applied through
  `_appraise(event, intensity, source)`; `source` is where Phase 4 will hook
  the relationship ledger. Wired events: startle (safety, -0.4v/+0.6a),
  calm company (social, +0.05v × trust per sustained 10s within 250px),
  novelty (curiosity, +0.1v/+0.3a — fires on first noticing the cursor until
  Phase D remaps it to drawn shapes), inspected (curiosity, +0.15v — fires on
  bored walk-off after curiosity passed 0.6). Declared but triggerless until
  their systems exist: erasure (Phase E), rest (Phase C), trapped (Phase D).
- **v1.5 Layer 5.1 — body modulation** (smooth functions, no thresholds):
  arousal scales all speeds/forces (`speed_gain`), step rate, and head-cock
  rate; valence sets posture — positive = upright with walk-bob bounce and
  bigger idle weight-shift sway and longer wander pauses; negative = hunch
  lean, shoulder sag, shorter stride. Named emotions exist only as the
  debug overlay's region label; `Man` has no afraid/excited/content/dejected
  fields anymore — pose weights are inline products of (valence, arousal).
- Emotion pose layer (crouch, toward/away lean, head cock, reach <110px,
  arms-up guard in flee) unchanged, wariness driven by the inline distress
  product max(0,-v)·a. That product < 0.15 also still blocks re-approach
  after a startle (v1 carryover until Phase 5 builds decision input).
- **v1.5 Layer 3 — prediction**: left-click-drag paints white onto a
  persistent `World` canvas (pulled forward from Phase D in minimal form —
  no obstacle force, no INSPECT yet) with a coarse 30×20 occupancy grid.
  `Man.memory` mirrors the grid; every frame, cells within 250px are
  compared: matches drift him toward comfort (+0.007 valence/s at a fully
  familiar view → equilibrium ≈ +0.3, arousal −0.008/s), mismatches fire a
  "surprise" appraisal (intensity = mismatch size) and then memory accepts
  reality. Rolling world volatility (half-life 120s, +0.35 per unit
  mismatch, spawn 0.15) sets the arousal DECAY TARGET:
  aro_base = 0.2 + 0.5·(vol − 0.15), clamped [0.08, 0.5] (dampener).
  Modulation stays centered on the neutral 0.2 constant, so a secure world
  reads as genuinely languid and a chaotic one as ambient anxiety.
- Debug overlay: D toggles; bars for speed, valence (centered fill + zero
  tick), arousal, curious, trust, volatile; "mood:" region label below, plus
  a transient "event:" line naming the last appraisal (event, need, source)
  for 3s after it fires. The cursor_valence bar lands with Phase 4.

Verified with a headless harness (2026-07-06): Phase 1 — double startle →
valence -0.79 / arousal 0.99 / speed gain 1.55; arousal 0.44 at +12s; valence
recovers on the 30s half-life; four mood-corner renders; bounds hold under 60s
of chase; no NaNs. Phase 2 — novelty on alert moved v/a +0.10/+0.30 per table;
a full look then bored walk-off fired inspected (+0.15v); startle and calm
company fire with correct deltas; the three triggerless hooks apply exact
table deltas when called; overlay renders the event line. Phase 3 — 3 min of
unchanged world: valence +0.30 / arousal 0.07 / aro_base 0.15 = content; a
blob painted in view spiked arousal 0.07→0.61 via surprise and stopped
surprising once remembered; 90s of constant repainting pinned volatility
(arousal 0.95, aro_base capped at 0.5); 4 min of stillness recovered him to
content (volatility 0.25, arousal 0.18); startle/bounds/overlay regressions
pass.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.
- Substrate half-lives 30s/7s (spec ranges 20–40s / 5–10s).

## What's broken

- Nothing known. Phase 3 is verified headlessly; needs the live playtest
  (settling in a still world, edginess in a redecorated one) before Phase 4.
- Calm company is nearly invisible until Phase 4 makes trust real (0.05 ×
  trust 0.2 = +0.01 per 10s window).
- Painting is watch-only: he sees and remembers drawn shapes but does not
  avoid or inspect them (that's Phase D of the v2 arc). Drawn pixels are
  also not erasable yet (Phase E).
- Emotion→decision effects from the old protocol (hair-trigger spook when
  afraid, wider flee distance, longer hesitation, excited burst/stop-distance
  changes, dejected notice radius, curiosity-gain valence coupling) were
  REMOVED in Phase 1 — they are Layer 5.2 and return properly in Phase 5.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Playtest Phase 3 per its done-when: leaving the world unchanged for 3 min
  visibly settles him; repeatedly changing it keeps him on edge.
- On confirmation: Phase 4 — relationship ledger (cursor_valence + standing
  bias + proximity effects), soul.json persistence, sensitivity drift, and
  the scripted 20-startle dampener test.
- Then phases 5–6 (decision input, perception gating).

# Current state

_Last updated: 2026-07-06_

## Status

v1 complete. v2 Phase A (debug bars) done. The EMOTION PROTOCOL has been
superseded by the **Emotion & Behavior Architecture (v1.5)** (see DESIGN.md),
built in 6 phases: phases 1 (substrate + modulation, playtested "feels ok"),
2 (full appraisal layer), 3 (prediction layer), and **4 (relationship
ledger + soul.json persistence) done** — phases 3+4 shipped together on
user instruction ("move onto phase 4 without waiting"), so both await
playtest before Phase 5 (decision input).
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
- **v1.5 Layer 4 — relationship ledger + persistence**: `trust` is live
  (drops 0.08 per startle, floor 0.05; rises 0.015 per calm-company
  window) and `cursor_valence` (-0.7 floor .. +1) accumulates from every
  cursor-sourced appraisal at 0.25× its valence delta. Effects: while he's
  aware of the cursor (≤250px or engaged) his valence decay target shifts
  by 0.25·cursor_valence (standing bias); smooth dread/warmth ramps past
  the -0.3/+0.4 edges make proximity itself unnerving (drift -0.02v/+0.05a
  per s) or comforting (+0.02v per s), and dread widens his watch/stop
  distance up to 2.2×. Sensitivity drift: each startle +0.02 startle
  sensitivity (cap 1.5 = +50%), amplifying future startle appraisals.
  Dampeners: floors everywhere, and uneventful time (>15s since any event)
  heals negative cursor_valence at 0.001/s and excess sensitivity at
  0.00006/s — trauma recovers, jumpiness lingers across sessions.
  `soul.json` (gitignored, next to stickman.py) persists trust,
  cursor_valence, volatility, sensitivities, and lifetime startle/comfort
  counts; loaded on start (clamped to floors/caps), saved on exit + every
  60s. Deleting it is a full rebirth. `test_dampeners.py` (committed) is
  the mandated 20-startle verification.
- Debug overlay: a strip across the top of the screen (user request), one
  column per parameter — valence (centered), arousal (with a tick at its
  volatility-set decay target), cursor_valence (centered), volatile, trust,
  curious, speed — plus a "mood:" region label and transient "event:" line
  underneath. D toggles; all white.

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
pass. Phase 4 (`test_dampeners.py`, rerunnable) — 20 startles: trust sits
exactly on its 0.05 floor, cursor_valence on -0.7, sensitivity 1.40, valence
-0.78 (not pinned); the jumpy man's startle hits 1.4× a fresh one's; 5 min of
calm heals mood to content and cursor_valence to -0.41 while jumpiness stays
1.38; soul round-trips through save/load and deleting it births identical
defaults; dread holds his watch distance at 66px vs the 50px base; the
wander→alert→approach→watch chain and overlay strip still work.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.
- Substrate half-lives 30s/7s (spec ranges 20–40s / 5–10s).

## What's broken

- Nothing known. Phases 3 and 4 are verified headlessly; both need the live
  playtest pass.
- Painting is watch-only: he sees and remembers drawn shapes but does not
  avoid or inspect them (that's Phase D of the v2 arc). Drawn pixels are
  also not erasable yet (Phase E).
- "Seeks proximity when lonely" (the warm-cursor ledger effect) is deferred
  to Phase 5 — it needs the utility layer and a social meter; the comfort
  drift when near a loved cursor is in.
- Emotion→decision effects from the old protocol (hair-trigger spook when
  afraid, wider flee distance, longer hesitation, excited burst/stop-distance
  changes, dejected notice radius, curiosity-gain valence coupling) were
  REMOVED in Phase 1 — they are Layer 5.2 and return properly in Phase 5.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Playtest phases 3+4: still world settles him / changing world keeps him on
  edge; abuse across a restart carries over via soul.json (jumpier, more
  distant), gentleness slowly warms him; deleting soul.json rebirths him.
- On confirmation: Phase 5 — decision input (valence/arousal/cursor_valence
  terms in behavior utility scores; approach willingness, flee sensitivity,
  rest readiness, inspect drive; the same slow cursor approached by a
  content creature, avoided by a distressed one).
- Then Phase 6 (perception gating, last: view distance + novelty threshold
  with caps, the no-permanent-spiral test).

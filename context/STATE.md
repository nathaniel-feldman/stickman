# Current state

_Last updated: 2026-07-06_

## Status

v1 complete. v2 Phase A (debug bars) done. The EMOTION PROTOCOL has been
superseded by the **Emotion & Behavior Architecture (v1.5)** (see DESIGN.md),
built in 6 phases: Phase 1 (substrate + body modulation) done and playtested
("feels ok"); **Phase 2 (full appraisal layer) done**, awaiting playtest
before Phase 3 (prediction layer / memory grid).
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
- Debug overlay: D toggles; bars for speed, valence (centered fill + zero
  tick), arousal, curious, trust; "mood:" region label below, plus a
  transient "event:" line naming the last appraisal (event, need, source)
  for 3s after it fires. cursor_valence and volatility bars land with
  phases 4 and 3.

Verified with a headless harness (2026-07-06): Phase 1 — double startle →
valence -0.79 / arousal 0.99 / speed gain 1.55; arousal 0.44 at +12s; valence
recovers on the 30s half-life; four mood-corner renders; bounds hold under 60s
of chase; no NaNs. Phase 2 — novelty on alert moved v/a +0.10/+0.30 per table;
a full look then bored walk-off fired inspected (+0.15v); startle and calm
company fire with correct deltas; the three triggerless hooks apply exact
table deltas when called; overlay renders the event line.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.
- Substrate half-lives 30s/7s (spec ranges 20–40s / 5–10s).

## What's broken

- Nothing known. Phase 2 is verified headlessly; needs the live playtest
  (watch the event line + bars as each event fires) before Phase 3.
- Calm company is nearly invisible until Phase 4 makes trust real (0.05 ×
  trust 0.2 = +0.01 per 10s window).
- Emotion→decision effects from the old protocol (hair-trigger spook when
  afraid, wider flee distance, longer hesitation, excited burst/stop-distance
  changes, dejected notice radius, curiosity-gain valence coupling) were
  REMOVED in Phase 1 — they are Layer 5.2 and return properly in Phase 5.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Playtest Phase 2 per its done-when: distinct events visibly move the bars
  per the table (watch the transient "event:" line in the overlay).
- On confirmation: Phase 3 — prediction layer: coarse seen-grid (built now,
  drawing input comes with Phase D), match→comfort / mismatch→surprise,
  rolling world volatility coupling to the arousal baseline.
- Then phases 4–6 per DESIGN.md v1.5 (ledger + soul.json, decision input,
  perception gating).

# Current state

_Last updated: 2026-07-06_

## Status

v1 complete. v2 Phase A (debug bars) done. The EMOTION PROTOCOL has been
superseded by the **Emotion & Behavior Architecture (v1.5)** (see DESIGN.md),
built in 6 phases: **Phase 1 (substrate + body modulation) done**, awaiting
playtest confirmation before Phase 2 (full appraisal layer).
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
- **v1.5 Layer 2 — appraisals (Phase 1 subset)**: the full appraisal table
  lives as `APR_*` constants; wired now are ONLY startle (fast cursor →
  -0.4v/+0.6a) and calm company (calm cursor within 250px sustained 10s →
  +0.05v × trust per window; trust is still the 0.2 placeholder, so ~+0.01
  per window — small but active). Inspection/novelty/erasure/rest/trapped
  constants exist unwired (Phase 2+).
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
  tick), arousal, curious, trust; "mood:" region label below. cursor_valence
  and volatility bars land with phases 4 and 3.

Verified with a headless harness (2026-07-06): double startle → valence -0.79 /
arousal 0.99 / speed gain 1.55; arousal 0.44 at +12s; valence recovers on the
30s half-life (-0.60 → -0.30 over 30s); 35s of calm proximity fires the calm
company appraisal; skeleton + overlay draw in all four mood corners; bounds
hold under 60s of chase; no NaNs.

## What's tuned

- Approach stops ~50–70px from the cursor.
- Wander heading jitter lowered (2.6 → 1.7) so strolls reach cruise stride.
- Head seated 1px closer to the neck; top-edge clamp raised so the head can't
  touch y=0.
- Substrate half-lives 30s/7s (spec ranges 20–40s / 5–10s).

## What's broken

- Nothing known. Phase 1 is verified headlessly; the *feel* (twitchy window
  after a double startle, slump depth, recovery arc readable with the overlay
  off) needs the live playtest before Phase 2.
- Calm company is nearly invisible until Phase 4 makes trust real (0.05 ×
  trust 0.2 = +0.01 per 10s window).
- Emotion→decision effects from the old protocol (hair-trigger spook when
  afraid, wider flee distance, longer hesitation, excited burst/stop-distance
  changes, dejected notice radius, curiosity-gain valence coupling) were
  REMOVED in Phase 1 — they are Layer 5.2 and return properly in Phase 5.
- Machine oddity, not app: root-level .md files were deleted from disk twice by
  something outside git during setup (restored from git). Watch for recurrence.

## What's next

- Playtest Phase 1 per its done-when: startle him twice → visibly twitchy,
  slumped movement recovering over ~30s, readable with the overlay OFF.
- On confirmation: Phase 2 — appraisal event system ({source, need,
  intensity, deltas}) + wire the remaining events that exist today.
- Then phases 3–6 per DESIGN.md v1.5 (prediction, ledger + soul.json,
  decision input, perception gating).

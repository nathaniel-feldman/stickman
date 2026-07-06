# Decisions log

Running log of design/technical decisions. Newest at the bottom. Format:
`YYYY-MM-DD — decision — one-line rationale`.

- 2026-07-05 — Single-file app (`stickman.py`), pygame + stdlib only — spec
  requirement; keeps the toy trivially runnable and readable.
- 2026-07-05 — Walk cycle phase advances with distance traveled, not time — makes
  stride visibly match speed for free and eliminates foot-sliding.
- 2026-07-05 — Behavior transitions blended by passing the steering force through
  an exponential smoother (~0.5s settle) instead of per-state weight ramps —
  simpler, one mechanism smooths both state changes and burst stop/start.
- 2026-07-05 — Behaviors expressed as desired velocities (steer = desired − vel,
  force-limited) — deceleration after a flee and braking to watch fall out for
  free instead of needing special cases.
- 2026-07-05 — Edge avoidance implemented as an inward velocity bias added to the
  desired velocity (ramping quadratically inside a 90px margin), plus a hard
  safety clamp — turns him along walls instead of bouncing; clamp is a last resort.
- 2026-07-05 — Stumble modeled as an underdamped spring on extra torso lean,
  kicked on startle — one wobble then recovery, no keyframes.
- 2026-07-05 — Verified headlessly (SDL dummy driver): scripted-cursor state
  machine tests + rendered pose contact sheets — no display needed for CI-style
  checks.
- 2026-07-05 — Wander heading changed from Brownian jitter to a per-segment
  target heading turned toward smoothly — pure noise reversed direction every few
  seconds and read as unnatural back-and-forth pacing (user feedback).
- 2026-07-05 — On losing interest the first wander heading points away from the
  cursor, and boredom suppresses re-alerting until the cursor moves — a human
  walks off from a thing he's done with instead of pacing beside it.
- 2026-07-05 — Added an emotion layer (fear + curiosity scalars → crouch, lean,
  head-cock, reach, arms-up) and an ALERT freeze state before approaching —
  user feedback: limbs and head should express wariness then curiosity like a
  human meeting an unknown object. DESIGN.md updated with the spec.
- 2026-07-05 — LOSE_INTEREST_S raised 5s → 9s — the curiosity arc (alert →
  approach → watch → lean in → reach) needs the time to play out before boredom.
- 2026-07-05 — v2 arc (phases A–F: debug bars, head tracking, drives, drawing/
  novelty, erasure, trust/personality) added to DESIGN.md — user spec; built one
  phase at a time with a playtest checkpoint between phases.
- 2026-07-05 — Debug overlay exempt from the "no UI, no text" rule while
  toggled on (D key, default ON during development) — it's the tuning
  instrument for every later phase; with it off the screen stays pure creature.
- 2026-07-05 — Overlay bars defined as a list of (label, getter) pairs on
  `DebugOverlay` — each later phase adds its meter as one line.
- 2026-07-05 — `Man.trust` added now as a constant 0.2 placeholder — Phase A
  spec wants trust in the code structure/overlay before Phase F drives it.
- 2026-07-05 — EMOTION PROTOCOL added to DESIGN.md and implemented: emotion is
  a continuous valence-arousal point, not a state machine — user spec; the
  discrete fear scalar "made no sense" and is replaced by the low-valence/
  high-arousal corner weight.
- 2026-07-05 — Emotion modulates via four smooth corner-weight products
  (afraid/excited/content/dejected = max(0,±v)·a or ·(1-a)) — spec forbids
  hard-edged if/else regions; products give continuous blending for free.
- 2026-07-05 — Spec impulses mapped to today's only stimulus, the cursor:
  entering ALERT = "novelty detected"; walking off bored after curiosity
  peaked (>0.6) = "completed an inspection" — Phase D will remap these to
  drawn shapes without changing the emotion code.
- 2026-07-05 — Old FEAR_CREEP replaced by a P_PROWL pressure (fast cursor
  nearby drifts valence down, arousal up) — preserves the v1 "prowling cursor
  unnerves him" behavior inside the new model.
- 2026-07-05 — Calm-company trust gate implemented as a smooth ramp
  (trust 0.4→0.7) instead of a hard >0.5 test — keeps inputs as edge-free as
  outputs; inert until Phase F since trust is still the 0.2 placeholder.
- 2026-07-05 — Emotion constants for not-yet-built systems (energy, resting,
  erasure, trust milestone, enclosure) declared now, wired in phases C–F —
  keeps the whole protocol's tuning surface in one block at the top.
- 2026-07-05 — Overlay: behavior-state text row removed and bar fills drawn
  flush against their 1px outlines — user request; valence gets a centered
  bar with a zero tick, and a debug-only "mood:" region label sits below the
  bars (the creature's code never reads it).
- 2026-07-06 — "Emotion & Behavior Architecture (v1.5)" added to DESIGN.md,
  superseding the EMOTION PROTOCOL's input wiring — user-designed layered
  stack (prediction → appraisal → substrate → outputs), built in 6 phases
  with a playtest stop after each; the valence-arousal substrate and body
  modulation carry forward.
- 2026-07-06 — Phase 1 removed the emotion→decision couplings (afraid spook/
  flee/hesitate bends, excited burst/stop-distance, dejected notice radius,
  curiosity-gain valence coupling) — they are Layer 5.2 decision input and
  are rebuilt properly in Phase 5; Phase 1 is body modulation only.
- 2026-07-06 — Kept fear blocking re-approach (inline distress product
  max(0,-v)·a < 0.15) as a v1-behavior carryover — without it he'd walk right
  back up to the thing he just fled; Phase 5 replaces it with a utility term.
- 2026-07-06 — P_PROWL pressure dropped — not in the v1.5 appraisal table;
  fast-cursor threat is the startle appraisal, and ambient unease in an
  unstable world returns as Phase 3 volatility.
- 2026-07-06 — Named corner-weight fields (afraid/excited/content/dejected)
  removed from `Man` — v1.5 mandates named emotions exist ONLY as debug
  labels; modulation reads valence/arousal directly via inline smooth
  products.
- 2026-07-06 — Calm company changed from a continuous trust-gated drift to a
  discrete appraisal per 10s of sustained calm proximity, scaled by trust —
  matches the v1.5 appraisal table; active now (tiny) with the 0.2 trust
  placeholder instead of inert.
- 2026-07-06 — Phase 2: appraisal table unified into one APPRAISALS dict
  (event → need, Δv, Δa) applied via _appraise(event, intensity, source) —
  the full Layer 2 event shape now, so Phase 4 can route cursor-sourced
  events into the relationship ledger without touching any call site.
- 2026-07-06 — Novelty/inspected stay mapped to cursor events (entering
  ALERT; bored walk-off after curiosity >0.6) until Phase D gives him drawn
  shapes to notice — carries the earlier EMOTION PROTOCOL mapping into v1.5.
- 2026-07-06 — Debug overlay gains a transient "event:" line naming the last
  appraisal (event, need, source) for 3s — Phase 2's done-when is per-event
  bar movement, and the label makes each appraisal attributable at a glance.
- 2026-07-06 — Phase 3 pulls minimal left-drag painting forward from Phase D
  (persistent canvas + coarse occupancy only; NO obstacle force, NO inspect
  behavior) — the prediction layer's done-when requires a world the user can
  actually change; the rest of Phase D lands on schedule.
- 2026-07-06 — Surprise is its own APPRAISALS entry ("prediction" need,
  0v/+0.6a, intensity = viewed mismatch, capped 1) — keeps every substrate
  write flowing through the Layer 2 table.
- 2026-07-06 — Table "novelty" stays mapped to cursor encounters for now —
  a drawn shape's discovery already spikes arousal via surprise; the
  valence-positive novelty appraisal moves to shapes with Phase D's INSPECT.
- 2026-07-06 — Volatility shifts only the arousal DECAY TARGET
  (aro_base = 0.2 + 0.5·(vol − 0.15), clamped [0.08, 0.5]); modulation stays
  centered on the neutral 0.2 constant — security reads as a genuinely
  lower-energy body, and the clamp is the mandated dampener.
- 2026-07-06 — Comfort drift tuned to a visible equilibrium (+0.007
  valence/s at a fully familiar view ≈ +0.3 after minutes) — makes "an
  unchanged world settles him" observable, not homeopathic.
- 2026-07-06 — Cell occupancy is an incremental per-dab estimate (+0.03,
  capped 1), not a pixel recount — coarse is fine for a 30×20 memory and
  keeps painting O(dabs).
- 2026-07-06 — Debug overlay relaid as a strip across the top of the screen
  (one column per emotional parameter, name above bar, all white; arousal
  bar carries a tick at its volatility-set decay target) — user request:
  a real-time physical representation of all emotional parameters at the
  top of the screen. Bars remain one (label, getter, centered, tick) line.
- 2026-07-06 — Phase 4 makes trust LIVE (−0.08 per startle, +0.015 per
  calm-company window) instead of waiting for Phase F — v1.5 folds trust
  into the ledger and mandates its 0.05 floor, which implies movement;
  Phase F keeps only the behavioral consequences (closer stops, FOLLOW).
- 2026-07-06 — Standing bias implemented by shifting the valence DECAY
  TARGET (VAL_BASE + 0.25·cursor_valence while aware of the cursor) — the
  same mechanism volatility uses for arousal; a bias that decay can't erase,
  with no extra pressure term to balance.
- 2026-07-06 — The ledger's -0.3/+0.4 effect edges are smooth 0.4-wide
  ramps (dread/warmth), per the project's no-hard-edges precedent; dread
  widens stop distance up to 2.2× ("keeps distance, watches warily").
- 2026-07-06 — "Seeks proximity when lonely/low social" deferred to Phase 5
  — it's a utility-layer behavior and no social meter exists yet.
- 2026-07-06 — test_dampeners.py committed as a permanent harness (backs up
  any real soul.json) — the phase mandates the scripted 20-startle
  verification; keeping it rerunnable guards phases 5–6 against spirals.
- 2026-07-06 — CV_HEAL cut 0.003 → 0.001 after the test showed dread fully
  healing in 5 idle minutes — recovery must read across sessions, not
  minutes (spec); now ~12 min of uneventful time from floor to neutral.
- 2026-07-06 — load_soul clamps every field to its floor/cap — a
  hand-edited soul.json must not be able to bypass the dampeners.

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

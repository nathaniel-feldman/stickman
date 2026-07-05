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

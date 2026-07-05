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

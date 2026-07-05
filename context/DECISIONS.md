# Decisions log

Running log of design/technical decisions. Newest at the bottom. Format:
`YYYY-MM-DD — decision — one-line rationale`.

- 2026-07-05 — Single-file app (`stickman.py`), pygame + stdlib only — spec
  requirement; keeps the toy trivially runnable and readable.
- 2026-07-05 — Walk cycle phase advances with distance traveled, not time — makes
  stride visibly match speed for free and eliminates foot-sliding.
- 2026-07-05 — Behavior states blended via per-state weight ramps (~0.5s) rather
  than hard switches — spec requires no snapping on transitions.

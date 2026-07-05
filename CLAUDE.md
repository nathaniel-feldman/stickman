# stickman — project instructions

A minimalist artificial-life toy in Python/pygame: a white stick figure on a black
background reacting to the mouse cursor. Single app file: `stickman.py`.

## Context files

- `context/DESIGN.md` — design vision and behavior spec. This is the source of truth
  for what the toy should do.
- `context/DECISIONS.md` — running log of design/technical decisions (date + one-line
  rationale each).
- `context/STATE.md` — current status: what works, what's tuned, what's broken,
  what's next.

## Standing rules

1. After every meaningful change, update `context/STATE.md`, and append to
   `context/DECISIONS.md` if a decision was made.
2. Commit after each working milestone with a descriptive message, and push to
   origin.
3. Never add features not in `context/DESIGN.md` without logging them as a decision
   first.
4. Constants live at the top of `stickman.py`; tuning changes get committed
   separately from features.

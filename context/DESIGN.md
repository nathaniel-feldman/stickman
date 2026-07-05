# stickman — design vision and behavior spec

A single-file Python program (pygame) called `stickman.py`: a minimalist
artificial-life toy where a white stick figure on a pure black background reacts to
the user's mouse cursor.

## Visual style

- Pure black background (#000000), pure white lines (#FFFFFF), nothing else. No UI,
  no text, no cursor trail.
- The man is a procedurally drawn stick figure (~60px tall): head (circle outline),
  spine, two arms, two legs. Drawn with pygame lines/circles every frame from a
  skeleton model — no sprites, no images.
- Window 900x600, 60 FPS.

## Movement (the core of the project — most effort goes here)

- Physics-based locomotion: position, velocity, acceleration; moved by steering
  forces (Reynolds-style seek / flee / wander) with max speed and max force limits —
  smooth, never teleporting.
- Procedural walk cycle: legs swing with phase driven by distance traveled (not
  time), arms counter-swing. Idle = standing with subtle sway/breathing (slow sine
  bob of head and shoulders).
- Body lean: torso tilts into acceleration. Running = stronger lean, larger stride.
  Sudden flee = brief stumble (over-lean recovered by a spring).
- All animation driven by physics state. No canned keyframes.
- Soft edge-avoidance force near window bounds (turns away, never clips or bounces).

## Behavior (cursor reactions)

The cursor is the only stimulus. Track its position and smoothed speed (~10-frame
average).

- Cursor far (>250px): wander — an unhurried stroll that holds a heading (picked
  per walk segment, turned toward smoothly) with only gentle drift; occasional
  1–3s idle pauses. No Brownian back-and-forth pacing.
- Cursor newly near (<250px), moving slowly (<200 px/s): alert — freeze for
  ~0.5–1s, face it, recoil a half-step, size it up. Then the cautious approach in
  short bursts (move, pause, move), stopping ~50px away, standing and facing it,
  head tracking the cursor.
- Cursor fast (>700 px/s) within 300px: startle — flee at max speed with stumble,
  decelerate ~350px away, turn back to look warily.
- Cursor idle long enough for the curiosity arc to play out (~9s) while he's
  engaged: lose interest and stroll away from it (not pace beside it); he ignores
  it until it moves again.
- Blend steering forces over ~0.5s on state transitions — no snapping.

## Emotional expression

Two slow-moving internal scalars shape the whole body; all pose changes are
smoothly blended (~0.25s), never snapped.

- **Fear** (0–1): spikes to 1 on a startle, creeps up while a moderately fast
  cursor prowls nearby, decays over ~5s of calm. High fear = crouched stance,
  torso leaning away from the cursor, no reaching; it also blocks re-approaching
  until it has faded.
- **Curiosity** (0–1): builds over a few seconds of watching a calm cursor,
  collapses the moment the cursor moves. High curiosity = torso leaning in toward
  the cursor, head cocked side to side, and — when close and confident — the near
  hand slowly reaching out toward it.
- **Panic** (during flee): both arms come up beside the head, slight crouch,
  glancing back at the cursor mid-sprint.
- Alert stance: upright, leaning slightly away, locked gaze — "what is that?"

## Code structure

- One file, pygame + stdlib only.
- Classes: `Skeleton` (draws figure from physics state), `Man` (physics + steering +
  state machine), main loop.
- Tunable constants grouped at top. ~300–400 lines, commented where animation math
  is non-obvious.

## Definition of done (v1)

`python stickman.py` runs. He wanders naturally; slow nearby cursor → cautious
approach and watching; jerked cursor → stumble and flee. Never leaves the window,
never jitters, walk visibly matches speed.

---

# v2 — internal state & world interaction

Built in phases, one at a time; each phase ends with a playtest checkpoint before
the next begins. New tunable constants stay grouped at the top of `stickman.py`.
The existing wander/flee/approach behaviors must never break; any intentional
change to their feel gets a DECISIONS entry.

## Phase A: Debug bars

A debug overlay at the top-left, toggled with the D key (default ON during
development; the "no UI, no text" rule applies only when the overlay is off).

- One horizontal bar per internal property, stacked top-left. Each bar: a white
  1px rectangle outline (~120px wide, 10px tall) with a white fill proportional
  to the value (0–1), property name in small white text to its left. White on
  black only — no color, no styling.
- Bars update live every frame.
- Initial rows: current behavior state (as text, not a bar), speed (normalized
  to max speed), fear, curiosity, and trust (a constant placeholder until
  Phase F wires it up).
- Architecture: a list of (label, getter) pairs — adding a bar is one line.

## Phase B: Head tracking

- While standing/watching: head orients toward the cursor, clamped to ±60° from
  body facing (never owl-neck), rotation smoothed by lerp, never snapped.
- If the cursor stays outside the clamp range for >1s, he turns his body to
  face it instead.
- While wandering: occasional brief glances (1–2s) at a cursor within ~350px,
  then gaze returns to his heading.

## Phase C: Drives — energy and curiosity

Two internal meters, 0–1, shown in the debug bars.

- ENERGY: decays slowly while moving (faster when fleeing), recovers while
  idle. Low energy → slower max speed, shorter approach bursts, longer idle
  pauses. Below ~0.15 → he sits down (legs folded) and rests until energy
  passes ~0.5. Fleeing overrides sitting (fear beats fatigue) but costs extra.
- CURIOSITY: rises slowly over time and on novel events; satisfied by
  approaching/watching the cursor. High → longer watches, closer stops;
  low → he ignores a slow cursor entirely and keeps wandering.
- Rates tuned so state changes are observable within 1–3 minutes of play.
- Behavior selection becomes utility-based: each behavior (wander, approach,
  watch, rest, flee) scores from drives + stimuli; highest wins; flee always
  wins when triggered. Transitions blend over ~0.5s as before.

## Phase D: Drawing + novelty response

- Left-click-drag paints white pixels onto a persistent world canvas (brush
  ~4px). White pixels are solid: steering avoids walking through them
  (obstacle-avoidance force).
- Coarse memory grid (~30x20 cells) of what he has SEEN per cell; only cells
  within ~250px line-of-sight update.
- Novelty: a seen cell differing from memory spikes novelty → curiosity jumps →
  INSPECT behavior: approach the novel region, walk along/around the shape,
  head tracking it, duration scaled by curiosity. Then habituation: novelty
  decays, he wanders off and ignores it.
- NOVELTY bar added to the debug overlay.

## Phase E: Erasure reaction

- Right-click-drag erases pixels.
- If a habituated region (remembered as occupied) is empty when he sees it:
  SEARCH — go to where the shape was, short back-and-forth walks with head
  scanning for 5–10s, then give up, update memory, resume wandering.

## Phase F: Trust and personality

- TRUST: 0–1, starts ~0.2, in the debug bars. Rises slowly during calm
  proximity; drops sharply on each startle. Stopping distance shrinks ~50px
  (low) → ~15px (high); approach hesitation shortens; above ~0.8 he FOLLOWS a
  slowly moving cursor, trailing at a distance.
- PERSONALITY: at spawn, randomize ±30% around defaults — boldness (flee
  threshold, stopping distance), curiosity gain rate, energy decay rate, base
  speed. Rolled values printed to console on start.

## Definition of done (v2)

With debug bars on, internal state visibly drives behavior: he rests when
tired, ignores the cursor when incurious, inspects what the user draws,
searches for what they erase, and warms up to a gentle cursor over minutes.
With bars off (D), the screen is pure creature — black, white, alive.

---

# EMOTION PROTOCOL — continuous valence-arousal

Supersedes the v1 "Emotional expression" fear scalar: fear is no longer a
stored variable but the low-valence/high-arousal region of a continuous 2D
emotional state. Curiosity remains a separate drive (Phase C); its gain rate
now couples to valence (below).

## Core model: valence-arousal (no emotion state machine)

Emotion is NOT a discrete state. A continuous 2D emotional state:

- valence: -1 (distressed) to +1 (content), baseline 0
- arousal: 0 (calm) to 1 (activated), baseline ~0.2

Both are float fields on Man, updated every frame, moving toward baseline
with slow decay (half-life ~20–40s for valence, ~5–10s for arousal — arousal
is fast weather, valence is slow mood).

## Inputs (event-driven impulses + continuous pressures)

Impulses (instant bumps when events occur):

- Startle/flee trigger: arousal +0.6, valence -0.4
- Novelty detected: arousal +0.3, valence +0.1
- Completed an inspection (habituated successfully): valence +0.15
- Erasure discovered (searched, found nothing): valence -0.2, arousal +0.2
- Trust milestone crossed upward: valence +0.2

Continuous pressures (per-second drift while condition holds):

- Energy < 0.25: valence drifts down
- Resting successfully: valence drifts up, arousal drifts down
- Calm cursor nearby with trust > 0.5: valence drifts up slightly
- Enclosed/trapped (when Phase D obstacle data allows detection): arousal
  drifts up, valence drifts down

All impulse magnitudes and drift rates are named constants at the top of the
file. Inputs whose systems don't exist yet (energy, resting, erasure, trust
milestones, enclosure) get their constants now and are wired when their
phase (C/D/E/F) lands.

## Outputs: emotion modulates, never selects

Emotion must NOT directly choose behaviors (drives + stimuli still do that,
flee still always wins). Instead it modulates parameters continuously:

- Arousal → movement gain: max speed and max force scale up with arousal
  (calm = languid, activated = twitchy). Walk stride frequency and
  head-glance frequency scale with arousal.
- Valence → posture: torso lean/slump. Positive = upright, slight bounce in
  the walk (amplitude of the walk bob). Negative = slumped shoulders,
  lowered head default angle, shorter stride.
- Low valence + high arousal (fear region): stronger flee distances, larger
  startle threshold sensitivity (easier to spook), hesitation pauses
  lengthen.
- High valence + high arousal (excitement region): approach bursts get
  longer and bouncier, stopping distance shrinks slightly.
- High valence + low arousal (content region): slow wandering with longer
  idle pauses, occasional small idle animations (weight shift).
- Low valence + low arousal (dejected region): slowest movement, ignores
  mild novelty (novelty threshold rises), sits more readily (once Phase C
  adds sitting).

Implement these as smooth functions of (valence, arousal) — no if/else
regions with hard edges. The named regions above are tuning guidance, not
code branches.

## Emotion labeling (debug only)

- VALENCE and AROUSAL bars in the debug overlay (valence bar centered: fill
  extends right of center for positive, left of center for negative).
- A text label in the overlay naming the nearest emotion region: afraid,
  excited, content, dejected, neutral — computed from which
  quadrant/magnitude the (valence, arousal) point falls in. Tuning aid only:
  the creature's code must never read it.

## Interaction with existing systems

- Trust changes feed valence (impulses above); valence must NOT feed trust
  (trust is earned by events only).
- Curiosity gain rate scales mildly with valence (a distressed creature
  explores less).
- Personality (Phase F) additionally randomizes: baseline valence, arousal
  decay rate, and impulse sensitivity ±30%.

## Definition of done

With debug bars on: startle him twice and watch arousal spike then decay
over ~10s while valence recovers over ~30s+ — and SEE the difference in his
movement during that window (twitchy, easily spooked, slumped) versus 2
minutes later (recovered). Leave him alone with a gentle cursor for 3
minutes and watch him visibly settle into content: slower, upright,
unbothered. The emotional state must be readable from movement alone with
the overlay OFF.

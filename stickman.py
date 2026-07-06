"""stickman — a minimalist artificial-life toy.

A white stick figure on a black canvas reacts to the mouse cursor: he wanders
when left alone, cautiously approaches a slow nearby cursor, and stumbles into
a panicked sprint when the cursor jerks at him.

All motion is physics: steering forces drive position/velocity, and every pose
is derived from that physics state each frame (no sprites, no keyframes).

Run:  python stickman.py     (Esc or close the window to quit)
"""

import math
import random
from collections import deque

import pygame
from pygame.math import Vector2

# ---------------------------------------------------------------- window ----
WIDTH, HEIGHT = 900, 600
FPS = 60
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LINE_W = 2

# ------------------------------------------------- figure proportions (px) --
HEAD_R = 6          # head circle radius
SPINE_LEN = 21      # neck to hip
LEG_LEN = 25        # hip to planted foot
ARM_LEN = 17        # shoulder to hand
FOOT_LIFT = 5.0     # max foot lift during a stride

# ------------------------------------------------------------- locomotion ---
WANDER_SPEED = 55.0     # cruising speed while wandering (px/s)
APPROACH_SPEED = 85.0   # burst speed while approaching
FLEE_SPEED = 270.0      # flat-out sprint
WANDER_FORCE = 170.0    # max steering force per state (px/s^2)
APPROACH_FORCE = 300.0
WATCH_FORCE = 340.0     # braking force when stopping to stand
FLEE_FORCE = 1100.0
STEER_TAU = 0.12        # steering smoothing time constant (~0.5 s to settle)
EDGE_MARGIN = 90.0      # start turning away this far from a wall
EDGE_PUSH = 260.0       # inward velocity bias at the very edge (px/s)
BOUND_PAD = 26.0        # hard safety clamp so the figure stays on screen

# ------------------------------------------------------- behavior triggers --
NEAR_DIST = 250.0       # cursor closer than this = "near"
SLOW_CURSOR = 200.0     # cursor slower than this = "moving slowly" (px/s)
FAST_CURSOR = 700.0     # cursor faster than this = startling (px/s)
STARTLE_DIST = 300.0    # fast cursor only startles within this range
SAFE_DIST = 350.0       # stop fleeing once this far from the cursor
STOP_DIST = 50.0        # approach stops this far from the cursor
LOSE_INTEREST_S = 9.0   # cursor idle this long -> lose interest, stroll off
CURSOR_IDLE_SPEED = 6.0  # below this the cursor counts as idle (px/s)
SPEED_SAMPLES = 10      # frames averaged for smoothed cursor speed
MIN_FLEE_S = 0.4        # flee at least this long so the stumble reads

# --------------------------------------------------------------- animation --
PHASE_RATE = 2 * math.pi / 44.0  # walk-phase radians per px traveled
STRIDE_PER_SPEED = 0.0085        # stride amplitude (rad) per px/s of speed
MAX_STRIDE = 1.0                 # stride amplitude cap (rad)
ARM_SWING = 0.62                 # arm swing relative to leg swing
LEAN_PER_ACC = 0.00075           # torso lean (rad) per px/s^2 of acceleration
LEAN_PER_VEL = 0.0011            # extra lean into sustained running
MAX_LEAN = 0.42                  # torso lean clamp (rad)
STUMBLE_KICK = 7.5               # lean-spring impulse on startle (rad/s)
STUMBLE_K = 60.0                 # stumble spring stiffness
STUMBLE_C = 8.0                  # stumble damping (underdamped: one wobble)
FACE_RATE = 5.0                  # how quickly he turns around (1/s)
BREATH_FREQ = 0.27               # idle breathing cycles per second
BREATH_AMP = 1.7                 # chest rise (px)
SWAY_AMP = 1.3                   # idle hip sway (px)
IDLE_SPLAY = 0.14                # idle stance: feet apart (rad)

# ---------------------------------------------------------- wander pacing ---
WANDER_TURN = 1.8                # how fast heading turns toward its target (1/s)
WANDER_NOISE = 0.3               # gentle heading drift while strolling (rad/sqrt(s))
WANDER_TURN_SPAN = 1.1           # new segment target = old heading +- gauss(this)
WALK_SPAN = (3.0, 8.0)           # seconds of walking between pauses
PAUSE_SPAN = (1.0, 3.0)          # seconds of standing during a pause
BURST_SPAN = (0.35, 0.8)         # approach: seconds of moving per burst
BURST_REST = (0.3, 0.7)          # approach: seconds of pausing per burst
ALERT_SPAN = (0.5, 1.1)          # seconds frozen sizing up a new cursor

# ----------------------------------------- emotion architecture v1.5 --------
# PREDICTION feeds APPRAISAL feeds SUBSTRATE (DESIGN.md "Emotion & Behavior
# Architecture (v1.5)"). Layer 1, the substrate, is a continuous 2D point:
# valence = slow mood (-1 distressed .. +1 content), arousal = fast weather
# (0 calm .. 1 activated). Appraisals (Layer 2) bump it; it always decays
# toward baseline (a mandatory dampener: valence is never pinned). Named
# emotions (afraid/excited/content/dejected/neutral) exist ONLY as debug
# overlay labels — no code branches on them.
VAL_BASE = 0.0
ARO_BASE = 0.2
VAL_HALF = 30.0         # valence half-life toward baseline (s) — slow mood
ARO_HALF = 7.0          # arousal half-life toward baseline (s) — fast weather
LN2 = math.log(2.0)

# Layer 2 appraisal table (v1.5): every significant event is scored against
# the need it affects and bumps the substrate via Man._appraise. Format:
#   event: (need affected, valence delta, arousal delta)
# Cursor-sourced appraisals will also feed the relationship ledger (Phase 4).
# Until drawn shapes exist (Phase D), "novelty" fires on first noticing the
# cursor and "inspected" on walking off satisfied after a long look at it;
# erasure/rest/trapped are declared but have no trigger yet (phases E/C/D).
APPRAISALS = {
    "startle":      ("safety",    -0.40, 0.6),  # fast cursor: threat
    "calm_company": ("social",     0.05, 0.0),  # calm cursor near 10s (x trust)
    "inspected":    ("curiosity",  0.15, 0.0),  # inspection completed
    "novelty":      ("curiosity",  0.10, 0.3),  # novel shape appears in view
    "erasure":      ("safety",    -0.20, 0.2),  # memory violated (Phase E hook)
    "rest":         ("energy",     0.10, 0.0),  # energy recovered (Phase C hook)
    "trapped":      ("safety",    -0.30, 0.4),  # enclosed (Phase D hook)
    "surprise":     ("prediction", 0.00, 0.6),  # view != memory (x mismatch)
}
CALM_COMPANY_S = 10.0   # sustained calm proximity per social appraisal
INSPECT_CURIO = 0.6     # curiosity above this marks the look an inspection
EVENT_FLASH_S = 3.0     # debug overlay names the last appraisal this long

# ------------------------------------------- prediction layer (v1.5 L3) -----
# His memory of the world IS his prediction of it. A coarse grid remembers
# how occupied each cell looked; cells in view are compared to memory every
# frame. Match = tiny comfort drift; mismatch = a surprise appraisal scaled
# by its size, then memory updates. A rolling world-volatility value (recent
# mismatch rate) moves the arousal decay TARGET: a world that keeps changing
# gives ambient anxiety, a long-familiar one genuine security. Modulation
# stays centered on the neutral ARO_BASE constant.
GRID_COLS, GRID_ROWS = 30, 20   # coarse grid: 30x30 px cells
VIEW_DIST = 250.0        # cells with centers this close are "in view"
BRUSH_R = 4              # left-drag paint brush radius (px)
DAB_OCC = 0.03           # cell occupancy added per paint dab (coarse estimate)
COMFORT_VAL = 0.007      # valence/s while the view matches memory (~+0.3 eq.)
COMFORT_ARO = -0.008     # arousal/s while the view matches memory
VOL_HALF = 120.0         # world-volatility half-life (s)
VOL_GAIN = 0.35          # volatility added per unit of viewed mismatch
VOL_START = 0.15         # neutral volatility at spawn (persisted in Phase 4)
VOL_ARO_SPAN = 0.5       # arousal-target shift per unit of volatility
ARO_BASE_MIN = 0.08      # dampener: arousal target floor (secure world)
ARO_BASE_MAX = 0.5       # dampener: arousal target cap (chaotic world)

# Layer 5.1 modulation (body): smooth functions of the substrate, no hard
# thresholds. Arousal scales speed/force/step rate/head rate; valence sets
# posture (upright+bounce vs slump+short stride) and idle style.
ARO_SPEED_GAIN = 0.7    # speed/force multiplier slope per unit arousal
ARO_STRIDE_GAIN = 0.35  # step-frequency slope per unit arousal (twitchy steps)
ARO_GLANCE_GAIN = 1.5   # head-movement frequency slope per unit arousal
VAL_BOUNCE = 0.9        # extra walk-bob amplitude at full positive valence
VAL_STRIDE = 0.3        # stride amplitude lost at full slump
VAL_SLUMP_LEAN = 0.13   # forward hunch (rad) at full negative valence
VAL_SLUMP_DROP = 4.0    # shoulder sag (px) at full negative valence
VAL_IDLE_SWAY = 1.6     # idle weight-shift sway gain at content (+v, calm)
VAL_PAUSE = 1.0         # wander pauses lengthen this fraction at content
# v1 carryover, replaced by a proper Layer 5.2 utility term in Phase 5:
# fear still blocks re-approaching until it fades (distress = max(0,-v)*a)
APPROACH_BLOCK = 0.15

# ------------------------------------------------------------ emotion pose --
EMO_TAU = 0.25          # pose-parameter smoothing (s) — blended, never snapped
CURIOUS_DELAY = 0.8     # calm watching before curiosity starts building (s)
CURIOUS_RAMP = 2.5      # seconds for curiosity to saturate
CURIOUS_DROP = 1.5      # curiosity lost per second once the cursor moves
CROUCH_DROP = 0.16      # leg-length fraction the hips drop at full crouch
LEAN_CURIOUS = 0.17     # lean toward the cursor at full curiosity (rad)
LEAN_WARY = 0.13        # lean away from the cursor when fearful/alert (rad)
TILT_AMP = 3.2          # head-cock offset at full curiosity (px)
TILT_FREQ = 0.22        # head cocks side to side this often (Hz)
REACH_DIST = 110.0      # the hand only reaches out within this range
GUARD_RAISE = 0.8       # how high the hands come up in a flee (fraction of arm)

# ----------------------------------------------------------- debug overlay --
DEBUG_START_ON = True   # overlay visible at launch (D toggles it)
BAR_W, BAR_H = 120, 10  # bar outline size (px)
BAR_GAP = 4             # vertical gap between rows (px)
BAR_MARGIN = 8          # overlay offset from the top-left corner (px)
BAR_LABEL_W = 60        # label column width left of the bars (px)
DEBUG_FONT_PT = 14      # small white text

WANDER, ALERT, APPROACH, WATCH, FLEE = (
    "wander", "alert", "approach", "watch", "flee")

CELL_W = WIDTH / GRID_COLS
CELL_H = HEIGHT / GRID_ROWS


class World:
    """The persistent paintable canvas and its coarse occupancy grid — what
    is actually there, as opposed to what the man remembers (Man.memory).
    Pulled forward from Phase D in minimal form (paint only: no obstacle
    force, no inspect behavior yet) so the prediction layer has a world
    that can change."""

    def __init__(self):
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.canvas.fill(BLACK)
        self.occ = [[0.0] * GRID_COLS for _ in range(GRID_ROWS)]

    def _dab(self, pos):
        pygame.draw.circle(self.canvas, WHITE,
                           (round(pos.x), round(pos.y)), BRUSH_R)
        c = min(GRID_COLS - 1, max(0, int(pos.x / CELL_W)))
        r = min(GRID_ROWS - 1, max(0, int(pos.y / CELL_H)))
        self.occ[r][c] = min(1.0, self.occ[r][c] + DAB_OCC)

    def paint(self, a, b):
        """Paint a stroke segment as dabs every few px so drags stay solid."""
        seg = b - a
        steps = max(1, int(seg.length() / 3))
        for i in range(steps + 1):
            self._dab(a + seg * (i / steps))


class Man:
    """Physics, steering, and the cursor-reaction state machine."""

    def __init__(self, pos):
        self.pos = Vector2(pos)
        self.vel = Vector2()
        self.steer = Vector2()       # smoothed steering force
        self.acc_smooth = Vector2()  # smoothed acceleration, for body lean
        self.state = WANDER
        self.state_time = 0.0

        # cursor tracking
        self.prev_cursor = None
        self.speed_hist = deque(maxlen=SPEED_SAMPLES)
        self.cursor_speed = 0.0
        self.cursor_idle_s = 0.0

        # wander / approach pacing
        self.heading = random.uniform(0, 2 * math.pi)
        self.heading_target = self.heading
        self.moving = True
        self.move_timer = random.uniform(*WALK_SPAN)

        # animation state (read by Skeleton)
        self.phase = 0.0             # walk phase, advances with distance
        self.facing = 1.0            # smoothed -1..1; sign = which way he faces
        self.lean = 0.0              # torso lean (rad), includes stumble
        self.stumble = 0.0           # extra lean from the startle spring
        self.stumble_vel = 0.0
        self.breath_t = random.uniform(0, 10)
        self.look = Vector2(1, 0)    # unit-ish gaze direction for the head

        # emotion substrate (v1.5 Layer 1): a continuous valence-arousal
        # point, never a discrete state. Only _appraise writes bumps into it.
        self.valence = VAL_BASE      # -1 distressed .. +1 content (slow mood)
        self.arousal = ARO_BASE      # 0 calm .. 1 activated (fast weather)
        self.speed_gain = 1.0        # arousal-driven speed/force multiplier
        self.calm_company_t = 0.0    # seconds of sustained calm proximity
        self.inspected = False       # this encounter reached full curiosity
        self.last_event = ""         # debug: most recent appraisal fired
        self.last_event_t = 1e9      # debug: seconds since it fired

        # prediction (v1.5 Layer 3): what he remembers each cell looked like,
        # how unstable the world has recently been, and the arousal target
        # that instability sets (decay pulls arousal toward aro_base)
        self.memory = [[0.0] * GRID_COLS for _ in range(GRID_ROWS)]
        self.volatility = VOL_START
        self.aro_base = ARO_BASE

        self.curious = 0.0           # 0..1: builds while watching a calm cursor
        self.trust = 0.2             # 0..1: placeholder until Phase F drives it
        self.alert_span = 0.0        # how long this alert freeze lasts
        self.crouch = 0.0            # smoothed pose params
        self.lean_emo = 0.0
        self.tilt = 0.0
        self.reach = 0.0
        self.guard = 0.0
        self.slump = 0.0             # smoothed -valence posture weight
        self.bounce = 0.0            # smoothed +valence posture weight

    # ------------------------------------------------------------ helpers --
    def _track_cursor(self, cursor, dt):
        if self.prev_cursor is None:
            self.prev_cursor = Vector2(cursor)
        inst = (cursor - self.prev_cursor).length() / dt
        self.prev_cursor = Vector2(cursor)
        self.speed_hist.append(inst)
        self.cursor_speed = sum(self.speed_hist) / len(self.speed_hist)
        if self.cursor_speed > CURSOR_IDLE_SPEED:
            self.cursor_idle_s = 0.0
        else:
            self.cursor_idle_s += dt

    def _pick_heading(self, cursor):
        """Choose the next stroll heading: usually a moderate turn from the
        current one; if he just lost interest in a nearby cursor, away from it."""
        bored_near = (cursor is not None
                      and self.cursor_idle_s > LOSE_INTEREST_S
                      and self.pos.distance_to(cursor) < NEAR_DIST * 1.5)
        if bored_near:
            away = self.pos - cursor
            self.heading_target = (math.atan2(away.y, away.x)
                                   + random.uniform(-0.8, 0.8))
        else:
            self.heading_target = self.heading + random.gauss(0, WANDER_TURN_SPAN)

    def _set_state(self, state):
        if state != self.state:
            self.state = state
            self.state_time = 0.0
            if state in (WANDER, APPROACH):
                self.moving = True
                self.move_timer = self._move_span()
                if state == WANDER:
                    self._pick_heading(self.prev_cursor)
            elif state == ALERT:
                self.alert_span = random.uniform(*ALERT_SPAN)

    def _move_span(self):
        """Duration of the next move/pause leg. Idle style rides on the mood
        (Layer 5.1): a content creature (positive valence, calm) lingers in
        its wander pauses. Burst pacing is plain until Phase 5 adds emotion
        to the decision layer."""
        if self.state == WANDER and not self.moving:
            ease = max(0.0, self.valence) * (1.0 - self.arousal)
            return random.uniform(*PAUSE_SPAN) * (1 + VAL_PAUSE * ease)
        if self.state == WANDER:
            return random.uniform(*WALK_SPAN)
        if self.moving:
            return random.uniform(*BURST_SPAN)
        return random.uniform(*BURST_REST)

    def _appraise(self, event, intensity=1.0, source="world"):
        """Layer 2: score one event against the need it affects and move the
        substrate by the table deltas x intensity. `source` marks who caused
        it; cursor-sourced appraisals will also update the relationship
        ledger when Phase 4 lands. Sensitivities (Phase 4) scale here too."""
        need, dv, da = APPRAISALS[event]
        self.valence = max(-1.0, min(1.0, self.valence + dv * intensity))
        self.arousal = max(0.0, min(1.0, self.arousal + da * intensity))
        self.last_event = f"{event} ({need}, {source})"
        self.last_event_t = 0.0

    def _substrate(self, cursor, dt):
        """Layer 1: decay the valence-arousal point toward baseline (always
        active — valence must never pin) and derive the body-modulation gain.
        Also runs the one sustained Phase 1 appraisal: calm cursor proximity
        held CALM_COMPANY_S seconds meets the social need, scaled by trust."""
        near_calm = (self.pos.distance_to(cursor) < NEAR_DIST
                     and self.cursor_speed < SLOW_CURSOR
                     and self.state != FLEE)
        if near_calm:
            self.calm_company_t += dt
            if self.calm_company_t >= CALM_COMPANY_S:
                self.calm_company_t -= CALM_COMPANY_S
                self._appraise("calm_company", intensity=self.trust,
                               source="cursor")
        else:
            self.calm_company_t = 0.0

        # decay: valence toward its fixed baseline, arousal toward the
        # volatility-set target (an unstable world keeps the floor raised)
        self.valence = VAL_BASE + (self.valence - VAL_BASE) * math.exp(
            -LN2 * dt / VAL_HALF)
        self.arousal = self.aro_base + (self.arousal - self.aro_base) * math.exp(
            -LN2 * dt / ARO_HALF)
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.speed_gain = 1.0 + ARO_SPEED_GAIN * (self.arousal - ARO_BASE)

    def _predict(self, world, dt):
        """Layer 3: compare cells in view to memory. Match drifts him toward
        comfort; mismatch fires a surprise appraisal scaled by its size, then
        memory accepts the new reality. Recent mismatch feeds a rolling world
        volatility whose level sets the arousal decay target (clamped — the
        dampener keeping a chaotic world short of permanent panic)."""
        c0 = max(0, int((self.pos.x - VIEW_DIST) / CELL_W))
        c1 = min(GRID_COLS - 1, int((self.pos.x + VIEW_DIST) / CELL_W))
        r0 = max(0, int((self.pos.y - VIEW_DIST) / CELL_H))
        r1 = min(GRID_ROWS - 1, int((self.pos.y + VIEW_DIST) / CELL_H))
        view_sq = VIEW_DIST * VIEW_DIST
        mismatch, matched, viewed = 0.0, 0, 0
        for r in range(r0, r1 + 1):
            dy = (r + 0.5) * CELL_H - self.pos.y
            for c in range(c0, c1 + 1):
                dx = (c + 0.5) * CELL_W - self.pos.x
                if dx * dx + dy * dy > view_sq:
                    continue
                viewed += 1
                diff = world.occ[r][c] - self.memory[r][c]
                if abs(diff) > 0.001:
                    mismatch += abs(diff)
                    self.memory[r][c] = world.occ[r][c]
                else:
                    matched += 1
        if mismatch > 0.0:
            self._appraise("surprise", intensity=min(1.0, mismatch))
        if viewed:
            ease = matched / viewed  # a familiar view is quietly reassuring
            self.valence += COMFORT_VAL * ease * dt
            self.arousal = max(0.0, self.arousal + COMFORT_ARO * ease * dt)

        self.volatility = min(1.0, self.volatility * math.exp(
            -LN2 * dt / VOL_HALF) + VOL_GAIN * min(1.0, mismatch))
        self.aro_base = max(ARO_BASE_MIN, min(
            ARO_BASE_MAX,
            ARO_BASE + VOL_ARO_SPAN * (self.volatility - VOL_START)))

    def _transitions(self, cursor):
        dist = self.pos.distance_to(cursor)
        bored = self.cursor_idle_s > LOSE_INTEREST_S

        # startle overrides everything (flee on genuine startle always wins)
        if (self.state != FLEE and self.cursor_speed > FAST_CURSOR
                and dist < STARTLE_DIST):
            self._set_state(FLEE)
            self._appraise("startle", source="cursor")
            self.stumble_vel += STUMBLE_KICK * (1 if self.vel.x <= 0 else -1)
            return

        if self.state == FLEE:
            if dist > SAFE_DIST and self.state_time > MIN_FLEE_S:
                self._set_state(WATCH)  # pull up and look back warily
        elif self.state == WANDER:
            if dist < NEAR_DIST and self.cursor_speed < SLOW_CURSOR and not bored:
                self._set_state(ALERT)  # freeze first: "what is that?"
                self._appraise("novelty", source="cursor")
                self.inspected = False
        elif self.state == ALERT:
            if dist > NEAR_DIST or bored:
                self._set_state(WANDER)
            elif self.state_time > self.alert_span:
                self._set_state(APPROACH)
        elif self.state == APPROACH:
            if dist > NEAR_DIST or bored:
                self._set_state(WANDER)
            elif dist < STOP_DIST + 4:
                self._set_state(WATCH)
        elif self.state == WATCH:
            if dist > NEAR_DIST or bored:
                if bored and self.inspected:
                    # sized it up fully and walked off satisfied
                    self._appraise("inspected", source="cursor")
                    self.inspected = False
                self._set_state(WANDER)
            elif (dist > STOP_DIST + 30 and self.cursor_speed < SLOW_CURSOR
                    and max(0.0, -self.valence) * self.arousal
                    < APPROACH_BLOCK):  # too rattled to close in (v1 carryover)
                self._set_state(APPROACH)

    def _desired_velocity(self, cursor, dt):
        """Each behavior expresses itself as a velocity it would like to have.
        Arousal scales every speed and force: calm = languid, activated =
        twitchy."""
        to_cursor = cursor - self.pos
        dist = to_cursor.length()
        g = self.speed_gain

        if self.state == FLEE:
            away = -to_cursor / dist if dist > 1e-6 else Vector2(1, 0)
            return away * FLEE_SPEED * g, FLEE_FORCE * g

        if self.state == WATCH:
            return Vector2(), WATCH_FORCE  # brake to a standstill

        if self.state == ALERT:
            if self.state_time < 0.25 and dist > 1e-6:
                # a startled half-step back before freezing
                return -to_cursor / dist * 30.0, WATCH_FORCE
            return Vector2(), WATCH_FORCE

        # wander and approach alternate moving with standing still
        self.move_timer -= dt
        if self.move_timer <= 0:
            self.moving = not self.moving
            if self.state == WANDER and self.moving:
                self._pick_heading(cursor)
            self.move_timer = self._move_span()
        if not self.moving:
            return Vector2(), WANDER_FORCE

        if self.state == APPROACH:
            # ease off over the last 80 px so he settles at the stop distance
            ease = max(0.0, min(1.0, (dist - STOP_DIST) / 80.0))
            direction = to_cursor / dist if dist > 1e-6 else Vector2()
            return direction * APPROACH_SPEED * g * ease, APPROACH_FORCE * g

        # WANDER: hold a per-segment heading, turning toward it in a smooth arc
        # with only gentle drift — never Brownian back-and-forth pacing
        diff = (self.heading_target - self.heading + math.pi) % (2 * math.pi) - math.pi
        self.heading += diff * min(1.0, WANDER_TURN * dt)
        self.heading += random.gauss(0, WANDER_NOISE) * math.sqrt(dt)
        # near walls the edge bias wins; let heading follow the actual motion
        # so he strolls along the wall instead of pressing into it
        if self.vel.length() > 20:
            va = math.atan2(self.vel.y, self.vel.x)
            adrift = (va - self.heading + math.pi) % (2 * math.pi) - math.pi
            self.heading += adrift * min(1.0, 0.8 * dt)
        return (Vector2(math.cos(self.heading), math.sin(self.heading))
                * WANDER_SPEED * g, WANDER_FORCE * g)

    def _edge_bias(self):
        """Inward velocity bias that ramps up near walls: turns, never bounces."""
        push = Vector2()
        for axis, size in ((0, WIDTH), (1, HEIGHT)):
            d_lo = self.pos[axis]
            d_hi = size - self.pos[axis]
            if d_lo < EDGE_MARGIN:
                push[axis] += EDGE_PUSH * (1 - d_lo / EDGE_MARGIN) ** 2
            if d_hi < EDGE_MARGIN:
                push[axis] -= EDGE_PUSH * (1 - d_hi / EDGE_MARGIN) ** 2
        return push

    # ------------------------------------------------------------- update --
    def update(self, cursor, dt, world=None):
        self.state_time += dt
        self.breath_t += dt
        self.last_event_t += dt
        self._track_cursor(cursor, dt)
        if world is not None:
            self._predict(world, dt)
        self._substrate(cursor, dt)
        self._transitions(cursor)

        desired, max_force = self._desired_velocity(cursor, dt)
        desired += self._edge_bias()

        steer_target = desired - self.vel
        if steer_target.length() > max_force:
            steer_target.scale_to_length(max_force)
        # exponential smoothing = the ~0.5 s blend between behavior states
        blend = min(1.0, dt / STEER_TAU)
        self.steer += (steer_target - self.steer) * blend

        self.vel += self.steer * dt
        cap = FLEE_SPEED * max(1.0, self.speed_gain)
        if self.vel.length() > cap:
            self.vel.scale_to_length(cap)
        if self.vel.length() < 1.5 and desired.length() < 1e-6:
            self.vel = Vector2()  # settle fully: no micro-jitter while standing
        self.pos += self.vel * dt

        # hard safety clamp (edge bias should keep this from ever engaging)
        self.pos.x = max(BOUND_PAD, min(WIDTH - BOUND_PAD, self.pos.x))
        self.pos.y = max(BOUND_PAD + 44, min(HEIGHT - BOUND_PAD, self.pos.y))

        self._animate(cursor, dt)

    def _animate(self, cursor, dt):
        speed = self.vel.length()

        # walk phase advances with distance traveled, so stride matches speed;
        # arousal quickens the step rate (shorter, twitchier strides)
        self.phase += speed * dt * PHASE_RATE * (
            1 + ARO_STRIDE_GAIN * (self.arousal - ARO_BASE))

        # facing: velocity while moving; the cursor while standing watchful.
        # A deadband on vel.x keeps him from flip-flopping on shallow arcs.
        if speed > 10 and abs(self.vel.x) > 8:
            target = 1.0 if self.vel.x >= 0 else -1.0
        elif self.state in (WATCH, APPROACH, ALERT):
            target = 1.0 if cursor.x >= self.pos.x else -1.0
        else:
            target = 1.0 if self.facing >= 0 else -1.0
        self.facing += (target - self.facing) * min(1.0, FACE_RATE * dt)

        # torso lean into (smoothed) acceleration, plus a bit into speed
        self.acc_smooth += (self.steer - self.acc_smooth) * min(1.0, dt / 0.1)
        lean = self.acc_smooth.x * LEAN_PER_ACC + self.vel.x * LEAN_PER_VEL
        lean = max(-MAX_LEAN, min(MAX_LEAN, lean))

        # stumble = underdamped spring on extra lean, kicked by a startle
        acc = -STUMBLE_K * self.stumble - STUMBLE_C * self.stumble_vel
        self.stumble_vel += acc * dt
        self.stumble += self.stumble_vel * dt

        self._emote(cursor, dt)
        # low valence hunches him forward on top of whatever else he's doing
        self.lean = (lean + self.stumble + self.lean_emo
                     + VAL_SLUMP_LEAN * self.slump * self.facing)

        # gaze: the cursor when engaged with it (a glance back mid-flee),
        # otherwise straight ahead
        if self.state in (WATCH, APPROACH, ALERT, FLEE):
            to_c = cursor - self.pos
            if to_c.length() > 1e-6:
                self.look = to_c.normalize()
        else:
            self.look = Vector2(self.facing, 0)

    def _emote(self, cursor, dt):
        """Update curiosity and blend the posture the mood calls for."""
        dist = self.pos.distance_to(cursor)

        # curiosity: builds only while calmly watching; any motion resets it.
        # (Valence coupling to curiosity gain returns as Phase 5 decision input.)
        if (self.state == WATCH and self.cursor_speed < SLOW_CURSOR
                and self.state_time > CURIOUS_DELAY):
            self.curious = min(1.0, self.curious + dt / CURIOUS_RAMP)
            if self.curious > INSPECT_CURIO:
                self.inspected = True  # a full look counts as an inspection
        else:
            self.curious = max(0.0, self.curious - CURIOUS_DROP * dt)

        toward = 1.0 if cursor.x >= self.pos.x else -1.0
        # distress posture weight: a smooth product of the substrate (low
        # valence x high arousal), not a stored emotion — labels stay debug-only
        f = max(0.0, -self.valence) * self.arousal
        c = self.curious * (1.0 - f)  # fear overrides curiosity
        t_crouch = t_lean = t_tilt = t_reach = t_guard = 0.0
        if self.state == ALERT:
            t_crouch, t_lean = 0.12, -LEAN_WARY * toward
        elif self.state == APPROACH:
            t_crouch = 0.18 + 0.4 * f
            t_lean = toward * (0.05 - LEAN_WARY * f)
        elif self.state == WATCH:
            t_crouch = 0.4 * f + 0.1 * c
            t_lean = toward * (LEAN_CURIOUS * c - LEAN_WARY * f)
            tilt_hz = TILT_FREQ * (1 + ARO_GLANCE_GAIN * (self.arousal - ARO_BASE))
            t_tilt = TILT_AMP * c * math.sin(
                self.state_time * 2 * math.pi * tilt_hz)
            if dist < REACH_DIST:
                t_reach = max(0.0, (c - 0.35) / 0.65)
        elif self.state == FLEE:
            t_crouch, t_guard = 0.25, 1.0

        blend = min(1.0, dt / EMO_TAU)
        self.crouch += (t_crouch - self.crouch) * blend
        self.lean_emo += (t_lean - self.lean_emo) * blend
        self.tilt += (t_tilt - self.tilt) * blend
        self.reach += (t_reach - self.reach) * blend
        self.guard += (t_guard - self.guard) * blend
        self.slump += (max(0.0, -self.valence) - self.slump) * blend
        self.bounce += (max(0.0, self.valence) - self.bounce) * blend


class Skeleton:
    """Draws the stick figure every frame from a Man's physics state."""

    def draw(self, surf, man):
        speed = man.vel.length()
        walk = max(0.0, min(1.0, speed / 30.0))  # 0 standing .. 1 walking
        idle = 1.0 - walk
        f = man.facing
        ph = man.phase
        lean = man.lean
        # low valence shortens the stride; positive valence bounces the step
        stride = min(MAX_STRIDE, speed * STRIDE_PER_SPEED) * (
            1 - VAL_STRIDE * man.slump)
        bob = 1.4 * (1 + VAL_BOUNCE * man.bounce)

        breath = math.sin(man.breath_t * 2 * math.pi * BREATH_FREQ)
        # contentment (+valence, calm) reads as a slow idle weight shift
        ease = max(0.0, man.valence) * (1.0 - man.arousal)
        sway = (math.sin(man.breath_t * 0.7) * SWAY_AMP * idle
                * (1 + VAL_IDLE_SWAY * ease))

        # hip: the anchor. Bobs slightly with each step (twice per cycle).
        # Crouching shortens the hip-to-foot drop so the feet stay planted.
        leg_drop = LEG_LEN * (1 - CROUCH_DROP * man.crouch)
        hip = Vector2(man.pos.x + sway,
                      man.pos.y - leg_drop + abs(math.sin(ph)) * bob * walk)

        # spine tilts by the lean angle; chest rises with idle breathing and
        # sags when he's slumped (shoulders drop, head rides down with them)
        up = Vector2(math.sin(lean), -math.cos(lean))
        sag = VAL_SLUMP_DROP * man.slump
        neck = hip + up * (SPINE_LEN - sag + breath * BREATH_AMP * idle)
        shoulder = hip + up * (SPINE_LEN * 0.86 - sag + breath * BREATH_AMP * idle)

        # head sits past the neck, shifts a little toward the gaze, and cocks
        # sideways (perpendicular to the spine) when he's curious
        perp = Vector2(-up.y, up.x)
        head = neck + up * (HEAD_R + 1) + man.look * 2.5 + perp * man.tilt
        head.y += breath * 0.6 * idle

        pygame.draw.line(surf, WHITE, hip, neck, LINE_W)
        pygame.draw.circle(surf, WHITE, (round(head.x), round(head.y)),
                           HEAD_R, LINE_W)

        for s in (1, -1):  # the two sides of the body
            # leg: swing angle from vertical; the forward-swinging leg lifts
            a = math.sin(ph) * stride * s + IDLE_SPLAY * s * idle
            lift = max(0.0, math.cos(ph) * s) * FOOT_LIFT * walk
            foot = Vector2(hip.x + math.sin(a) * leg_drop * f,
                           hip.y + math.cos(a) * leg_drop - lift)
            knee = (hip + foot) / 2
            # knees always bend forward; a crouch bends them further
            knee.x += f * (1.3 + lift * 0.9 + man.crouch * 3.5)
            pygame.draw.line(surf, WHITE, hip, knee, LINE_W)
            pygame.draw.line(surf, WHITE, knee, foot, LINE_W)

            # arm: counter-swings against the same-side leg
            b = math.sin(ph + math.pi) * stride * ARM_SWING * s
            hand = Vector2(shoulder.x + math.sin(b) * ARM_LEN * f + s * 2 * idle,
                           shoulder.y + math.cos(b) * ARM_LEN)
            elbow_bias = -f * (1.0 + abs(math.sin(b)) * 2.0)  # elbows trail back

            if s == 1 and man.reach > 0.01:
                # curiosity: the near hand stretches out toward the cursor
                reach_to = shoulder + man.look * (ARM_LEN * 0.95)
                hand = hand.lerp(reach_to, man.reach)
                elbow_bias *= 1 - man.reach  # a reaching arm straightens

            if man.guard > 0.01:
                # panic: both hands come up beside the head, elbows flared
                guard_to = shoulder + Vector2(s * 4 - f * 2,
                                              -ARM_LEN * GUARD_RAISE)
                hand = hand.lerp(guard_to, man.guard)
                elbow_bias = elbow_bias * (1 - man.guard) + s * 5 * man.guard

            elbow = (shoulder + hand) / 2
            elbow.x += elbow_bias
            pygame.draw.line(surf, WHITE, shoulder, elbow, LINE_W)
            pygame.draw.line(surf, WHITE, elbow, hand, LINE_W)


def emotion_region(valence, arousal):
    """Debug-only label for the nearest emotion region. The creature's code
    must never read this — it exists purely for tuning the overlay."""
    if math.hypot(valence, arousal - ARO_BASE) < 0.18:
        return "neutral"
    if arousal >= 0.45:
        return "afraid" if valence < 0 else "excited"
    return "dejected" if valence < 0 else "content"


class DebugOverlay:
    """Live bars for the man's internal state, top-left. D toggles it.

    Adding a bar is one line in self.bars: a (label, getter, centered) tuple.
    Plain bars fill 0..1 from the left; a centered bar takes -1..1 and fills
    outward from the middle (right = positive, left = negative).
    """

    def __init__(self, man):
        self.font = pygame.font.Font(None, DEBUG_FONT_PT)
        self.man = man
        self.bars = [
            ("speed", lambda: man.vel.length() / FLEE_SPEED, False),
            ("valence", lambda: man.valence, True),
            ("arousal", lambda: man.arousal, False),
            ("curious", lambda: man.curious, False),
            ("trust", lambda: man.trust, False),
            ("volatile", lambda: man.volatility, False),
        ]

    def draw(self, surf):
        y = BAR_MARGIN
        x = BAR_MARGIN + BAR_LABEL_W
        inner = BAR_W - 2  # the fill sits flush against the 1px outline
        for label, get, centered in self.bars:
            text = self.font.render(label, True, WHITE)
            surf.blit(text, (BAR_MARGIN, y + (BAR_H - text.get_height()) // 2))
            pygame.draw.rect(surf, WHITE, (x, y, BAR_W, BAR_H), 1)
            if centered:
                v = max(-1.0, min(1.0, get()))
                fill = round(inner / 2 * abs(v))
                mid = x + BAR_W // 2
                left = mid if v >= 0 else mid - fill
                if fill > 0:
                    pygame.draw.rect(surf, WHITE, (left, y + 1, fill, BAR_H - 2))
                pygame.draw.rect(surf, WHITE, (mid, y, 1, BAR_H))  # zero tick
            else:
                fill = round(inner * max(0.0, min(1.0, get())))
                if fill > 0:
                    pygame.draw.rect(surf, WHITE, (x + 1, y + 1, fill, BAR_H - 2))
            y += BAR_H + BAR_GAP

        mood = emotion_region(self.man.valence, self.man.arousal)
        surf.blit(self.font.render("mood: " + mood, True, WHITE),
                  (BAR_MARGIN, y))
        if self.man.last_event_t < EVENT_FLASH_S:
            # transient: names the appraisal that just moved the bars
            surf.blit(self.font.render("event: " + self.man.last_event,
                                       True, WHITE),
                      (BAR_MARGIN, y + DEBUG_FONT_PT))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("stickman")
    clock = pygame.time.Clock()

    man = Man((WIDTH / 2, HEIGHT / 2))
    world = World()
    skeleton = Skeleton()
    overlay = DebugOverlay(man)
    debug_on = DEBUG_START_ON
    paint_from = None  # last stroke point while the left button is held

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 20.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_d:
                debug_on = not debug_on

        cursor = Vector2(pygame.mouse.get_pos())
        if pygame.mouse.get_pressed()[0]:
            world.paint(paint_from or cursor, cursor)
            paint_from = Vector2(cursor)
        else:
            paint_from = None
        if dt > 0:
            man.update(cursor, dt, world)

        screen.blit(world.canvas, (0, 0))
        skeleton.draw(screen, man)
        if debug_on:
            overlay.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

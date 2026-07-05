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

# ------------------------------------------------------------ emotion pose --
EMO_TAU = 0.25          # pose-parameter smoothing (s) — blended, never snapped
FEAR_DECAY = 0.22       # fear halves in ~3 s of calm
FEAR_CREEP = 1.2        # fear/s while a moderately fast cursor prowls nearby
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

WANDER, ALERT, APPROACH, WATCH, FLEE = (
    "wander", "alert", "approach", "watch", "flee")


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

        # emotion state (drives posture; read by Skeleton)
        self.fear = 0.0              # 0..1: spikes on startle, decays with calm
        self.curious = 0.0           # 0..1: builds while watching a calm cursor
        self.alert_span = 0.0        # how long this alert freeze lasts
        self.crouch = 0.0            # smoothed pose params
        self.lean_emo = 0.0
        self.tilt = 0.0
        self.reach = 0.0
        self.guard = 0.0

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
                span = WALK_SPAN if state == WANDER else BURST_SPAN
                self.move_timer = random.uniform(*span)
                if state == WANDER:
                    self._pick_heading(self.prev_cursor)
            elif state == ALERT:
                self.alert_span = random.uniform(*ALERT_SPAN)

    def _transitions(self, cursor):
        dist = self.pos.distance_to(cursor)
        bored = self.cursor_idle_s > LOSE_INTEREST_S

        # startle overrides everything
        if (self.state != FLEE and self.cursor_speed > FAST_CURSOR
                and dist < STARTLE_DIST):
            self._set_state(FLEE)
            self.fear = 1.0
            self.stumble_vel += STUMBLE_KICK * (1 if self.vel.x <= 0 else -1)
            return

        if self.state == FLEE:
            if dist > SAFE_DIST and self.state_time > MIN_FLEE_S:
                self._set_state(WATCH)  # pull up and look back warily
        elif self.state == WANDER:
            if dist < NEAR_DIST and self.cursor_speed < SLOW_CURSOR and not bored:
                self._set_state(ALERT)  # freeze first: "what is that?"
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
                self._set_state(WANDER)
            elif (dist > STOP_DIST + 30 and self.cursor_speed < SLOW_CURSOR
                    and self.fear < 0.5):  # too rattled to close in again yet
                self._set_state(APPROACH)

    def _desired_velocity(self, cursor, dt):
        """Each behavior expresses itself as a velocity it would like to have."""
        to_cursor = cursor - self.pos
        dist = to_cursor.length()

        if self.state == FLEE:
            away = -to_cursor / dist if dist > 1e-6 else Vector2(1, 0)
            return away * FLEE_SPEED, FLEE_FORCE

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
            if self.state == WANDER:
                span = WALK_SPAN if self.moving else PAUSE_SPAN
                if self.moving:
                    self._pick_heading(cursor)
            else:
                span = BURST_SPAN if self.moving else BURST_REST
            self.move_timer = random.uniform(*span)
        if not self.moving:
            return Vector2(), WANDER_FORCE

        if self.state == APPROACH:
            # ease off over the last 80 px so he settles at STOP_DIST
            ease = max(0.0, min(1.0, (dist - STOP_DIST) / 80.0))
            direction = to_cursor / dist if dist > 1e-6 else Vector2()
            return direction * APPROACH_SPEED * ease, APPROACH_FORCE

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
                * WANDER_SPEED, WANDER_FORCE)

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
    def update(self, cursor, dt):
        self.state_time += dt
        self.breath_t += dt
        self._track_cursor(cursor, dt)
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
        if self.vel.length() > FLEE_SPEED:
            self.vel.scale_to_length(FLEE_SPEED)
        if self.vel.length() < 1.5 and desired.length() < 1e-6:
            self.vel = Vector2()  # settle fully: no micro-jitter while standing
        self.pos += self.vel * dt

        # hard safety clamp (edge bias should keep this from ever engaging)
        self.pos.x = max(BOUND_PAD, min(WIDTH - BOUND_PAD, self.pos.x))
        self.pos.y = max(BOUND_PAD + 44, min(HEIGHT - BOUND_PAD, self.pos.y))

        self._animate(cursor, dt)

    def _animate(self, cursor, dt):
        speed = self.vel.length()

        # walk phase advances with distance traveled, so stride matches speed
        self.phase += speed * dt * PHASE_RATE

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
        self.lean = lean + self.stumble + self.lean_emo

        # gaze: the cursor when engaged with it (a glance back mid-flee),
        # otherwise straight ahead
        if self.state in (WATCH, APPROACH, ALERT, FLEE):
            to_c = cursor - self.pos
            if to_c.length() > 1e-6:
                self.look = to_c.normalize()
        else:
            self.look = Vector2(self.facing, 0)

    def _emote(self, cursor, dt):
        """Update fear/curiosity and blend the posture they call for."""
        dist = self.pos.distance_to(cursor)

        # fear: creeps while a moderately fast cursor prowls nearby, decays calm
        if (self.cursor_speed > SLOW_CURSOR and dist < NEAR_DIST
                and self.state in (ALERT, APPROACH, WATCH)):
            self.fear = min(1.0, self.fear + FEAR_CREEP * dt)
        self.fear *= math.exp(-FEAR_DECAY * dt)

        # curiosity: builds only while calmly watching; any motion resets it
        if (self.state == WATCH and self.cursor_speed < SLOW_CURSOR
                and self.state_time > CURIOUS_DELAY):
            self.curious = min(1.0, self.curious + dt / CURIOUS_RAMP)
        else:
            self.curious = max(0.0, self.curious - CURIOUS_DROP * dt)

        toward = 1.0 if cursor.x >= self.pos.x else -1.0
        f = self.fear
        c = self.curious * (1.0 - f)  # fear overrides curiosity
        t_crouch = t_lean = t_tilt = t_reach = t_guard = 0.0
        if self.state == ALERT:
            t_crouch, t_lean = 0.12, -LEAN_WARY * toward
        elif self.state == APPROACH:
            t_crouch = 0.18 + 0.3 * f
            t_lean = toward * (0.05 - LEAN_WARY * f)
        elif self.state == WATCH:
            t_crouch = 0.3 * f + 0.1 * c
            t_lean = toward * (LEAN_CURIOUS * c - LEAN_WARY * f)
            t_tilt = TILT_AMP * c * math.sin(
                self.state_time * 2 * math.pi * TILT_FREQ)
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


class Skeleton:
    """Draws the stick figure every frame from a Man's physics state."""

    def draw(self, surf, man):
        speed = man.vel.length()
        walk = max(0.0, min(1.0, speed / 30.0))  # 0 standing .. 1 walking
        idle = 1.0 - walk
        f = man.facing
        ph = man.phase
        lean = man.lean
        stride = min(MAX_STRIDE, speed * STRIDE_PER_SPEED)

        breath = math.sin(man.breath_t * 2 * math.pi * BREATH_FREQ)
        sway = math.sin(man.breath_t * 0.7) * SWAY_AMP * idle

        # hip: the anchor. Bobs slightly with each step (twice per cycle).
        # Crouching shortens the hip-to-foot drop so the feet stay planted.
        leg_drop = LEG_LEN * (1 - CROUCH_DROP * man.crouch)
        hip = Vector2(man.pos.x + sway,
                      man.pos.y - leg_drop + abs(math.sin(ph)) * 1.4 * walk)

        # spine tilts by the lean angle; chest rises with idle breathing
        up = Vector2(math.sin(lean), -math.cos(lean))
        neck = hip + up * (SPINE_LEN + breath * BREATH_AMP * idle)
        shoulder = hip + up * (SPINE_LEN * 0.86 + breath * BREATH_AMP * idle)

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


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("stickman")
    clock = pygame.time.Clock()

    man = Man((WIDTH / 2, HEIGHT / 2))
    skeleton = Skeleton()

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 20.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE):
                running = False

        cursor = Vector2(pygame.mouse.get_pos())
        if dt > 0:
            man.update(cursor, dt)

        screen.fill(BLACK)
        skeleton.draw(screen, man)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

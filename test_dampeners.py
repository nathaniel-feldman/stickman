"""v1.5 Phase 4 dampener test (headless).

Scripts 20 startles and verifies the mandated dampeners: he becomes a jumpy
individual (sensitivity drift, capped), his feelings floor instead of
pinning (trust >= 0.05, cursor_valence >= -0.7, valence decay never stops),
and calm time heals him back to a livable state. Also round-trips
soul.json persistence. Run: python test_dampeners.py
"""
import math
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from pygame.math import Vector2

import stickman as sm

pygame.init()
pygame.display.set_mode((sm.WIDTH, sm.HEIGHT))
DT = 1 / 60.0
FAR = Vector2(5, 5)


def step(man, world, cursor, seconds):
    for _ in range(int(seconds / DT)):
        man.update(Vector2(cursor), DT, world)
        assert -1.0 <= man.valence <= 1.0 and 0.0 <= man.arousal <= 1.0
        assert man.trust >= sm.TRUST_FLOOR - 1e-9, "trust floor broken"
        assert man.cursor_valence >= sm.CV_FLOOR - 1e-9, "cv floor broken"
        assert man.startle_sens <= sm.SENS_MAX + 1e-9, "sens cap broken"


def jerk(man, world):
    c = Vector2(man.pos) + Vector2(150, 0)
    for _ in range(12):
        c.x -= 25  # 1500 px/s straight at him
        man.update(Vector2(c), DT, world)


def main():
    man = sm.Man((sm.WIDTH / 2, sm.HEIGHT / 2))
    world = sm.World()
    step(man, world, FAR, 3.0)

    # --- 20 startles: he becomes jumpy, everything floors, nothing pins ---
    for i in range(20):
        pre = man.state
        jerk(man, world)
        assert man.state == sm.FLEE, f"startle {i} ignored (was {pre})"
        step(man, world, FAR, 8.0)
    print(f"after 20 startles: trust {man.trust:.3f}  cursor_valence "
          f"{man.cursor_valence:+.2f}  startle_sens {man.startle_sens:.2f}  "
          f"valence {man.valence:+.2f}  startles {man.startles}")
    assert man.startles == 20
    assert man.startle_sens > 1.3, "did not become jumpy"
    assert man.trust == sm.TRUST_FLOOR, "trust should sit on its floor"
    assert man.cursor_valence == sm.CV_FLOOR, "cv should sit on its floor"
    assert man.valence > -1.0, "valence pinned at the bottom"
    jumpy_sens = man.startle_sens

    # --- a jumpy individual startles harder than a fresh one ---
    fresh = sm.Man((sm.WIDTH / 2, sm.HEIGHT / 2))
    w2 = sm.World()
    step(fresh, w2, FAR, 3.0)
    v_fresh = fresh.valence
    jerk(fresh, w2)
    drop_fresh = v_fresh - fresh.valence
    drop_jumpy = 0.4 * jumpy_sens
    print(f"startle valence hit: fresh {drop_fresh:.2f} vs jumpy "
          f"{drop_jumpy:.2f} (x{jumpy_sens:.2f} sensitivity)")
    assert drop_jumpy > drop_fresh * 1.2

    # --- calm time heals: recoverable, but the jumpiness lingers ---
    step(man, world, FAR, 300.0)
    print(f"after 5 min calm: valence {man.valence:+.2f}  arousal "
          f"{man.arousal:.2f}  cursor_valence {man.cursor_valence:+.2f}  "
          f"startle_sens {man.startle_sens:.3f}  region "
          f"{sm.emotion_region(man.valence, man.arousal)}")
    assert man.valence > -0.15, "mood did not recover"
    assert man.arousal < 0.35, "arousal did not settle"
    assert man.cursor_valence > sm.CV_FLOOR + 0.2, "dread did not heal at all"
    assert man.startle_sens > 1.3, "jumpiness should heal much slower"

    # --- soul.json round-trip (preserving any real soul) ---
    path = sm.soul_path()
    backup = None
    if os.path.exists(path):
        with open(path) as f:
            backup = f.read()
    try:
        sm.save_soul(man)
        reborn = sm.Man((100, 100))
        sm.load_soul(reborn)
        assert abs(reborn.trust - man.trust) < 1e-3
        assert abs(reborn.cursor_valence - man.cursor_valence) < 1e-3
        assert abs(reborn.startle_sens - man.startle_sens) < 1e-3
        assert reborn.startles == 20
        os.remove(path)
        rebirth = sm.Man((100, 100))
        sm.load_soul(rebirth)  # no file: identical fresh defaults
        assert rebirth.trust == sm.TRUST_START and rebirth.startles == 0
        print("soul.json round-trip + rebirth ok")
    finally:
        if backup is not None:
            with open(path, "w") as f:
                f.write(backup)

    # --- dread keeps him at a distance ---
    assert man.dread > 0.0 and man._stop_dist() > sm.STOP_DIST + 10
    print(f"dread standoff: watches from {man._stop_dist():.0f}px "
          f"(base {sm.STOP_DIST:.0f}px)")

    print("ALL DAMPENER CHECKS PASS")


if __name__ == "__main__":
    main()

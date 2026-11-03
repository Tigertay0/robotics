"""Plan v3: both robots' routes, piece motion and score, for tools/match_sim.py.

Frame: inches, origin = inside corner of the bottom-left PVC, x 0..93.08, y 0..40.2.
Heading 0 = east (+x), 90 = north. Robot A (mecanum) never turns: heading 0.

Start positions (rule summary p.3/p.12): A in Zone 5 (the large box), B in the small box.
Footprints come from the build-manual models (docs/manual/*.glb): A 16.2 x 10.9 in;
B 16.7 x 8.1 in with the claw raised in front, 12.9 x 8.1 in below 2.75 in (plow tips),
which is what touches ducks, poms, stacks and the PVC (the raised claw passes over them).

Why this order:
  * B's first run stays SOUTH of the duck lane: its hook drags the lower cup (and its 3
    hidden poms) west along the lower tape, then a 20 deg pivot rolls the cup upright off
    the tape into Zone 5, west of everything B and A use later. B grabs the red pom.
    The ducks are never near B.
  * A strafes north under the red pom stack and the upper cup, pushing both into Zone 1,
    so the lane west of the red duck is free; then it swallows the 5 ducks along the lane.
    The lane is first in, first out: the red duck leaves first.
  * B pushes the other 4 stacks only after A is east of the centre line, then drops down
    to the bottom wall east of the cup, knocks pickleball 1 toward the platform and puts
    the red pom on the platform.
  * A drops its last two ducks (Zone 5, then Zone 3) only after B has passed below.
"""
import math

from match_sim import Path, pose

A_FULL = (-4.76, 11.40, -5.43, 5.43)
B_FULL = (-4.82, 11.89, -4.06, 4.06)
B_LOW = (-4.82, 8.06, -4.06, 4.06)
A_MOUTH, A_EXIT = 11.40, -5.30
LANE_Y = 25.44
DUCK_X = {"red": 53.2, "green": 61.2, "lavender": 69.2, "blue": 77.2, "yellow": 85.2}
STACK_X = {"gold": 8.0, "turquoise": 16.0, "lavender": 24.0, "green": 32.0, "red": 40.0}
CUP_UP, CUP_LOW = (46.6, 25.4), (46.6, 12.2)
PB4 = (46.6, -0.6)
R_DUCK, R_STACK, R_CUP, R_POM, R_PB = 1.14, 1.10, 1.82, 0.75, 1.46
POCKET = 4.92                      # B's plow pocket face, ahead of its centre

# tunables (inches, seconds)
P = {
    "A_start": (28.5, 5.7), "A_wait": (14.3, 17.9), "A_push_x": 39.26, "A_push_y": 28.6,
    "A_z3_y": 21.0, "A_z5_x": 38.5, "A_z3_x": 41.0,
    "B_start": (63.8, 7.15), "B_approach": 8.4, "B_drag_to": 37.0, "B_pivot": 20.0, "B_backoff": 2.5, "B_grab_x": 41.8,
    "B_lane_y": 17.5, "B_gold_x": 11.0, "B_gold_to": 29.0,
    "B_descent_x": 32.5, "B_r1": 5.0, "B_r2": 4.9, "B_stop_x": 58.9,
    # the robots do not talk to each other: every hand-off is a fixed match time, copied into
    # code/robot_*/main.c. Each one is padded past the moment the simulation says it is safe
    # (checked below), so a slower real robot still keeps the order.
    "T_A_east": 12.0, "T_B_north": 26.0, "T_A_west": 60.0, "T_A_down": 66.0,
}


def handoff(name, safe_t):
    t = P[name]
    assert t >= safe_t, f"{name} = {t:.1f} s is before the safe time {safe_t:.1f} s"
    return t


def build():
    pieces, events = [], []
    A = Path(0.0, *P["A_start"], 0.0, speed=9.0)
    B = Path(0.0, *P["B_start"], 180.0, speed=8.0, turn_rate=110.0)

    B.wait_until(0.6, label="B: wait_for_light(); hook down")
    B.fwd(P["B_approach"], speed=6.0, label="B: forward_in(8.4): hook meets the lower cup")
    t_cup0 = B.t
    xc, yc, hc = B.state
    o = (CUP_LOW[0] - xc, CUP_LOW[1] - yc)
    B.fwd(xc - P["B_drag_to"], speed=5.0, label="B: drag_and_flip_cup(18.4): hook drags the cup (and its 3 poms) west along the tape")
    t_drag1 = B.t
    xd, yd, _ = B.state
    B.turn(P["B_pivot"], label="B: drag_and_flip_cup(): turn_deg(+20), the wing rolls the cup upright off the tape")
    t_cup1 = B.t
    xb, yb, hb = B.state
    dth = math.radians(hb - hc)
    cup_final = (xb + o[0] * math.cos(dth) - o[1] * math.sin(dth), yb + o[0] * math.sin(dth) + o[1] * math.cos(dth))
    B.fwd(-P["B_backoff"], label="B: forward_in(-2.5): back off the cup, hook up")
    B.turn(180.0 - hb, label="B: turn_deg(-20): square up facing west")
    x0, _, _ = B.state
    B.fwd(x0 - P["B_grab_x"], label="B: forward_in(-2.45): claw clear of the cup")
    t_grab = B.t
    B.wait(3.0, label="B: grab_red_pom(): camera, approach, claw closes, arm up")

    # ============================================================ Robot A, part 1
    A.go(P["A_start"][0], P["A_wait"][1], label="A: move_in(0, 12.2): north out of Zone 5")
    A.go(*P["A_wait"], label="A: move_in(-14.2, 0): west end of Zone 3, clear of the cup drag")
    A.wait_until(handoff("T_A_east", t_grab + 3.0), label="A: wait until 12 s: B drags the lower cup west under Zone 3")
    A.go(P["A_push_x"], P["A_wait"][1], label="A: move_in(25, 0): under the red stack")
    t_push0 = A.t
    A.go(P["A_push_x"], P["A_push_y"], speed=5.0, label="A: move_in(0, 10.7): side pushes the red stack + upper cup north")
    t_push1 = A.t
    A.go(P["A_push_x"], LANE_Y, label="A: move_in(0, -3.2): onto the duck lane")
    t_lane0 = A.t
    A.go(75.9, LANE_Y, speed=5.5, label="A: follow_tape_east(36.6): swallow the 5 ducks")
    t_lane1 = A.t
    drops = []

    def drop(zone):
        drops.append((zone, A.t))
        A.wait(0.8, label="A: drop_one_duck(): pin B closes, exit A opens")
        x, y, _ = A.state
        A.go(x + 2.5, y, speed=4, label="A: drop_one_duck(): creep 2.5 in, exit A closes")

    A.go(75.9, 33.0, label="A: move_in(0, 7.6): into Zone 2")
    drop("Z2")
    A.go(78.4, 17.6, label="A: move_in(0, -15.4): down into Zone 4")
    A.go(77.4, 17.6, label="A: move_in(-1, 0)")
    drop("Z4")
    A.go(79.9, 24.9, label="A: move_in(0, 7.3): back onto the lane line")
    A.go(49.3, 24.9, label="A: move_in(-30.6, 0): west along the empty lane")
    A.go(49.3, 28.2, label="A: move_in(0, 3.3): Zone 1")
    drop("Z1")
    A.go(51.8, P["A_z3_y"], label="A: move_in(0, -7.2): wait above the lower tape")
    A.go(52.6, P["A_z3_y"], label="A: move_in(0.8, 0)")

    # ============================================================ Robot B, rest
    t_clear = time_when(A.keys, lambda p: p[0] >= 55.0, t_lane0, t_lane1)
    B.wait_until(handoff("T_B_north", t_clear), label="B: wait until 26 s (holding the red pom): A is past the centre line")
    B.turn(-90.0, label="B: turn_deg(-90): face north")
    lane_y = P["B_lane_y"]
    x0, y0, _ = B.state
    B.fwd(lane_y - y0, label="B: forward_in(9.5): up to the Zone 3 travel line")
    B.turn(90.0, label="B: turn_deg(+90): face west")
    order = (("green", 32.0, 33.0), ("lavender", 24.0, 33.0), ("turquoise", 16.0, 33.0),
             ("gold", P["B_gold_x"], P["B_gold_to"]))
    for name, bx, sy_to in order:
        sx = STACK_X[name]
        x0, _, _ = B.state
        B.fwd(x0 - bx, label=f"B: forward_in(): along Zone 3 to the {name} stack")
        t_turn = B.t
        B.turn(-90.0, label="B: turn_deg(-90): face north")
        t0 = B.t
        push = sy_to - R_STACK - POCKET - lane_y
        B.fwd(push, speed=4.5, label=f"B: push_stack_north(): {name} stack into Zone 1")
        t1 = B.t
        B.fwd(-push, label="B: push_stack_north(): back off")
        t_meet = t0 + max(0.0, 25.4 - R_STACK - POCKET - lane_y) / 4.5
        pieces.append({"name": f"stack {name}", "kind": "stack", "color": name, "r": R_STACK, "h": 2.72,
                       "track": [(0, sx, 25.4), (t_meet, sx, 25.4), (t1, sx, sy_to), (120, sx, sy_to)],
                       "contact": [{"robot": "B", "t0": t_turn, "t1": t1 + 1.6}]})
        events.append((round(t1, 1), 8, 0, f"{name} stack -> zone 1"))
        if name != "gold":
            B.turn(90.0, label="B: turn_deg(+90): face west")
    B.turn(-90.0, label="B: turn_deg(-90): face east")
    x0, _, _ = B.state
    B.fwd(P["B_descent_x"] - x0, label="B: forward_in(21.5): east along Zone 3")
    t_arc = B.t
    B.arc(P["B_r1"], -90.0, speed=5.0, label="B: arc_r(5.0, -90): down toward the bottom wall")
    B.arc(P["B_r2"], 90.0, speed=5.0, label="B: arc_r(4.9, +90): face east along the wall")
    t_ball0 = B.t
    x0, _, _ = B.state
    B.fwd(P["B_stop_x"] - x0, speed=4.5, label="B: hook knocks pickleball 1 off its post; plow pushes it toward the platform")
    t_ball1 = B.t
    B.wait(1.5, label="B: arm to ARM_PLATFORM, open claw: red pom on the platform")
    t_red = B.t
    B.wait_until(118.0, label="B: done")

    # ============================================================ Robot A, part 2 (after B has left Zone 3)
    A.wait_until(handoff("T_A_west", t_ball0), label="A: wait until 60 s: B has left Zone 3")
    A.go(P["A_z5_x"], P["A_z3_y"], label="A: move_in(-14.1, 0): west through Zone 3")
    t_down = time_when(B.keys, lambda p: p[0] - 4.82 >= P["A_z5_x"] + A_FULL[1] + 0.5, t_ball0, t_ball1)
    A.wait_until(handoff("T_A_down", t_down), label="A: wait until 66 s: B is parked at the platform")
    A.go(P["A_z5_x"], 6.8, label="A: move_in(0, -14.2): down into Zone 5")
    drop("Z5")
    A.go(P["A_z3_x"], P["A_z3_y"], label="A: move_in(0, 14.2): back up into Zone 3")  # creep left A at x 41
    drop("Z3")
    A.wait_until(118.0, label="A: done")

    drop_pos = {}
    for (zone, td) in drops:
        x, y, _ = pose(A.keys, td)
        drop_pos[zone] = (td, x + A_EXIT, y)
    # the lane is first in, first out: the red duck (swallowed first) leaves first
    zone_for = dict(zip(["red", "green", "lavender", "blue", "yellow"], [z for z, _ in drops]))
    for name in ["red", "green", "lavender", "blue", "yellow"]:
        dx = DUCK_X[name]
        tc = time_when(A.keys, lambda p: p[0] + A_MOUTH >= dx - R_DUCK, t_lane0, t_lane1)
        td, px, py = drop_pos[zone_for[name]]
        pieces.append({"name": f"duck {name}", "kind": "duck", "color": name, "r": R_DUCK, "h": 1.6,
                       "track": [(0, dx, LANE_Y), (tc, dx, LANE_Y), (td, px, py), (120, px, py)],
                       "carried_by": "A", "carried_from": tc, "carried_to": td,
                       "contact": [{"robot": "A", "t0": tc - 0.6, "t1": tc + 0.1}, {"robot": "A", "t0": td - 0.1, "t1": td + 1.6}]})
        events.append((round(td, 1), 1, 1, f"duck in {zone_for[name]}"))

    up_final = (46.6, P["A_push_y"] + 5.43 + R_CUP)
    red_final = (40.0, P["A_push_y"] + 5.43 + R_STACK)
    pieces.append({"name": "stack red", "kind": "stack", "color": "red", "r": R_STACK, "h": 2.72,
                   "track": [(0, STACK_X["red"], 25.4), (t_push0 + 1.0, STACK_X["red"], 25.4), (t_push1, *red_final), (120, *red_final)],
                   "contact": [{"robot": "A", "t0": t_push0, "t1": t_push1 + 0.3}]})
    events.append((round(t_push1, 1), 8, 0, "red stack -> zone 1 (pushed by A)"))
    pieces.append({"name": "cup upper", "kind": "cup", "color": "teal", "r": R_CUP, "h": 5.7,
                   "track": [(0, *CUP_UP), (t_push0 + 1.2, *CUP_UP), (t_push1, *up_final), (120, *up_final)],
                   "contact": [{"robot": "A", "t0": t_push0, "t1": t_push1 + 0.3}]})
    # its 2 hidden poms stay inside the upside-down cup and move with it

    cup_drag = (xd + o[0], yd + o[1])
    pieces.append({"name": "cup lower", "kind": "cup", "color": "green", "r": R_CUP, "h": 5.7,
                   "track": [(0, *CUP_LOW), (t_cup0, *CUP_LOW), (t_drag1, *cup_drag), (t_cup1, *cup_final), (120, *cup_final)],
                   "contact": [{"robot": "B", "t0": 0.6, "t1": t_cup1 + 1.2}]})
    events.append((round(t_cup1, 1), 21, 0, "lower cup upright in Zone 5 (off tape)"))
    spill = [(cup_final[0] - 2.6, cup_final[1] - 1.0), (cup_final[0] - 0.6, cup_final[1] - 3.0)]
    for k, c in enumerate(("turquoise", "green")):
        pieces.append({"name": f"pom hidden {c}", "kind": "pom", "color": c, "r": R_POM, "h": 1.5,
                       "track": [(0, *CUP_LOW), (t_cup0, *CUP_LOW), (t_drag1, *cup_drag), (t_cup1, *spill[k]), (120, *spill[k])],
                       "contact": [{"robot": "B", "t0": t_cup0 - 0.3, "t1": t_grab + 0.5}]})
    xg, yg, _ = pose(B.keys, t_grab)
    red_at = (xg - 9.5, yg - 2.0)
    xr, yr, _ = pose(B.keys, t_red)
    plat = (xr + 12.5, yr)
    pieces.append({"name": "mystery red pom", "kind": "pom", "color": "red", "r": R_POM, "h": 1.5,
                   "track": [(0, *CUP_LOW), (t_cup0, *CUP_LOW), (t_drag1, *cup_drag), (t_cup1, *red_at), (t_grab + 2.5, *red_at),
                             (t_red, *plat), (120, *plat)],
                   "carried_by": "B", "carried_from": t_grab + 2.5, "carried_to": t_red,
                   "contact": [{"robot": "B", "t0": t_cup0 - 0.3, "t1": t_grab + 2.6}]})
    events.append((round(t_red, 1), 51, 0, "red pom alone on the platform"))
    # the hook knocks the ball off its post; it then rides in front of the right plow wing
    ball_track = [(0, *PB4), (t_ball0, *PB4)]
    tt = t_ball0 + 0.5
    while tt < t_ball1:
        bx_, by_, _ = pose(B.keys, tt)
        ball_track.append((tt, bx_ + B_LOW[1] + R_PB + 0.3, max(by_ - 2.6, 1.6)))
        tt += 0.25
    ball_track += [(t_ball1 + 1.0, 75.0, 5.5), (120, 75.0, 5.5)]
    pieces.append({"name": "pickleball 1", "kind": "pickleball", "color": "pink", "r": R_PB, "h": 5.2,
                   "track": ball_track,
                   "contact": [{"robot": "B", "t0": t_arc, "t1": t_ball1 + 1.2}]})
    events.append((round(t_ball1, 1), 8, 0, "pickleball under the platform"))

    statics = [
        {"name": "ring post L", "x": -0.65, "y": 25.48, "r": 1.07},
        {"name": "ring post B", "x": 21.85, "y": -0.65, "r": 1.07},
        {"name": "bottle enclosure", "box": (-1.46, 1.9, 4.04, 12.9)},
        {"name": "pickleball top 1", "x": 55.6, "y": 40.85, "r": R_PB},
        {"name": "pickleball top 2", "x": 66.5, "y": 40.85, "r": R_PB},
        {"name": "pickleball right", "x": 93.73, "y": 25.48, "r": R_PB},
        {"name": "big duck on platform", "box": (71.1, 1.9, 76.0, 6.7)},
    ]
    return {
        "robots": {"A": {"keys": A.keys, "labels": A.labels, "full": A_FULL, "low": A_FULL},
                   "B": {"keys": B.keys, "labels": B.labels, "full": B_FULL, "low": B_LOW}},
        "pieces": pieces, "statics": statics, "events": events,
        "meta": {"end": 120.0, "field": {
            "interior": [0, 0, 93.08, 40.2],
            "tape": {"centre_vertical": [45.66, 0, 47.54, 40.2], "upper_lane": [0, 24.5, 93.08, 26.38],
                     "lower": [3.6, 11.25, 93.08, 13.13], "platform_edge": [68.66, 0, 70.54, 11.25]},
            "zones": {"Z1": [0, 26.38, 45.66, 40.2], "Z2": [47.54, 26.38, 93.08, 40.2], "Z3": [0, 13.13, 45.66, 24.5],
                      "Z4": [47.54, 13.13, 93.08, 24.5], "Z5 (large start box)": [4.04, 0, 45.66, 11.25]},
            "small_start_box": [47.54, 0, 68.66, 11.25], "raised_platform": [70.54, -1.46, 94.54, 11.04],
            "bottle_enclosure": [0, 1.9, 4.04, 12.9]}},
    }


def time_when(keys, cond, t0, t1, dt=0.02):
    t = t0
    while t <= t1:
        if cond(pose(keys, t)):
            return t
        t += dt
    return t1

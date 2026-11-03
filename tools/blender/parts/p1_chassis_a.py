"""PRINT 1/4 - Robot A "Duck Runner" printed chassis with the duck lane built in.

One print (team rule: 4 parts total, any size up to the Ender 3 V3 SE bed,
220 x 220 x 250 mm). Replaces the KIPR metal chassis, standoffs, motor brackets
and the rear of the metal duck lane.

Layout (robot frame: +X forward, +Y left, Z up from the FLOOR, mm):
  * deck: 214 x 180 x 5 mm, its underside 46 mm above the floor, so a 1.6 in
    (40.6 mm) duck passes under it with 5 mm to spare;
  * duck lane: two walls along the centre, 45.7 mm (1.8 in) apart, hanging from
    the deck and stopping 4 mm ABOVE the floor (the channel never touches it);
    open at the rear (ducks leave there) and at the front (the kit-metal intake
    extension with the funnel and intake gate C bolts onto the wall ends);
  * gate slots through the deck for exit gate A and pin gate B, servo screw holes
    beside them; lane-full touch switch window in the right lane wall;
  * two side walls carrying the 4 motors: a window per corner for the motor body
    and 4 ear screw holes; axle height = mecanum wheel radius (30 mm);
  * front and rear bumper plates either side of the lane, and the whole deck,
    drilled with 4.4 mm holes on an 8 mm grid (KIPR printed-chassis convention:
    8-32 / M4 screws, LEGO parts via screws) for extra sensors and components;
  * Wombat case holes on its 112.7 x 83.8 mm pattern.
Rules check (rule summary p.12): whole robot within 11.25 x 21.125 x 12 in at the
start; asserted below for the width with wheels.

MEASURE before printing: motor body, ear screw pitch and the ear-to-shaft-face
distance (servo-style case, values below are estimates from the Blender model),
mecanum wheel diameter/width, duck height, Wombat case holes.
Print upside down (deck on the bed), 3 walls, 20 % infill, no supports.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

IN = 25.4
# ---- overall
L, W = 214.0, 180.0                 # chassis footprint (bed is 220 x 220)
DECK_T = 5.0
DUCK_H = 1.6 * IN                   # 40.6 mm (STRATEGY.md); MEASURE
DECK_Z = DUCK_H + 5.4               # deck underside height above the floor (46 mm)
LANE_W = 1.8 * IN                   # inside width of the duck channel
LANE_T = 3.5
LANE_FLOOR_GAP = 4.0                # lane walls stop this far above the floor
SIDE_T = 4.0
SIDE_Z0 = 14.0                      # side walls stop 14 mm above the floor
# ---- wheels and motors (KIPR black gear motor, servo-style case; estimates)
WHEEL_D, WHEEL_W = 60.0, 28.0       # 60 mm mecanum
AXLE_Z = WHEEL_D / 2
WHEEL_X = 88.0                      # front/rear axle positions (+/-)
MOTOR_LEN, MOTOR_THK = 40.6, 20.3   # body: length along X, thickness along Z
SHAFT_FROM_END = 10.2               # shaft centre from the outer end of the body
EAR_PITCH = 48.5                    # ear screw holes along the body
EAR_ACROSS = 10.0                   # the 2 holes in each ear
EAR_TO_FACE = 12.0                  # ear plane (wall outer face) to the shaft face
SHAFT_STICKOUT = 6.0                # shaft + hub beyond the face before the wheel
START_BOX_W = 11.25 * IN
# ---- lane features (lane rear = chassis rear)
X_REAR, X_FRONT = -L / 2, L / 2
GATE_A_X = X_REAR + 10.0            # exit gate
GATE_B_X = X_REAR + 66.0            # pin gate (2.6 in from the rear, as in the model)
TOUCH_X = X_REAR + 31.0
SLOT_W = 9.0
SERVO_PITCH = 48.5
GRID = 8.0
HOLE = 4.4
WOMBAT = (112.7, 83.8)              # PCB hole pattern; centred at WOMBAT_C
WOMBAT_C = (-15.0, 0.0)

half, side_y = LANE_W / 2, W / 2
total_w = W + 2 * (EAR_TO_FACE + SHAFT_STICKOUT + WHEEL_W)
assert total_w <= START_BOX_W - 5, f"robot {total_w:.0f} mm wide > start box {START_BOX_W:.0f} mm"
assert DECK_Z - DUCK_H >= 4, "duck would hit the deck"

out = pl.out_dir_from_args()
pl.reset()
deck_top = DECK_Z + DECK_T

chassis = pl.box_from((X_REAR, -side_y, DECK_Z), (X_FRONT, side_y, deck_top), "p1_chassis_a")
# duck lane walls (overlap the deck by 0.5 mm so they fuse)
for s in (-1, 1):
    y0, y1 = (half, half + LANE_T) if s > 0 else (-half - LANE_T, -half)
    pl.union(chassis, pl.box_from((X_REAR, y0, LANE_FLOOR_GAP), (X_FRONT, y1, DECK_Z + 0.5)))
# side walls (motor carriers)
for s in (-1, 1):
    y0, y1 = (side_y - SIDE_T, side_y) if s > 0 else (-side_y, -side_y + SIDE_T)
    pl.union(chassis, pl.box_from((X_REAR, y0, SIDE_Z0), (X_FRONT, y1, DECK_Z + 0.5)))
# front and rear bumper plates either side of the lane (accessory mounting)
BUMPER_T = 4.0
for xb in (X_FRONT - BUMPER_T, X_REAR):
    for s in (-1, 1):
        y0, y1 = (half + LANE_T - 0.5, side_y - SIDE_T + 0.5) if s > 0 else (-side_y + SIDE_T - 0.5, -half - LANE_T + 0.5)
        pl.union(chassis, pl.box_from((xb, y0, SIDE_Z0), (xb + BUMPER_T, y1, DECK_Z + 0.5)))
# mid cross ribs between lane and side walls (stiffness), clear of the motors
for xr in (-30.0, 30.0):
    for s in (-1, 1):
        y0, y1 = (half + LANE_T - 0.5, side_y - SIDE_T + 0.5) if s > 0 else (-side_y + SIDE_T - 0.5, -half - LANE_T + 0.5)
        pl.union(chassis, pl.box_from((xr - 2, y0, DECK_Z - 12), (xr + 2, y1, DECK_Z + 0.5)))

# ---- motor windows + ear screw holes (4 corners)
motor_boxes = []
for xw in (WHEEL_X, -WHEEL_X):
    out_end = xw + (SHAFT_FROM_END if xw > 0 else -SHAFT_FROM_END)       # outer end of the body
    body_x0, body_x1 = sorted((out_end, out_end - (MOTOR_LEN if xw > 0 else -MOTOR_LEN)))
    body_cx = (body_x0 + body_x1) / 2
    motor_boxes.append((body_x0, body_x1))
    assert X_REAR + 2 < body_cx - EAR_PITCH / 2 and body_cx + EAR_PITCH / 2 < X_FRONT - 2, "ear holes off the chassis"
    for s in (-1, 1):
        pl.difference(chassis, pl.box_from((body_x0 - 0.4, s * side_y - 10, AXLE_Z - MOTOR_THK / 2 - 0.4),
                                           (body_x1 + 0.4, s * side_y + 10, AXLE_Z + MOTOR_THK / 2 + 0.4)))
        ears = [(body_cx + dx, s * (side_y - SIDE_T / 2), AXLE_Z + dz)
                for dx in (-EAR_PITCH / 2, EAR_PITCH / 2) for dz in (-EAR_ACROSS / 2, EAR_ACROSS / 2)]
        pl.hole_grid(chassis, ears, 2.6, SIDE_T + 4, axis="Y", segments=16)

# ---- gate slots + servo holes; touch switch window
for gx, sside in ((GATE_A_X, +1), (GATE_B_X, -1)):
    pl.difference(chassis, pl.box(SLOT_W, LANE_W - 2, DECK_T + 4, center=(gx, 0, DECK_Z + DECK_T / 2)))
    pads = [(gx + dx, sside * (half + LANE_T + 9), DECK_Z + DECK_T / 2)
            for dx in (-SERVO_PITCH / 2, SERVO_PITCH / 2) if X_REAR + 4 < gx + dx < X_FRONT - 4]
    pl.hole_grid(chassis, pads, 2.2, DECK_T + 4, segments=16)
pl.difference(chassis, pl.box(14, LANE_T + 4, 10, center=(TOUCH_X, -(half + LANE_T / 2), 16)))
pl.hole_grid(chassis, [(TOUCH_X + dx, -(half + LANE_T / 2), 16) for dx in (-9.5, 9.5)], 2.2, LANE_T + 4, axis="Y", segments=16)
# front joint for the kit-metal intake extension (4x12 plates bolted outside the lane walls)
pl.hole_grid(chassis, [(X_FRONT - dx, s * (half + LANE_T / 2), z) for s in (-1, 1) for dx in (8, 20) for z in (15, 35)],
             HOLE, LANE_T + 4, axis="Y", segments=16)

# ---- Wombat holes, then the 8 mm accessory grid on the deck (kept clear of everything)
wombat_pts = [(WOMBAT_C[0] + sx * WOMBAT[0] / 2, WOMBAT_C[1] + sy * WOMBAT[1] / 2)
              for sx in (-1, 1) for sy in (-1, 1)]
pl.hole_grid(chassis, [(x, y, DECK_Z + DECK_T / 2) for x, y in wombat_pts], 3.2, DECK_T + 4, segments=16)


def deck_free(x, y):
    if abs(abs(y) - (half + LANE_T / 2)) < LANE_T / 2 + 3.5:      # over a lane wall
        return False
    if abs(y) > side_y - SIDE_T - 3.5:                            # over a side wall
        return False
    if any(abs(x - gx) < SLOT_W / 2 + 4 for gx in (GATE_A_X, GATE_B_X)) and abs(y) < half + LANE_T + 16:
        return False                                              # gate slots + servo pads
    if any(abs(x - xr) < 6 for xr in (-30.0, 30.0)) or abs(x - X_FRONT) < 8 or abs(x - X_REAR) < 8:
        return False                                              # ribs / bumpers
    if any((x - wx) ** 2 + (y - wy) ** 2 < 7 ** 2 for wx, wy in wombat_pts):
        return False
    return True


xs = [X_REAR + 12 + GRID * i for i in range(int((L - 24) // GRID) + 1)]
ys = [GRID * j - GRID * int(side_y // GRID) for j in range(2 * int(side_y // GRID) + 1)]
grid_pts = [(x, y, DECK_Z + DECK_T / 2) for x in xs for y in ys if deck_free(x, y)]
pl.hole_grid(chassis, grid_pts, HOLE, DECK_T + 4)

# front + rear bumper accessory grids (8 mm pitch, both bumpers)
bump_pts = []
for xb in (X_FRONT - BUMPER_T / 2, X_REAR + BUMPER_T / 2):
    for y in ys:
        if half + LANE_T + 4 < abs(y) < side_y - SIDE_T - 4:
            for z in (SIDE_Z0 + 6 + GRID * k for k in range(int((DECK_Z - SIDE_Z0 - 10) // GRID) + 1)):
                bump_pts.append((xb, y, z))
pl.hole_grid(chassis, bump_pts, HOLE, BUMPER_T + 4, axis="X")

pl.finish(chassis, "p1_chassis_a", out, print_class="team",
          extra={"robot_width_with_wheels_mm": round(total_w, 1), "deck_underside_mm": DECK_Z,
                 "lane_floor_gap_mm": LANE_FLOOR_GAP, "accessory_holes": len(grid_pts) + len(bump_pts)},
          notes=f"robot ~{total_w:.0f} mm wide with wheels (start box {START_BOX_W:.0f}); deck underside "
                f"{DECK_Z:.0f} mm, lane {LANE_W:.1f} mm wide stopping {LANE_FLOOR_GAP:.0f} mm above the floor; "
                f"{len(grid_pts) + len(bump_pts)} accessory holes (4.4 mm on 8 mm); print deck-down, no supports")

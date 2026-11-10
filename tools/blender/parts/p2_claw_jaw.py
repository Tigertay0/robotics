"""PRINT 2/4 - Robot B claw jaw: ONE solid piece (base plate + fixed finger + pom pad).

Team decision (Nov 10 2026): the claw must be a single printed piece. The earlier geared
claw was three bodies printed in place (base + 2 fingers), which does not count as one.
Now only the fixed half is printed; the moving finger is a kit part:
  * a kit Servo hangs in a kit Servo Bracket under the base, shaft up through the base;
  * a Round Servo Horn sits on the shaft in the round recess on top of the base;
  * a 1 x 7 Liftarm bolted on that horn is the moving finger. It closes the pom against
    the printed pad and swings outward to open.

Part frame (mm): +Y = toward the pom (robot forward), Z up from the print bed.
MEASURE before printing: pom diameter, Round Servo Horn diameter and thickness, the servo
bracket's hole spacing, how far the servo shaft sticks up through a 4 mm plate.
Print flat (base on the bed), 3 walls, 20 % infill, no supports.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

BASE_W, BASE_L, BASE_T = 74.0, 70.0, 4.0
BASE_Y0 = -54.0                     # rear edge; front edge = BASE_Y0 + BASE_L = +16
PIVOT = (16.0, 0.0)                 # servo shaft = moving finger's pivot
POM_D = 1.6 * 25.4                  # 40.6 mm; MEASURE
SQUEEZE = 2.0                       # the closed claw is this much narrower than the pom
LIFTARM_W, LIFTARM_T = 7.8, 7.8     # LEGO beam section
HORN_D, HORN_T = 24.0, 3.5          # kit Round Servo Horn; MEASURE
SHAFT_HOLE_D = 10.0                 # servo spline boss
RECESS = 2.6                        # recess under the horn: room for the 2 M3 nuts under it
FINGER_W, FINGER_H = 9.0, 22.0      # fixed finger: thickness (X) and height (Z)
POM_GAP = 2.0                       # pom stays this far in front of the base plate
BRACKET_HOLES = [(PIVOT[0] + dx, dy) for dx in (-15.0, 15.0) for dy in (-25.0, 7.0)]   # kit Servo Bracket, 4 screws
REAR_ROWS = (BASE_Y0 + 8.0, BASE_Y0 + 16.0)   # rows of LEGO-pitch holes: bolt to the 1x5 liftarm on the arm tip

out = pl.out_dir_from_args()
pl.reset()

y_front = BASE_Y0 + BASE_L
moving_face_x = PIVOT[0] - LIFTARM_W / 2                 # liftarm's gripping face when closed (parallel to Y)
pad_face_x = moving_face_x - (POM_D - SQUEEZE)           # deepest point of the printed pad
pom_c = ((moving_face_x + pad_face_x) / 2, y_front + POM_GAP + POM_D / 2)
finger_x1 = pad_face_x + 0.1
finger_x0 = finger_x1 - FINGER_W
finger_y1 = pom_c[1] + 13.0
assert finger_x0 >= -BASE_W / 2, "fixed finger hangs off the base"
assert pom_c[1] - PIVOT[1] <= 40.0, "pom centre beyond the last hole of a 1x7 liftarm"

jaw = pl.rounded_plate(BASE_W, BASE_L, BASE_T, 6, center=(0, BASE_Y0 + BASE_L / 2, BASE_T / 2), name="p2_claw_jaw")
# fixed finger: a wall from the base out past the pom, with a pad that cradles the pom
pl.union(jaw, pl.box_from((finger_x0, -12.0, 0.0), (finger_x1, finger_y1, FINGER_H)))
pl.union(jaw, pl.box_from((finger_x1 - 0.5, pom_c[1] - 13.0, 0.0), (finger_x1 + 8.0, finger_y1, FINGER_H)))
pl.difference(jaw, pl.cyl(POM_D, FINGER_H + 4, (pom_c[0], pom_c[1], FINGER_H / 2), segments=96))
# gusset: the finger root is tied to the base over a long line (the wall above), plus a rib behind it
pl.union(jaw, pl.box_from((finger_x0, -30.0, 0.0), (finger_x1, -12.0, 10.0)))
# servo shaft hole + horn recess
pl.difference(jaw, pl.cyl(SHAFT_HOLE_D, 20, (PIVOT[0], PIVOT[1], BASE_T / 2)))
pl.difference(jaw, pl.cyl(HORN_D + 3, 2 * RECESS, (PIVOT[0], PIVOT[1], BASE_T)))
# holes: servo bracket (8-32) and the arm-tip mount (LEGO pitch)
pl.hole_grid(jaw, [(x, y, BASE_T / 2) for x, y in BRACKET_HOLES], pl.KIT_8_32_CLEAR, BASE_T + 2)
for y in REAR_ROWS:
    pl.hole_row(jaw, 5, pl.LEGO_PITCH, pl.LEGO_HOLE_D, start=(-16, y, BASE_T / 2), depth=BASE_T + 2, direction=(1, 0, 0))

pl.finish(jaw, "p2_claw_jaw", out, print_class="team",
          extra={"pivot_xy": list(PIVOT), "base_y0": BASE_Y0, "pom_centre_xy": [round(v, 2) for v in pom_c],
                 "closed_gap_mm": round(POM_D - SQUEEZE, 1), "bracket_holes_xy": BRACKET_HOLES,
                 "moving_finger": "kit 1 x 7 Liftarm on a Round Servo Horn (not printed)"},
          notes="ONE solid piece: base + fixed finger + pom pad. The moving finger is a kit 1x7 liftarm on a Round "
                "Servo Horn; kit Servo in a Servo Bracket under the base. Print flat, no supports.")

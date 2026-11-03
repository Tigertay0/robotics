"""L1 - Robot B claw palm + fixed jaw (large print class).

Claw points +Y. A standard servo sits INVERTED on top of the palm plate (tabs on
the plate, output shaft pointing down through the plate) so the moving jaw
(claw_jaw.py) swings underneath, in the same plane as the fixed jaw, and nothing
hangs below the jaws when the claw is lowered onto a pom.
The rear plate carries a horn recess for the WRIST servo (roll axis = Y) used to
flip Cup 1 upright.

Jaw geometry (shaft at X=+PIVOT_X, fixed-jaw inner face at X=-PIVOT_X):
  pom 38 mm grips at ~10 deg inward, Botguy 63.5 mm ~-2 deg, cup ~79 mm ~-8 deg,
  Big Duck 121 mm ~-33 deg (servo range +/-50 deg is enough).
MEASURE the team's servo and replace SERVO_* before printing.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

SERVO_L, SERVO_W = 40.8, 20.4       # body footprint (standard servo)
SERVO_TAB_PITCH = 48.5              # tab screw spacing along the body
SERVO_SHAFT_OFFSET = 10.2           # shaft centre from the body end
PIVOT_X = 30.0                      # shaft X; fixed jaw inner face at -PIVOT_X
PLATE_T = 6.0
PLATE_Z = 40.0                      # plate bottom (jaws hang below it)
JAW_LEN = 130.0
JAW_T = 7.0
JAW_Z0 = 2.0                        # jaw bottom (lowest point of the claw)
POM_D = 38.0
WRIST_HORN_D = 24.0                 # round horn recess (MEASURE)
WRIST_SCREW_R = 8.5
Y_BACK = -62.0

out = pl.out_dir_from_args()
pl.reset()

x_min = -PIVOT_X - JAW_T
x_max = PIVOT_X + SERVO_W / 2 + 14
plate = pl.box_from((x_min, Y_BACK, PLATE_Z), (x_max, 20, PLATE_Z + PLATE_T), "claw_palm")

# servo cut-out: body long axis along Y, shaft at (PIVOT_X, 0)
y_end = SERVO_SHAFT_OFFSET
pl.difference(plate, pl.box_from(
    (PIVOT_X - SERVO_W / 2 - 0.3, y_end - SERVO_L - 0.3, PLATE_Z - 1),
    (PIVOT_X + SERVO_W / 2 + 0.3, y_end + 0.3, PLATE_Z + PLATE_T + 1)))
y_mid = y_end - SERVO_L / 2
for dy in (-SERVO_TAB_PITCH / 2, SERVO_TAB_PITCH / 2):
    for dx in (-5, 5):
        pl.difference(plate, pl.cyl(pl.SERVO_HORN_SCREW_D + 0.6, 30,
                                    (PIVOT_X + dx, y_mid + dy, PLATE_Z)))

# fixed jaw: vertical blade from the plate down to JAW_Z0, running forward
pl.union(plate, pl.box_from((x_min, Y_BACK + 6, JAW_Z0), (-PIVOT_X, JAW_LEN, PLATE_Z + PLATE_T)))
# grip ribs on the inner face
for i in range(8):
    y = 25 + i * 12
    pl.union(plate, pl.box_from((-PIVOT_X - 0.5, y, JAW_Z0 + 2), (-PIVOT_X + 1.5, y + 3, PLATE_Z - 2)))
# pom notch near the tip (centres a 38 mm pom against the moving jaw)
NOTCH_DEPTH = 3.5   # into the 7 mm blade from its inner (+X) face
pl.difference(plate, pl.cyl(POM_D * 0.9, 80, (-PIVOT_X + POM_D * 0.45 - NOTCH_DEPTH, JAW_LEN - 22, 20)))

# rear wrist plate with a horn recess (wrist axis along Y)
wz = (JAW_Z0 + PLATE_Z + PLATE_T) / 2
wx = (x_min + x_max) / 2
pl.union(plate, pl.box_from((x_min, Y_BACK, JAW_Z0 + 6), (x_max, Y_BACK + 6, PLATE_Z + PLATE_T)))
pl.difference(plate, pl.cyl(WRIST_HORN_D + 0.6, 3.2, (wx, Y_BACK + 1.5, wz), axis="Y"))
pl.difference(plate, pl.cyl(8.0, 20, (wx, Y_BACK, wz), axis="Y"))
for a in range(45, 360, 90):
    r = math.radians(a)
    pl.difference(plate, pl.cyl(pl.SERVO_HORN_SCREW_D, 20,
                                (wx + WRIST_SCREW_R * math.cos(r), Y_BACK, wz + WRIST_SCREW_R * math.sin(r)),
                                axis="Y"))
# LEGO-pitch holes along the plate edge for bracing / camera mount
pl.hole_row(plate, 4, pl.LEGO_PITCH, pl.LEGO_HOLE_D,
            start=(-PIVOT_X + 7, -46, PLATE_Z + PLATE_T / 2), depth=PLATE_T + 2, direction=(0, 1, 0))

pl.finish(plate, "claw_palm", out, print_class="large",
          notes="print plate-down; servo inverted on top, horn below; moving jaw = claw_jaw.stl")

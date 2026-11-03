"""M2 - Robot B moving jaw, bolts to the claw servo's round horn (mid class).

Hub centre = servo shaft. Arm runs along +Y; inner (gripping) face is -X.
Do NOT print a splined hub (GCER 2026: printed splines fail) - screw through the
stock horn into the 4 pilot holes instead.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

HORN_D = 24.0          # stock round horn diameter (MEASURE)
HORN_SCREW_R = 8.5
HUB_D = 34.0
ARM_LEN = 128.0
ARM_T = 10.0
JAW_Z0, JAW_Z1 = 2.0, 30.0
POM_D = 38.0

out = pl.out_dir_from_args()
pl.reset()

jaw = pl.cyl(HUB_D, 6, (0, 0, JAW_Z1 - 3), name="claw_jaw")
pl.difference(jaw, pl.cyl(HORN_D + 0.6, 2.6, (0, 0, JAW_Z1 - 1.2)))     # horn seat
pl.difference(jaw, pl.cyl(6.5, 20, (0, 0, JAW_Z1)))                     # shaft screw access
for a in range(45, 360, 90):
    r = math.radians(a)
    pl.difference(jaw, pl.cyl(1.8, 20, (HORN_SCREW_R * math.cos(r), HORN_SCREW_R * math.sin(r), JAW_Z1)))

pl.union(jaw, pl.box_from((-ARM_T / 2, HUB_D / 2 - 6, JAW_Z0), (ARM_T / 2, ARM_LEN, JAW_Z1)))
# grip ribs on the inner face
for i in range(8):
    y = 25 + i * 12
    pl.union(jaw, pl.box_from((-ARM_T / 2 - 1.5, y, JAW_Z0 + 2), (-ARM_T / 2 + 0.5, y + 3, JAW_Z1 - 2)))
# pom notch near the tip (matches the fixed jaw)
NOTCH_DEPTH = 4.0   # into the arm from its inner (-X) face
pl.difference(jaw, pl.cyl(POM_D * 0.9, 80, (-ARM_T / 2 - POM_D * 0.45 + NOTCH_DEPTH, ARM_LEN - 22, 15)))

pl.finish(jaw, "claw_jaw", out, print_class="mid",
          notes="print on its side (inner face up); fix to the horn with 4 small self-tapping screws")

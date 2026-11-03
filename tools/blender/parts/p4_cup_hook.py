"""PRINT 4/4 - Robot B lipped cup hook (replaces the bent 1x10 strap).

Bolts to the stock round horn of the right-side hook servo. A long arm runs
forward along the robot's right side, drops down at the tip and ends in an
inward lip that catches the cup's rim while the plow wing rolls the cup upright
(flip_cup_with_right_wing() in code/robot_b/main.c). Printed in one piece; a
flat arm is stiffer than a bent strap and the lip works at any approach angle.

Frame: hub at the origin (servo shaft axis = Y, across the robot), arm along +X,
Z = up. MEASURE: horn diameter / screw radius, and the rim height of an
upside-down cup, then set DROP so the lip sits just under the rim.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

HORN_D = 24.0
HORN_SCREW_R = 8.5
HUB_D = 34.0
HUB_T = 6.0
ARM_L = 140.0
ARM_H = 14.0
ARM_T = 6.0
DROP = 38.0               # tip drop below the arm (~1.5 in, as the strap design)
LIP = 7.0                 # inward lip length (toward the robot, -Y)

out = pl.out_dir_from_args()
pl.reset()

hook = pl.cyl(HUB_D, HUB_T, (0, 0, 0), axis="Y", name="p4_cup_hook")
# arm
pl.union(hook, pl.box_from((HUB_D / 2 - 6, -ARM_T / 2, -ARM_H / 2), (ARM_L, ARM_T / 2, ARM_H / 2)))
# drop leg + inward lip
pl.union(hook, pl.box_from((ARM_L - 10, -ARM_T / 2, -ARM_H / 2 - DROP), (ARM_L, ARM_T / 2, ARM_H / 2)))
pl.union(hook, pl.box_from((ARM_L - 10, -ARM_T / 2 - LIP, -ARM_H / 2 - DROP), (ARM_L, ARM_T / 2, -ARM_H / 2 - DROP + 5)))
# fillet block at the arm/leg corner
corner = pl.box(10, ARM_T, 10, center=(ARM_L - 12, 0, -ARM_H / 2 - 3))
pl.rotate(corner, 45, "Y", pivot=(ARM_L - 12, 0, -ARM_H / 2 - 3))
pl.union(hook, corner)
# horn seat + screw holes LAST, so the arm cannot refill the seat rim
pl.difference(hook, pl.cyl(HORN_D + 0.6, 2.6, (0, -HUB_T / 2 + 1.2, 0), axis="Y"))
pl.difference(hook, pl.cyl(6.5, 20, (0, 0, 0), axis="Y"))
for ang in range(45, 360, 90):
    r = math.radians(ang)
    pl.difference(hook, pl.cyl(1.8, 20, (HORN_SCREW_R * math.cos(r), 0, HORN_SCREW_R * math.sin(r)), axis="Y"))

pl.finish(hook, "p4_cup_hook", out, print_class="team",
          notes=f"print on its side (flat face down); lip {LIP} mm inward at {DROP} mm below the arm")

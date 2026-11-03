"""PRINT 4/4 - Robot B lipped cup hook (replaces the bent 1x10 strap).

Bolts to a kit "1 x 5 Servo Horn" on the right-side hook servo with 2 kit "Silver
Servo Horn Machine Screw (M3)" + "Silver Servo Horn Nut (M3)" (nut traps on the
outer face); the horn's centre screw goes through the 6.5 mm access hole. A long arm runs
forward along the robot's right side, drops down at the tip and ends in an
inward lip that catches the cup's rim while the plow wing rolls the cup upright
(flip_cup_with_right_wing() in code/robot_b/main.c). Printed in one piece; a
flat arm is stiffer than a bent strap and the lip works at any approach angle.

Frame: hub at the origin (servo shaft axis = Y, across the robot), arm along +X,
Z = up. Built for the RIGHT side of Robot B: the servo is inboard (+Y), so the horn
seat and the lip both face +Y (toward the robot). MEASURE: horn diameter / screw radius, and the rim height of an
upside-down cup, then set DROP so the lip sits just under the rim.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

HORN_W, HORN_L, HORN_T = 9.5, 66.0, 2.6   # kit 1 x 5 Servo Horn channel (MEASURE)
HORN_PITCH = 0.5 * 25.4                    # its holes are on a 0.5 in pitch
HUB_D = 34.0
HUB_T = 9.0               # 2.6 horn channel + 2.4 nut trap + 4 mm of plastic between
ARM_L = 140.0
ARM_H = 14.0
ARM_T = 6.0
DROP = 38.0               # tip drop below the arm (~1.5 in, as the strap design)
LIP = 7.0                 # inward lip length (toward the robot, +Y)

out = pl.out_dir_from_args()
pl.reset()

hook = pl.cyl(HUB_D, HUB_T, (0, 0, 0), axis="Y", name="p4_cup_hook")
# arm
pl.union(hook, pl.box_from((HUB_D / 2 - 6, -ARM_T / 2, -ARM_H / 2), (ARM_L, ARM_T / 2, ARM_H / 2)))
# drop leg + inward lip
pl.union(hook, pl.box_from((ARM_L - 10, -ARM_T / 2, -ARM_H / 2 - DROP), (ARM_L, ARM_T / 2, ARM_H / 2)))
pl.union(hook, pl.box_from((ARM_L - 10, -ARM_T / 2, -ARM_H / 2 - DROP), (ARM_L, ARM_T / 2 + LIP, -ARM_H / 2 - DROP + 5)))
# fillet block at the arm/leg corner
corner = pl.box(10, ARM_T, 10, center=(ARM_L - 12, 0, -ARM_H / 2 - 3))
pl.rotate(corner, 45, "Y", pivot=(ARM_L - 12, 0, -ARM_H / 2 - 3))
pl.union(hook, corner)
# 1x5 horn channel + screw holes LAST, so the arm cannot refill them. The channel runs
# along the arm on the +Y face (servo side); the horn's centre sits on the hub centre.
pl.difference(hook, pl.box(HORN_L + 1, 2 * HORN_T, HORN_W + 0.6, center=(0, HUB_T / 2, 0)))
pl.difference(hook, pl.cyl(6.5, 20, (0, 0, 0), axis="Y"))          # horn centre-screw access
for k in (-1, 1):
    hx = k * HORN_PITCH
    pl.difference(hook, pl.cyl(pl.M3_CLEAR, 20, (hx, 0, 0), axis="Y"))
    # nut trap on the -Y face: build the hex along Z, then turn it so Z -> -Y
    nut = pl.hex_prism(pl.M3_NUT_AF, HUB_T / 2 - 2.4, HUB_T / 2 + 1, center=(hx, 0))
    nut.data.transform(pl.Matrix.Rotation(math.radians(90), 4, "X"))
    pl.difference(hook, nut)

pl.finish(hook, "p4_cup_hook", out, print_class="team",
          notes=f"print on its side (flat face down); lip {LIP} mm inward at {DROP} mm below the arm")

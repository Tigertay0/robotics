"""PRINT 3/4 - Robot B one-piece pocket plow (replaces the two bent 4x12 plates).

A flat centre face (wide enough for one pom stack) with two wings angled forward,
so a pushed stack sits IN a pocket and stays one group (4 + 4 pts each, x5),
and the pickleball can't roll off sideways. Rounded wing tips (no sharp ends to
split a stack or snag a cup). A pocket at the centre holds the kit lever switch
so the code knows when the plow touches a wall, cup or stack. Two rear tabs bolt
to the chassis front flange (0.5 in hole pitch, slotted for adjustment).

Frame: +X = robot forward, Y = across (+Y = left), Z = up; the plow bottom rides
GROUND mm above the floor. MEASURE the pom stack (3 + 1 = ~2.7 in tall).

NOTE vs STRATEGY.md: the metal V-plow there has its point forward and uses the wings
to roll the cups. This pocket shape keeps stacks together better; check the cup
flips (B's first 16 s) still work with the wing tips before switching.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

IN = 25.4
H = 72.0                   # wall height (pom stack is ~69 mm)
T = 4.0
FACE_W = 70.0              # centre face, a stack is ~56 mm wide
WING_L = 95.0
WING_DEG = 50.0            # wings open forward, measured from the centre face line
TIP_R = 7.0
GROUND = 3.0               # set when mounting (rules nothing; just clear the FRP bumps)

out = pl.out_dir_from_args()
pl.reset()

plow = pl.box_from((0, -FACE_W / 2, 0), (T, FACE_W / 2, H), "p3_pocket_plow")
a = math.radians(WING_DEG)
for s in (-1, 1):
    # wing hinges at the face edge and runs forward-outward
    x0, y0 = 0.0, s * FACE_W / 2
    cx = x0 + (WING_L / 2) * math.sin(a)
    cy = y0 + s * (WING_L / 2) * math.cos(a)
    wing = pl.box(T, WING_L + T, H, center=(cx, cy, H / 2))
    pl.rotate(wing, -s * WING_DEG, "Z", pivot=(cx, cy, 0))       # long axis -> (sin a, s cos a)
    pl.union(plow, wing)
    tx = x0 + WING_L * math.sin(a)
    ty = y0 + s * WING_L * math.cos(a)
    pl.union(plow, pl.cyl(2 * TIP_R, H, (tx, ty, H / 2)))           # rounded tip
    # vertical rib behind the joint so the wing can't flex
    pl.union(plow, pl.box_from((-10, s * FACE_W / 2 - (6 if s > 0 else -6) - 3, 0),
                               (0.5, s * FACE_W / 2 - (6 if s > 0 else -6) + 3, H)))
# lever switch pocket in the centre face (lever pokes through to the front)
pl.difference(plow, pl.box(T + 2, 28, 12, center=(T / 2, 0, 24)))
for dy in (-11, 11):
    pl.difference(plow, pl.cyl(2.2, 30, (T / 2, dy, 36), axis="X"))
# rear mounting tabs with slots at 0.5 in pitch
for s in (-1, 1):
    tab = pl.box_from((-28, s * 18 - 10, 0), (0.5, s * 18 + 10, T + 2))
    pl.union(plow, tab)
    for k in range(2):
        x = -22 + k * 0.5 * IN
        slot = pl.box(4.4, 8, 20, center=(x, s * 18, 3))
        pl.difference(plow, slot)
        for dy in (-4, 4):
            pl.difference(plow, pl.cyl(4.4, 20, (x, s * 18 + dy, 3)))

pl.finish(plow, "p3_pocket_plow", out, print_class="team",
          notes=f"print standing (wall height {H:.0f} mm up), no supports; mount with the bottom {GROUND} mm above the FRP")

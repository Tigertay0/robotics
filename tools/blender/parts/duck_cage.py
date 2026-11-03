"""M1 - Robot A floorless 3-slot duck cage (mid print class).

Robot front = +Y. Ducks enter broadside through the funnel at +Y and slide back
toward the rear plate. Three gate axles (G2 rear, G1 middle, G0 throat) cross the
channel; each carries a LEGO-beam flap driven by a servo mounted on the top rails.
Floorless: captured ducks ride on the field, so releasing = open gate + back away.

MEASURE the real ducks first and update DUCK_* below.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

DUCK_LEN = 57.7      # beak to tail (2.27 in) - lies across the channel
DUCK_W = 37.0        # body width (1.46 in) - along the channel
DUCK_H = 37.0
CLEAR = 4.0          # side clearance per side in the channel
WALL = 3.0
RIDE = 2.0           # wall bottom height above the FRP (set by the chassis mount)
CH_W = DUCK_LEN + 2 * CLEAR          # channel internal width (X)
SLOT = DUCK_W + 9.0                  # slot depth along Y
GATE = 6.0                           # gap reserved for each flap
WALL_H = 54.0
AXLE_Z = 42.0                        # flap axle centre above the wall bottom
AXLE_CLEAR = 3.0                     # duck top to axle-bore bottom
FUNNEL_LEN = 35.0
FUNNEL_MOUTH = 120.0                 # internal width at the mouth
BACK_T = 4.0
RAIL_W = 10.0
RAIL_T = 4.0

out = pl.out_dir_from_args()
pl.reset()

half = CH_W / 2
assert AXLE_Z - pl.LEGO_HOLE_D / 2 >= DUCK_H - RIDE + AXLE_CLEAR, "ducks would hit the gate axles"
y_slot3 = BACK_T
y_g2 = y_slot3 + SLOT
y_slot2 = y_g2 + GATE
y_g1 = y_slot2 + SLOT
y_slot1 = y_g1 + GATE
y_g0 = y_slot1 + SLOT
y_throat = y_g0 + GATE
y_mouth = y_throat + FUNNEL_LEN

# rear plate (mounts to the chassis)
cage = pl.box_from((-half - WALL, 0, 0), (half + WALL, BACK_T, WALL_H), "duck_cage")
# side walls
for s in (-1, 1):
    x0 = half if s > 0 else -half - WALL
    pl.union(cage, pl.box_from((x0, 0, 0), (x0 + WALL, y_throat, WALL_H)))
    # top rail (outward flange) with LEGO-pitch holes for servo brackets
    rx0 = half + WALL - 0.5 if s > 0 else -half - WALL - RAIL_W + 0.5   # 0.5 mm overlap
    rail = pl.box_from((rx0, 0, WALL_H - RAIL_T), (rx0 + RAIL_W, y_throat, WALL_H))
    pl.union(cage, rail)
    n = int((y_throat - 8) // pl.LEGO_PITCH)
    pl.hole_row(cage, n, pl.LEGO_PITCH, pl.LEGO_HOLE_D,
                start=(rx0 + RAIL_W / 2, 8, WALL_H), direction=(0, 1, 0))

# funnel flares (lower than the walls to save plastic)
dx = FUNNEL_MOUTH / 2 - half
length = math.hypot(dx, FUNNEL_LEN)
ang = math.degrees(math.atan2(dx, FUNNEL_LEN))
for s in (-1, 1):
    cx = s * (half + WALL / 2 + dx / 2)
    cy = y_throat + FUNNEL_LEN / 2
    flare = pl.box(WALL, length + WALL, 32, center=(cx, cy, 16))
    pl.rotate(flare, -s * ang, "Z", pivot=(cx, cy, 0))
    pl.union(cage, flare)

# gate axle holes through both walls (LEGO cross axle spins in a round 4.9 mm hole)
for yg in (y_g2, y_g1, y_g0):
    pl.difference(cage, pl.cyl(pl.LEGO_HOLE_D, CH_W + 4 * WALL + 2 * RAIL_W,
                               (0, yg + GATE / 2, AXLE_Z), axis="X"))
# rear plate mounting grid
for zx in range(3):
    pl.hole_row(cage, 7, pl.LEGO_PITCH, pl.LEGO_HOLE_D,
                start=(-24, BACK_T / 2, 12 + zx * 12), axis="Y", direction=(1, 0, 0))

pl.finish(cage, "duck_cage", out, print_class="mid",
          notes=f"channel {CH_W:.1f} mm wide, 3 slots x {SLOT:.1f} mm, mouth {FUNNEL_MOUTH} mm; "
                f"flap axles at Y={y_g2 + GATE/2:.1f}/{y_g1 + GATE/2:.1f}/{y_g0 + GATE/2:.1f}, Z={AXLE_Z:.1f} above wall bottom; mount wall bottom {RIDE} mm above the FRP; print upside down (rails on the bed)")

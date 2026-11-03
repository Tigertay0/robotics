"""PRINT 2/4 - Robot B print-in-place geared claw (one print, moving = 1 part).

Two fingers printed already assembled with the base, meshed by gear sectors, so
ONE micro servo opens and closes both:
  * left finger: turns on a captive printed pin + cap (0.4 mm clearances);
  * right finger: sits over a small hole in the base. The micro servo bolts UNDER
    the base, its shaft comes up through that hole, and its horn sits in a pocket
    under the right finger's hub; screw the horn to the hub through the 4 pilot
    holes. The servo turns the right finger, the gears mirror it to the left one.
After printing, rock the fingers to break any whiskers before fitting the servo.
Pads are concave cups sized for a 1.6 in pom so it can't roll out.

Frame: +Y = forward (finger tips), X = across, Z = up from the base bottom.
The rear holes are LEGO pitch (8 mm) to bolt onto the paralleling arm.
MEASURE: pom diameter, micro servo tab pitch / shaft offset, horn diameter.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

CLR = 0.4                    # print-in-place clearance (radial and vertical)
MIN_GAP = 0.35               # fail the build below this at any checked finger pose
BASE_T = 4.0
HUB_T = 8.0                  # finger / gear thickness
PIN_D = 6.0
CAP_D, CAP_T = 10.5, 2.0
MODULE = 2.0
TEETH = 12                   # pitch radius 12 mm
PITCH_R = MODULE * TEETH / 2
CENTRE = 2 * PITCH_R + 1.2   # pivot spacing incl. backlash/print clearance
TOOTH_W = 2.6                # tooth width at the pitch circle (space 6.28 - 2.6); wider teeth fuse mid-swing
FINGER_L = 72.0
FINGER_W = 9.0
OPEN_DEG = 18.0              # printed (rest) angle of each finger, outward from straight
SWING_DEG = 25.0             # clearance is checked from -SWING to +SWING around the rest pose
POM_D = 1.6 * 25.4
SHAFT_HOLE_D = 8.0           # micro servo spline + clearance
HORN_D, HORN_T = 22.0, 3.5   # pocket under the right hub for the micro servo horn
HORN_SCREW_R = 8.0
SERVO_TAB_PITCH = 27.5
SERVO_SHAFT_OFFSET = 5.5     # shaft to body centre, along the body

out = pl.out_dir_from_args()
pl.reset()

z_hub0 = BASE_T + CLR
z_hub1 = z_hub0 + HUB_T
zc = (z_hub0 + z_hub1) / 2
xL, xR = -CENTRE / 2, CENTRE / 2
root_r = PITCH_R - 1.25 * MODULE

# ---- base plate, left pin + cap, servo holes (body 1)
base = pl.rounded_plate(74, 100, BASE_T, 6, center=(0, -24, BASE_T / 2), name="base")
pin_h = z_hub1 + CLR + CAP_T - BASE_T + 0.5
pl.union(base, pl.cyl(PIN_D, pin_h, (xL, 0, BASE_T - 0.5 + pin_h / 2)))
pl.union(base, pl.cyl(CAP_D, CAP_T, (xL, 0, z_hub1 + CLR + CAP_T / 2)))
pl.difference(base, pl.cyl(SHAFT_HOLE_D, 20, (xR, 0, BASE_T / 2)))
# servo body runs along +X (outward) under the plate; tabs at body centre +/- pitch/2
body_cx = xR + SERVO_SHAFT_OFFSET
for dx in (-SERVO_TAB_PITCH / 2, SERVO_TAB_PITCH / 2):
    pl.difference(base, pl.cyl(2.0, 20, (body_cx + dx, 0, BASE_T / 2)))
# LEGO-pitch mounting holes at the rear, centred
for y in (-58.0, -66.0):
    pl.hole_row(base, 5, pl.LEGO_PITCH, pl.LEGO_HOLE_D, start=(-16, y, BASE_T / 2),
                depth=BASE_T + 2, direction=(1, 0, 0))


def finger(x_pivot, side, name):
    """Hub + gear sector + arm + pom pad, built straight, then turned to the rest angle."""
    if side < 0:   # left: ring around the printed pin
        hub = pl.tube(2 * root_r, PIN_D + 2 * CLR, HUB_T, center=(x_pivot, 0, zc), name=name)
    else:          # right: solid hub the servo horn screws into
        hub = pl.cyl(2 * root_r, HUB_T, (x_pivot, 0, zc), name=name)
    face = 0.0 if side < 0 else 180.0          # teeth face the other finger
    pitch_deg = 360.0 / TEETH
    offset = 0.0 if side < 0 else pitch_deg / 2
    for k in range(-3, 4):
        t = pl.box(2 * MODULE + 1.0, TOOTH_W, HUB_T, center=(x_pivot + root_r + MODULE - 0.5, 0, zc))
        pl.rotate(t, face + offset + k * pitch_deg, "Z", pivot=(x_pivot, 0, 0))
        pl.union(hub, t)
    arm_x = x_pivot + side * (root_r - FINGER_W / 2 + 1)
    pl.union(hub, pl.box_from((arm_x - FINGER_W / 2, 0, z_hub0), (arm_x + FINGER_W / 2, FINGER_L, z_hub1)))
    pad_x = arm_x - side * (FINGER_W / 2 + 3)
    pl.union(hub, pl.box(12, 26, HUB_T + 6, center=(pad_x, FINGER_L - 13, zc + 3)))
    pl.difference(hub, pl.cyl(POM_D, 40, (pad_x - side * (POM_D / 2 - 3), FINGER_L - 13, zc + 3)))
    if side < 0:   # re-cut the pin clearance last (the arm box overlaps the hub centre)
        pl.difference(hub, pl.cyl(PIN_D + 2 * CLR, HUB_T + 4, (x_pivot, 0, zc), segments=96))
    else:          # horn pocket underneath + screw pilots + centre screw access
        pl.difference(hub, pl.cyl(HORN_D + 0.6, 2 * HORN_T, (x_pivot, 0, z_hub0)))
        pl.difference(hub, pl.cyl(6.5, HUB_T + 4, (x_pivot, 0, zc)))
        for ang in range(45, 360, 90):
            r = math.radians(ang)
            pl.difference(hub, pl.cyl(1.8, HUB_T + 4, (x_pivot + HORN_SCREW_R * math.cos(r),
                                                       HORN_SCREW_R * math.sin(r), zc)))
    pl.rotate(hub, -side * OPEN_DEG, "Z", pivot=(x_pivot, 0, 0))   # tips swing outward
    return hub


left = finger(xL, -1, "finger_L")
right = finger(xR, +1, "finger_R")


def gaps_at(delta):
    """Turn copies of both fingers by +/-delta (geared: mirror motion) and measure gaps."""
    cl, cr = left.copy(), right.copy()
    cl.data, cr.data = left.data.copy(), right.data.copy()
    for c, n in ((cl, "finger_L"), (cr, "finger_R")):
        pl.bpy.context.scene.collection.objects.link(c)
        c.name = n
    pl.rotate(cl, -delta, "Z", pivot=(xL, 0, 0))
    pl.rotate(cr, +delta, "Z", pivot=(xR, 0, 0))
    try:
        return pl.min_gaps([base, cl, cr])
    finally:
        for c in (cl, cr):
            m = c.data
            pl.bpy.data.objects.remove(c, do_unlink=True)
            pl.bpy.data.meshes.remove(m)


def clean(key):
    return "~".join(part.split(".")[0] for part in key.split("~"))


worst = {}
for delta in [SWING_DEG * f for f in (-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1)]:
    g = {clean(k): v for k, v in gaps_at(delta).items()}
    print(f"POSE {delta:+.1f} deg", g)
    for k, v in g.items():
        worst[k] = min(worst.get(k, 99.0), v)
print("GAPS_MM over the swing", worst)
bad = {k: v for k, v in worst.items() if v < MIN_GAP}
if bad:
    raise RuntimeError(f"print-in-place bodies closer than {MIN_GAP} mm somewhere in +/-{SWING_DEG} deg: {bad}")

claw = pl.join([base, left, right], "p2_geared_claw")
pl.finish(claw, "p2_geared_claw", out, print_class="team",
          extra={"min_gap_mm": min(worst.values()), "swing_checked_deg": SWING_DEG},
          notes=f"print-in-place, 3 bodies (base+pin, finger_L, finger_R); min gap {min(worst.values()):.2f} mm "
                f"over +/-{SWING_DEG:.0f} deg; servo under the base drives finger_R through its horn pocket")

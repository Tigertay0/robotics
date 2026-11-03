"""S1-S6 - small-class parts (each <= 3 x 3 x 1 in after whole-inch rounding).

Every part is sized to the literal small box (60 x 60 x 20 mm) so it passes
under any reading of the class rule.

  camera_mount   (S1, Robot B)  L-bracket holding the Logitech camera's own clip,
                                two rubber-band hooks, LEGO-pitch base holes.
  tophat_bracket (S2+S3, both)  two top-hat bores 30 mm apart: centred on the
                                47.6 mm tape both read black; drifting puts one on
                                white (line follow) - also used for tape-edge stops.
  light_shroud   (S4+S5, both)  hood so wait_for_light() sees only the lamp; print 2.
                                Sensor and hood must stay inside the Starting Box.
  ring_fork      (S6, stretch)  tines slide beside the post's tee socket, under the
                                ring stack; a vertical lift then raises it 7.5 in.

MEASURE: top-hat barrel, light-sensor head, tee socket OD, ring OD/ID.
Run:  blender -b --factory-startup --python small_parts.py -- --out parts/out [--only name]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import partlib as pl  # noqa: E402

TOPHAT_D = 16.5
TOPHAT_SPACING = 30.0
LIGHT_D = 10.0
SOCKET_D = 42.0
RING_OD = 54.0


def camera_mount():
    w, base_d, t, up_h = 58.0, 26.0, 4.0, 19.0
    part = pl.box_from((-w / 2, 0, 0), (w / 2, base_d, t), "camera_mount")
    pl.union(part, pl.box_from((-w / 2, base_d - t, 0), (w / 2, base_d, up_h)))
    pl.difference(part, pl.box_from((-8, base_d - t - 1, 8), (8, base_d + 1, up_h + 1)))  # clip slot
    for s in (-1, 1):
        x = s * (w / 2 - 4)
        pl.union(part, pl.box_from((x - 2, base_d - 0.5, up_h - 6), (x + 2, base_d + 5, up_h)))  # band hooks
    for y in (8, 16):
        pl.hole_row(part, 4, pl.LEGO_PITCH, pl.LEGO_HOLE_D, start=(-12, y, 0), direction=(1, 0, 0))
    return part


def tophat_bracket():
    length, width, t = 58.0, 24.0, 6.0
    part = pl.rounded_plate(length, width, t, 4, center=(0, 0, t / 2), name="tophat_bracket")
    for s in (-1, 1):
        pl.difference(part, pl.cyl(TOPHAT_D + 0.4, 20, (s * TOPHAT_SPACING / 2, 0, t / 2)))
    pl.hole_row(part, 2, pl.LEGO_PITCH * 1.5, pl.LEGO_HOLE_D, start=(0, -6, t / 2), direction=(0, 1, 0))
    return part


def light_shroud():
    wall, tube_l = 2.0, 21.0
    od = LIGHT_D + 2 * wall
    part = pl.box_from((-od / 2 - 12, -3, 0), (od / 2 + 12, 3, 18), "light_shroud")
    pl.union(part, pl.tube(od, LIGHT_D + 0.4, tube_l, center=(0, 2.5 + tube_l / 2, od / 2), axis="Y"))
    pl.difference(part, pl.cyl(LIGHT_D + 0.4, 10, (0, 0, od / 2), axis="Y", segments=96))
    for s in (-1, 1):
        pl.difference(part, pl.cyl(pl.LEGO_HOLE_D, 10, (s * (od / 2 + 6), 0, 11), axis="Y"))
    return part


def ring_fork():
    gap = SOCKET_D + 2.0
    tine_w = (RING_OD - gap) / 2 + 2.0
    tine_l, t = 40.0, 4.0
    part = pl.box_from((-gap / 2 - tine_w, -18, 0), (gap / 2 + tine_w, 0, t), "ring_fork")
    for s in (-1, 1):
        x0 = gap / 2 if s > 0 else -gap / 2 - tine_w
        pl.union(part, pl.box_from((x0, -0.5, 0), (x0 + tine_w, tine_l, t)))
        # chamfer the outer tip corner so the tine steers around the socket
        cut = pl.box(tine_w * 2, 12, t + 2, center=(x0 + tine_w / 2 + s * tine_w, tine_l, t / 2))
        pl.rotate(cut, s * 35, "Z", pivot=(x0 + tine_w / 2, tine_l, 0))
        pl.difference(part, cut)
    pl.hole_row(part, 5, pl.LEGO_PITCH, pl.LEGO_HOLE_D, start=(-16, -9, t / 2), direction=(1, 0, 0))
    return part


PARTS = {
    "camera_mount": camera_mount,
    "tophat_bracket": tophat_bracket,
    "light_shroud": light_shroud,
    "ring_fork": ring_fork,
}

if __name__ == "__main__":
    out = pl.out_dir_from_args()
    args = pl.script_args()
    only = args[args.index("--only") + 1] if "--only" in args else None
    for name, build in PARTS.items():
        if only and name != only:
            continue
        pl.reset()
        pl.finish(build(), name, out, print_class="small")

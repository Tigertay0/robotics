"""Blender script: extract mesh-level details of the 2026 Fall Game GLB.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python tools/extract_glb_profiles.py -- Fall_Game_Table.glb data/glb_profiles.json

For every round game piece (bottle, ring, cup, pickleball, pom, duck, pipe post) it writes a radial profile
(max / min XY distance from the piece's vertical axis per 0.1 in height slice), plus the raw vertex list of the
two corrugated-plastic meshes (platform top and skirt) so the 1.625 in notch can be confirmed.

All numbers are inches in the team convention:
  X = (1.2192 - y_blender) / 0.0254   (along the 96 in length, left -> right in the overhead image)
  Y = (x_blender + 1.2192) / 0.0254   (across the 48 in width, bottom -> top)
  Z = (z_blender - 0.0213) / 0.0254   (height above the FRP surface)
"""
import json
import sys

import bpy
import numpy as np

M_PER_IN = 0.0254
BOARD_HALF = 1.2192
FRP_TOP = 0.0213

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path, out_path = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)


def verts_inches(obj):
    me = obj.data
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    mw = np.array(obj.matrix_world)
    homo = np.hstack([co, np.ones((n, 1))])
    w = homo @ mw.T
    xb, yb, zb = w[:, 0], w[:, 1], w[:, 2]
    return np.column_stack([
        (BOARD_HALF - yb) / M_PER_IN,
        (xb + BOARD_HALF) / M_PER_IN,
        (zb - FRP_TOP) / M_PER_IN,
    ])


def radial_profile(v, step=0.1):
    cx = (v[:, 0].min() + v[:, 0].max()) / 2.0
    cy = (v[:, 1].min() + v[:, 1].max()) / 2.0
    r = np.hypot(v[:, 0] - cx, v[:, 1] - cy)
    z0, z1 = v[:, 2].min(), v[:, 2].max()
    rows = []
    z = z0
    while z < z1 - 1e-9:
        m = (v[:, 2] >= z) & (v[:, 2] < z + step)
        if m.any():
            rows.append([round(float(z), 3), round(float(r[m].min()), 3), round(float(r[m].max()), 3)])
        z += step
    return {
        "axis_xy": [round(float(cx), 3), round(float(cy), 3)],
        "z_range": [round(float(z0), 3), round(float(z1), 3)],
        "r_max_overall": round(float(r.max()), 3),
        "r_min_overall": round(float(r.min()), 3),
        "slices_z_rmin_rmax": rows,
    }


targets = {
    "Blue Bottle-1 - Part": "bottle",
    "Ring 1.75in-1 - Part": "ring",
    "Cup - Black-1 - Part": "cup",
    "Cup - Black-2 - Part": "cup2",
    "pickle ball 2-1 - Part": "pickleball",
    "pom-red-1 - Part": "pom_red",
    "pom-green-4 - Part": "pom_green",
    "Rubber Duck Red 2.25in-1 - Part": "small_duck_body",
    "8 inch pvc-19 - Part": "post_pipe",
    "2.5 inch pvc-9 - Part": "pipe_2_5",
    "17.625 inch pvc-1 - Part": "pipe_17_625",
}
out = {"profiles": {}, "raw_vertices": {}}
tight = []
for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    # Tight world AABB from the actual vertices. NOTE: Object.bound_box transformed by matrix_world (what
    # tools/dump_glb.py used for data/glb_objects_raw.json) is the AABB of the *rotated local box*, so it is
    # inflated for any mesh whose import rotation is not a multiple of 90 degrees (pickleballs, rings, cups, ...).
    tv = verts_inches(obj)
    mn, mx = tv.min(axis=0), tv.max(axis=0)
    tight.append({
        "name": obj.name,
        "parent": obj.parent.name if obj.parent else None,
        "min_in": [round(float(c), 3) for c in mn],
        "max_in": [round(float(c), 3) for c in mx],
        "centroid_in": [round(float(c), 3) for c in tv.mean(axis=0)],
        "verts": int(len(tv)),
    })
    if obj.name in targets:
        out["profiles"][targets[obj.name]] = {"mesh": obj.name, **radial_profile(verts_inches(obj))}
    if obj.name in ("5.5x24-1 - Part", "12.5x24 No Holes-3 - Part"):
        v = verts_inches(obj)
        uniq = np.unique(np.round(v, 3), axis=0)
        out["raw_vertices"][obj.name] = uniq.tolist()

with open(out_path, "w") as fh:
    json.dump(out, fh, indent=1)
tight_path = out_path.replace("glb_profiles", "glb_objects_tight")
with open(tight_path, "w") as fh:
    json.dump({"units": "inch", "convention": "X=(1.2192-y)/0.0254, Y=(x+1.2192)/0.0254, Z=(z-0.0213)/0.0254",
               "objects": tight}, fh, indent=1)
print("WROTE", tight_path, len(tight))
print("WROTE", out_path, list(out["profiles"].keys()))

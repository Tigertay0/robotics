"""Render clean views of the two robots from blender/out/fall_game_2026.blend.

    blender -b blender/out/fall_game_2026.blend --python tools/render_robots.py -- docs/robots

Writes <robot>_<view>.png for Robot A (Duck Runner) and Robot B (Point Scorer),
using the off-table SHOWCASE copies. Model units are inches; +x = robot forward.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "docs/robots")
os.makedirs(out, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
scene.render.film_transparent = False
scene.render.film_transparent = False
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "MATERIAL"
shading.show_cavity = True
shading.cavity_type = "BOTH"
shading.show_object_outline = True
shading.object_outline_color = (0.1, 0.1, 0.1)
scene.view_settings.view_transform = "Standard"
scene.world = scene.world or bpy.data.worlds.new("w")
scene.world.color = (0.93, 0.94, 0.96)

# hide everything except the chosen showcase robot
def descendants(o):
    return [o, *o.children_recursive]

keep_all = {}
for name in ("SHOWCASE_A", "SHOWCASE_B"):
    keep_all[name] = descendants(bpy.data.objects[name])
for o in bpy.data.objects:
    if o.type in {"CAMERA", "LIGHT"}:
        continue
    o.hide_render = True
    o.hide_viewport = True

sun = next((o for o in bpy.data.objects if o.type == "LIGHT"), None)
if sun:
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))

floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
mesh = floor.data
mesh.from_pydata([(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)], [], [(0, 1, 2, 3)])
scene.collection.objects.link(floor)

VIEWS = {  # name: (direction from centre, ortho?)
    "front_left": ((1.0, -1.1, 0.75), False),
    "rear_right": ((-1.0, 1.1, 0.8), False),
    "side": ((0.0, -1.0, 0.12), True),
    "top": ((0.0, -0.001, 1.0), True),
}
NAMES = {"SHOWCASE_A": "robot_A_duck_runner", "SHOWCASE_B": "robot_B_point_scorer"}

for name, objs in keep_all.items():
    for o in bpy.data.objects:
        if o.type not in {"CAMERA", "LIGHT"}:
            o.hide_render = o not in objs and o is not floor
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr, size = (lo + hi) / 2, (hi - lo)
    floor.location = (0, 0, lo.z - 0.01)
    radius = size.length / 2
    print(f"{name} size in inches: {size.x:.1f} x {size.y:.1f} x {size.z:.1f}")
    for view, (d, ortho) in VIEWS.items():
        cam_data = bpy.data.cameras.new("c")
        cam_data.type = "ORTHO" if ortho else "PERSP"
        cam_data.ortho_scale = max(size.x, size.y if view == "top" else size.z * 2.2) * 1.35
        cam_data.lens = 50
        cam_data.clip_end = 1000
        cam = bpy.data.objects.new("c", cam_data)
        scene.collection.objects.link(cam)
        dirv = Vector(d).normalized()
        cam.location = ctr + dirv * radius * (3.0 if not ortho else 6.0)
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        scene.render.filepath = os.path.join(out, f"{NAMES[name]}_{view}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
print("DONE")

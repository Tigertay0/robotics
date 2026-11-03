"""Blender (Workbench) renders of the official 2026 Fall Game table.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python tools/render_views.py -- Fall_Game_Table.glb docs/renders

Writes top_ortho.png, iso.png and platform_front.png.

top_ortho.png pixel mapping (used by tools/annotate_top.py): 25 px per inch, image 2500 x 1300 px, showing
X -2..98 in (left -> right) and Y -2..50 in (bottom -> top):  px = (X + 2) * 25,  py = 1300 - (Y + 2) * 25.
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
glb, outdir = argv[0], argv[1]
IN = 0.0254
BOARD_HALF = 1.2192


def to_blender(x_in, y_in, z_in):
    """team inches (X right, Y up, Z up from FRP) -> Blender metres (see tools/extract_glb_profiles.py)."""
    return Vector((y_in * IN - BOARD_HALF, BOARD_HALF - x_in * IN, z_in * IN + 0.0213))


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

# Workbench 'Material' colour uses the viewport colour, which the glTF importer leaves white: copy the base colour.
for mat in bpy.data.materials:
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                c = node.inputs["Base Color"].default_value
                mat.diffuse_color = (c[0], c[1], c[2], 1.0)
                break

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_object_outline = True
sh.object_outline_color = (0.15, 0.15, 0.15)
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_shadows = True
sh.shadow_intensity = 0.35
scene.display.render_aa = "8"
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("bg")
world.color = (0.30, 0.32, 0.36)
scene.world = world


def make_camera(name, loc, rot=None, look_at=None, ortho_scale=None, lens=35):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = loc
    if ortho_scale:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.lens = lens
    cam_data.clip_start = 0.01
    cam_data.clip_end = 50
    if rot is not None:
        cam.rotation_euler = rot
    if look_at is not None:
        direction = look_at - loc
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, w, h):
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


# 1. top orthographic: image-right = -Y_blender, image-up = +X_blender  ->  camera rotated -90 deg about Z.
centre = to_blender(48.0, 24.0, 0)
cam_top = make_camera("top", Vector((centre.x, centre.y, 5.0)), rot=(0, 0, math.radians(-90)), ortho_scale=100 * IN)
render(cam_top, f"{outdir}/top_ortho.png", 2500, 1300)

# 2. 3/4 view from the bottom-left looking up the table (platform opening and Botguy both visible)
cam_iso = make_camera("iso", to_blender(-30, -34, 40), look_at=to_blender(52, 22, 0), lens=32)
render(cam_iso, f"{outdir}/iso.png", 2200, 1250)

# 3. close-up of the raised platform opening as a robot leaving the small Starting Box would see it
cam_front = make_camera("front", to_blender(50, 6.25, 4.5), look_at=to_blender(80, 6.25, 3.5), lens=24)
render(cam_front, f"{outdir}/platform_front.png", 1800, 1000)

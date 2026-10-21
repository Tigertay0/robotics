"""3D-printed duck lane for Robot A, in two halves (front with funnel, rear with exit gate).

Run:  Blender -b --factory-startup --python prints/build_lane.py -- prints/out
Writes lane_front.stl, lane_rear.stl (millimetres), a render and dims.json.

Rule check (2026 Fall Game, 3D Print Rules): mid-size part limit 220 x 220 x 80 mm, two allowed.
Both halves stay under 80 mm tall: the servos hang on the outside of the walls, not on top.
"""
import bpy, bmesh, os, sys, json, math
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.unit_settings.system = 'METRIC'; S.unit_settings.length_unit = 'MILLIMETERS'; S.unit_settings.scale_length = 0.001

# ---------------------------------------------------------------- dimensions (mm)
IN = 25.4
LANE_W   = 1.8 * IN          # 45.7 inside width (duck is 30 wide)
T        = 3.0               # wall thickness
H        = 70.0              # wall height; chassis floor sits on top (2.9 in = 73.7 above the table, walls start 3.7 above it)
L        = 160.0             # each half
FLANGE   = 14.0              # top flange outward, carries the bolt slots to the chassis floor
FUNNEL_L, FUNNEL_A = 50.0, math.radians(35)
SERVO    = (41.0, 20.5, 38.0)     # standard servo body: length x width x height (without the tabs)
MICRO    = (23.5, 12.5, 24.0)
SLOT_W, SLOT_Z0, SLOT_Z1 = 16.0, 8.0, 62.0   # flap slot through the wall
HOLE     = 4.4               # 8-32 clearance
Y_L = LANE_W / 2 + T / 2     # wall centre lines
Y_R = -Y_L

# ---------------------------------------------------------------- helpers
def cube(name, center, size, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return o
def cyl(name, center, r, depth, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=depth, location=center, rotation=rot)
    o = bpy.context.object; o.name = name
    return o
def boolean(a, b, op):
    m = a.modifiers.new("b", 'BOOLEAN'); m.operation = op; m.object = b; m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(b)
    return a
def union(a, b): return boolean(a, b, 'UNION')
def cut(a, b): return boolean(a, b, 'DIFFERENCE')

def wall(name, x0, x1, y):
    return cube(name, ((x0 + x1) / 2, y, H / 2), (x1 - x0, T, H))
def flange(name, x0, x1, y, outward):
    return cube(name, ((x0 + x1) / 2, y + outward * (T / 2 + FLANGE / 2 - 0.5), H - 1.5), (x1 - x0, FLANGE + 0.5, 3.0))
def flange_slots(body, x0, x1, y, outward):
    x = x0 + 12
    while x + 12 <= x1:
        body = cut(body, cube("slot", (x + 6, y + outward * (T / 2 + FLANGE / 2), H - 1.5), (12.0, HOLE, 6.0)))
        x += 25.4
    return body
def flap_slot(body, x, y):
    return cut(body, cube("flapslot", (x, y, (SLOT_Z0 + SLOT_Z1) / 2), (SLOT_W, T + 2, SLOT_Z1 - SLOT_Z0)))
def servo_pocket(body, x, y, outward, micro=False):
    """servo on the outside of the wall with its shaft pointing through the wall into the lane,
    so the 1x5 horn hangs down inside the lane and swings up through the flap slot.
    body length along the wall (x), shaft axis along y at z = SHAFT_Z, 10 mm from the body end."""
    bl, bw, bh = MICRO if micro else SERVO          # bl along x, bh along y (outward), bw along z
    SHAFT_Z = SLOT_Z1 - 4
    xc = x - (bl / 2 - 10)                           # shaft sits over the flap slot
    yc = y + outward * (T / 2 + (bh + 3) / 2)
    boss = cube("boss", (xc, yc, SHAFT_Z), (bl + 12, bh + 3, bw + 6))
    body = union(body, boss)
    body = cut(body, cube("pocket", (xc, yc + outward * 3, SHAFT_Z), (bl + 0.6, bh + 6, bw + 0.6)))   # open outward
    body = cut(body, cyl("shaft", (xc + (bl / 2 - 10) * 0 + (x - xc), y, SHAFT_Z), 6.0, T + 2, rot=(math.pi / 2, 0, 0)))
    for dx in (-(bl / 2 + 3.5), bl / 2 + 3.5):      # tab screws, along y into the boss ends
        body = cut(body, cyl("tabhole", (xc + dx, yc, SHAFT_Z), 1.2 if micro else 1.6, bh + 8, rot=(math.pi / 2, 0, 0)))
    return body
def joint_holes(body, x, y_sign):
    for z in (20, 50):
        body = cut(body, cyl("jh", (x, y_sign * Y_L, z), HOLE / 2, T + 2, rot=(math.pi / 2, 0, 0)))
    return body

# ---------------------------------------------------------------- front half (x = 0 rear joint .. L front, funnel beyond)
F = wall("lane_front", 0, L, Y_L)
F = union(F, wall("wR", 0, L, Y_R))
F = union(F, flange("fl", 0, L, Y_L, +1)); F = union(F, flange("fr", 0, L, Y_R, -1))
for s in (+1, -1):
    y = s * Y_L
    fun = cube("funnel", (L + FUNNEL_L / 2 * math.cos(FUNNEL_A), y + s * FUNNEL_L / 2 * math.sin(FUNNEL_A), H / 2),
               (FUNNEL_L, T, H), rot=(0, 0, s * FUNNEL_A))
    F = union(F, fun)
    F = union(F, cube("funroot", (L, y + s * 2.0, H / 2), (T * 1.5, T * 2.2, H)))   # fillet the root
F = flange_slots(F, 0, L, Y_L, +1); F = flange_slots(F, 0, L, Y_R, -1)
# intake gate C: left wall, 12 mm behind the funnel root
GATE_C_X = L - 18
F = flap_slot(F, GATE_C_X, Y_L)
F = servo_pocket(F, GATE_C_X, Y_L, +1)
F = joint_holes(F, 10, +1); F = joint_holes(F, 10, -1)

# ---------------------------------------------------------------- rear half (x = -L .. 0, joint tabs at 0 .. 20)
R = wall("lane_rear", -L, 0, Y_L)
R = union(R, wall("wR2", -L, 0, Y_R))
R = union(R, flange("fl2", -L, 0, Y_L, +1)); R = union(R, flange("fr2", -L, 0, Y_R, -1))
for s in (+1, -1):                                  # joint tabs overlapping the front half's walls on the outside
    R = union(R, cube("tab", (10, s * (Y_L + T), 35), (20, T, 50)))
R = flange_slots(R, -L, 0, Y_L, +1); R = flange_slots(R, -L, 0, Y_R, -1)
GATE_A_X, GATE_B_X = -L + 40, -66.0                 # exit gate at the rear end (left wall), pin gate (right wall, micro servo)
R = flap_slot(R, GATE_A_X, Y_L); R = servo_pocket(R, GATE_A_X, Y_L, +1)
R = flap_slot(R, GATE_B_X, Y_R); R = servo_pocket(R, GATE_B_X, Y_R, -1, micro=True)
R = cut(R, cube("touchwin", (-L + 30, Y_R, 20), (10, T + 2, 12)))     # window for the lane-full touch switch
R = joint_holes(R, 10, +1); R = joint_holes(R, 10, -1)
# the holes in the tabs must go through the tab, not the (absent) wall: re-cut at the tab y
for s in (+1, -1):
    for z in (20, 50):
        R = cut(R, cyl("tabh", (10, s * (Y_L + T), z), HOLE / 2, T * 3, rot=(math.pi / 2, 0, 0)))

# ---------------------------------------------------------------- checks, export, render
def dims(o):
    xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]; zs = [v.co.z for v in o.data.vertices]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
def volume_cm3(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = bm.calc_volume(); bm.free(); return v / 1000.0
report = {}
for o in (F, R):
    d = dims(o)
    inch = [math.ceil(v / IN) for v in d]
    report[o.name] = {"mm": [round(v, 1) for v in d], "whole_in": inch, "volume_cm3": round(volume_cm3(o), 1),
                      "fits_mid_size_220x220x80": bool(d[0] <= 220 and d[1] <= 220 and d[2] <= 80)}
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, f"{o.name}.stl"), export_selected_objects=True, ascii_format=False)
json.dump(report, open(os.path.join(OUT, "dims.json"), "w"), indent=1)
for k, v in report.items(): print("PART", k, v)

# duck for scale (2.4 x 1.2 x 1.6 in) and a render
duck = cube("duck_for_scale", (-60, 0, 20.5), (61, 30, 41))
m = bpy.data.materials.new("duck"); m.diffuse_color = (0.95, 0.8, 0.1, 1); duck.data.materials.append(m)
mp = bpy.data.materials.new("pla"); mp.diffuse_color = (0.55, 0.57, 0.6, 1)
for o in (F, R): o.data.materials.append(mp)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); S.collection.objects.link(cam)
cam.location = (260, -330, 230); cam.rotation_euler = (Vector((0, 0, 35)) - Vector(cam.location)).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 40; cam.data.clip_end = 5000; S.camera = cam
S.render.engine = 'BLENDER_WORKBENCH'; S.display.shading.light = 'STUDIO'; S.display.shading.color_type = 'MATERIAL'
S.display.shading.show_shadows = True; S.display.shading.show_cavity = True
S.render.resolution_x, S.render.resolution_y = 1600, 1000
S.render.filepath = os.path.join(OUT, "lane_render.png"); bpy.ops.render.render(write_still=True)
cam.location = (-90, 120, 420); cam.rotation_euler = (Vector((0, 0, 0)) - Vector(cam.location)).to_track_quat('-Z', 'Y').to_euler()
S.render.filepath = os.path.join(OUT, "lane_top.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lane.blend"))
print("DONE")

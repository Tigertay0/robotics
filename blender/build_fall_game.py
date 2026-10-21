"""Build the 2026 Botball Fall Game table (official GLB) plus the two proposed robots.

Run:  Blender -b --factory-startup --python build_fall_game.py -- <out_dir>
Needs next to this file's parent folder: Fall_Game_Table.glb and the extracted
"STL Parts" folder (Metal + Lego STLs), both from the Botball Team Home Base.

Units: 1 Blender unit = 1 inch. Origin = inside corner of the bottom-left PVC,
+X along the long side (toward the platform), +Y toward Botguy, Z up.

Every robot part carries custom properties:
  source   "kit-stl"  geometry is the official KIPR/LEGO STL
           "estimate" kit part without an STL (motor, servo, Wombat, wheels...), size measured from photos
           "design"   layout decision (positions, angles): adjust to what you build
  kit      the line of the 2026 kit list the part comes from
Parts NOT on the 2026 kit lists are bright red and named NOT_IN_KIT_*.
"""
import bpy, math, os, sys, json, glob
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index("--") + 1]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(HERE)                     # ~/BOTBALL
GLB = os.path.join(ROOT_DIR, "Fall_Game_Table.glb")
STL_DIRS = [os.path.join(ROOT_DIR, "STL Parts"), os.path.join(ROOT_DIR, "cad", "stl", "STL Parts")]
MM = 1 / 25.4

# ---------------------------------------------------------------- field frame (from the drawings)
IN_W, IN_H = 93.08, 40.20          # inside of the PVC (sheet 8)
CENTER_X = IN_W / 2                # centre tape, centred on the PVC T (sheet 7)
TOP_BOARD_Y = IN_H + 1.315 + 5.2   # board edge behind the top wall (GLB x=0 maps here)

# ---------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = 'IMPERIAL'
    s.unit_settings.length_unit = 'INCHES'
    s.unit_settings.scale_length = 0.0254

_mats = {}
def mat(name, rgba, rough=0.6, metal=0.0):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = rgba
    _mats[name] = m
    return m

_cols = {}
def coll(name, parent=None):
    if name in _cols:
        return _cols[name]
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    _cols[name] = c
    return c

def relink(obj, collection):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)

def tag(obj, name, material, collection, source, **props):
    obj.name = name
    if material is not None and obj.type == 'MESH':
        obj.data.materials.clear()
        obj.data.materials.append(material)
    relink(obj, collection)
    obj["source"] = source
    for k, v in props.items():
        obj[k] = v
    return obj

def box(name, center, size, material, collection, source, rot=(0, 0, 0), **props):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return tag(o, name, material, collection, source, **props)

def cyl(name, center, r, depth, material, collection, source, rot=(0, 0, 0), verts=32, **props):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=center, rotation=rot)
    return tag(bpy.context.object, name, material, collection, source, **props)

def sphere(name, center, r, material, collection, source, **props):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=center, segments=24, ring_count=12)
    return tag(bpy.context.object, name, material, collection, source, **props)

def world_bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))

def find_stl(basename):
    for d in STL_DIRS:
        hits = glob.glob(os.path.join(d, "**", basename), recursive=True)
        if hits:
            return hits[0]
    raise FileNotFoundError(basename)

_stl_cache = {}
def stl_part(name, basename, loc, material, collection, rot=(0, 0, 0), origin="bottom", kit=None, **props):
    """Import a KIPR/LEGO STL (mm, Y-up), convert to inches Z-up, put its origin at the bbox
    bottom-centre ("bottom") or centre ("center"), then place it. Mesh data is shared per STL."""
    if basename not in _stl_cache:
        bpy.ops.wm.stl_import(filepath=find_stl(basename))
        o = bpy.context.selected_objects[0]
        o.scale = (MM, MM, MM)
        o.rotation_euler = (math.pi / 2, 0, 0)          # Y-up -> Z-up
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        mn, mx = world_bbox(o)
        c = (mn + mx) / 2
        shift = Vector((c.x, c.y, mn.z)) if origin == "bottom" else c
        for v in o.data.vertices:
            v.co -= shift
        _stl_cache[basename] = o.data
        bpy.data.objects.remove(o)
    o = bpy.data.objects.new(name, _stl_cache[basename])
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o = tag(o, name, material, collection, "kit-stl", **props)
    if kit:
        o["kit"] = kit
    return o

# ---------------------------------------------------------------- build
reset()
M = {
    "metal": mat("KIPR metal", (0.66, 0.68, 0.71, 1), 0.35, 0.8),
    "lego": mat("LEGO grey", (0.55, 0.57, 0.6, 1), 0.4),
    "lego_dark": mat("LEGO dark", (0.25, 0.26, 0.28, 1), 0.4),
    "wombat": mat("Wombat case", (0.1, 0.1, 0.12, 1), 0.3),
    "screen": mat("Wombat screen", (0.12, 0.32, 0.55, 1), 0.1),
    "battery": mat("Battery", (0.15, 0.15, 0.6, 1), 0.4),
    "motor": mat("Gear motor", (0.06, 0.06, 0.06, 1), 0.4),
    "servo": mat("Servo", (0.08, 0.08, 0.08, 1), 0.4),
    "servo9g": mat("Micro servo", (0.15, 0.35, 0.8, 1), 0.4),
    "rubber": mat("Tyre", (0.03, 0.03, 0.03, 1), 0.9),
    "hub": mat("Wheel hub", (0.8, 0.8, 0.82, 1), 0.4, 0.6),
    "sensor": mat("Sensor PCB", (0.05, 0.35, 0.15, 1), 0.5),
    "camera": mat("Camera", (0.05, 0.05, 0.05, 1), 0.3),
    "tape": mat("Black", (0.02, 0.02, 0.02, 1), 0.5),
    "missing": mat("NOT IN KIT", (1.0, 0.0, 0.0, 1), 0.4),
}

# ---- official table -------------------------------------------------------
FIELD = coll("Field (official Fall_Game_Table.glb)")
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
imported = [o for o in bpy.data.objects if o not in before]
glb_root = next(o for o in imported if o.parent is None and o.name == "Root")
for o in imported:
    relink(o, FIELD)
for o in [o for o in imported if o.type in ('CAMERA', 'LIGHT')]:
    bpy.data.objects.remove(o)
imported = [o for o in imported if o.name in bpy.data.objects and bpy.data.objects[o.name] is o] if False else [o for o in bpy.data.objects if o.users_collection and o.users_collection[0] is FIELD]
# metres, Y-up (already converted by the importer) -> inches in the field frame:
# field x = CENTER_X - y_glb ; field y = TOP_BOARD_Y + x_glb ; z = z_glb - FRP top
# the importer already converts metres to the scene unit (inches)
glb_root.rotation_mode = 'XYZ'
glb_root.rotation_euler = (0, 0, math.pi / 2)
glb_root.location = (CENTER_X, TOP_BOARD_Y, 0)
bpy.context.view_layer.update()
frp = bpy.data.objects["FRP - 4x8-1 - Part"]
z_top = world_bbox(frp)[1].z
glb_root.location.z = -z_top
bpy.context.view_layer.update()

def piece_center(name):
    """world bbox centre of an imported assembly (empty + all mesh descendants)"""
    o = bpy.data.objects[name]
    meshes = [c for c in o.children_recursive if c.type == 'MESH'] or [o]
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for m in meshes:
        a, b = world_bbox(m)
        mn = Vector(map(min, mn, a)); mx = Vector(map(max, mx, b))
    return (mn + mx) / 2, mn, mx

PIECES = {}
for n in [o.name for o in imported if o.type == 'EMPTY']:
    if n.startswith(("Rubber Duck", "Pom Stack", "pom-red-1 2", "Cup - Black", "pickle ball", "Ring 1.75in", "Blue Bottle", "botguy-1")):
        c, mn, mx = piece_center(n)
        PIECES[n] = {"center": [round(v, 3) for v in c], "min": [round(v, 3) for v in mn], "max": [round(v, 3) for v in mx]}
# the big duck is two mirrored halves without a parent empty
bd = [o for o in imported if o.type == 'EMPTY' and o.name in ("Mirror3", "Split Line2")]
if bd:
    cs = [piece_center(o.name) for o in bd]
    mn = Vector(map(min, cs[0][1], cs[1][1])); mx = Vector(map(max, cs[0][2], cs[1][2]))
    PIECES["Big duck"] = {"center": [round(v, 3) for v in ((mn + mx) / 2)], "min": [round(v, 3) for v in mn], "max": [round(v, 3) for v in mx], "empties": [o.name for o in bd]}
plat = bpy.data.objects["12.5x24 No Holes-3 - Part"]
pmn, pmx = world_bbox(plat)
PIECES["Platform top"] = {"min": [round(v, 3) for v in pmn], "max": [round(v, 3) for v in pmx]}
with open(os.path.join(OUT, "pieces.json"), "w") as f:
    json.dump(PIECES, f, indent=1)
for k, v in PIECES.items():
    print("PIECE", k, v.get("center"), "z-top", v["max"][2])

# zone labels
LBL = coll("Zone labels")
def label(text, x, y, size=2.2):
    bpy.ops.object.text_add(location=(x, y, 0.02))
    o = bpy.context.object
    o.data.body = text; o.data.size = size; o.data.align_x = 'CENTER'; o.data.align_y = 'CENTER'
    tag(o, f"Label {text}", M["tape"], LBL, "design")
for t, x, y in [("Zone 1 (TL)", 22, 36), ("Zone 2 (TR)", 70, 36), ("Zone 3 (ML)", 22, 15.5), ("Zone 4 (MR)", 70, 15.5),
                ("Zone 5 (BL) = big start box", 22, 3), ("small start box", 58, 3)]:
    label(t, x, y, 1.8)

# ---- kit lines --------------------------------------------------------------
KIT = {
    "chassis": "Metal: Chassis (2)", "bracket": "Metal: Servo Bracket (8)", "plate": "Metal: Plate 4 x 12 (4, bendable)",
    "strap19": "Metal: Strap 1 x 19 (4, bendable)", "strap10": "Metal: Strap 1 x 10 (6, bendable)",
    "ch8": "Metal: Channel 3 x 8 (3)", "ch12": "Metal: Channel 3 x 12 (2)", "horn": "Metal: 1 x 5 Servo Horn (4)",
    "rhorn": "Metal: Round Servo Horn (2)", "micromount": "Metal: Micro Servo Mount (2)", "angle": "Metal: Angle Bracket (2)",
    "standoff1": "Metal: Standoff 8-32 x 1\" (7)", "standoff2": "Metal: Standoff 8-32 x 2\" (2)", "caster": "Metal: Caster (2)",
    "motor": "Electronics: Black Gear Motor (8)", "servo": "Electronics: Servo (5)", "micro": "Electronics: Micro Servo (2)",
    "wombat": "Electronics: Wombat (2)", "battery": "Electronics: Wombat Battery (2)", "mecanum": "Electronics: Mecanum Wheel (4)",
    "solar": "Electronics: Solarbotics Wheel (4)", "camera": "Electronics: Black Camera (1)", "et": "Electronics: ET rangefinder (2)",
    "tophat": "Electronics: Tophat (4)", "light": "Electronics: Light (3)", "lever": "Electronics: Lever (2)", "touch": "Electronics: Small Touch (4)",
    "liftarm": "Lego: liftarms", "pins": "Lego: pins",
}
def est(kind, name, *args, kit, collection, **kw):
    fn = {"box": box, "cyl": cyl, "sphere": sphere}[kind]
    o = fn(name, *args, collection, "estimate", **kw)
    o["kit"] = KIT[kit]
    return o

# shared estimated sizes (inches) of kit parts without STLs
MOTOR = (1.6, 0.8, 1.5)        # KIPR black gear motor, servo-style case
SERVO = (1.6, 0.8, 1.42)
MICRO = (0.9, 0.47, 1.1)
WOMBAT = (5.5, 4.0, 1.3)
BATT = (3.2, 1.4, 1.0)
MEC_D, MEC_W = 2.36, 1.1       # 60 mm mecanum
SOL_D, SOL_W = 2.75, 0.5       # Solarbotics wheel

def wombat(C, x, y, z, yaw=0):
    a = est("box", "Wombat controller", (x, y, z + WOMBAT[2] / 2), WOMBAT, M["wombat"], kit="wombat", collection=C, rot=(0, 0, yaw))
    b = est("box", "Wombat screen", (x + 0.3, y, z + WOMBAT[2] + 0.005), (3.6, 2.6, 0.01), M["screen"], kit="wombat", collection=C, rot=(0, 0, yaw))
    return [a, b]

def servo_box(C, name, loc, micro=False, rot=(0, 0, 0)):
    s = MICRO if micro else SERVO
    o = est("box", name, loc, s, M["servo9g" if micro else "servo"], kit="micro" if micro else "servo", collection=C, rot=rot)
    return o

def mecanum(C, name, loc, rot):
    objs = [est("cyl", name, loc, MEC_D / 2 - 0.25, MEC_W * 0.6, M["hub"], kit="mecanum", collection=C, rot=rot, verts=24)]
    for k in range(9):          # rollers at 45 deg, for looks
        a = 2 * math.pi * k / 9
        r = MEC_D / 2 - 0.22
        c = Vector(loc) + Vector((r * math.cos(a), 0, r * math.sin(a)))
        ro = est("cyl", f"{name} roller", c, 0.2, 0.9, M["rubber"], kit="mecanum", collection=C, rot=(0, 0, 0), verts=10)
        ro.rotation_euler = (math.radians(45), 0, 0)
        ro.rotation_euler.rotate(Matrix.Rotation(a, 3, 'Y'))
        objs.append(ro)
    return objs

# ---- Robot A: Duck Runner ---------------------------------------------------
RA = coll("Robot A - Duck Runner")
A = []
FLOOR_A = 2.9                      # chassis floor height: ducks (1.6" tall) pass underneath
LANE_W, LANE_L = 1.8, 12.5
CH_L, CH_W = 9.23, 5.0
A.append(stl_part("Chassis", "Chassis.STL", (0, 0, FLOOR_A - 0.08), M["metal"], RA, kit=KIT["chassis"], note="raised on standoffs"))
for sx in (-1, 1):
    for sy in (-1, 1):
        y_br = sy * (CH_W / 2 + 0.45)
        A.append(stl_part(f"Servo bracket motor {sx}{sy}", "Servo Bracket.STL", (sx * 3.0, y_br, 0.55), M["metal"], RA,
                          rot=(0, 0, math.pi / 2), origin="bottom", kit=KIT["bracket"]))
        A.append(est("box", f"Gear motor {sx}{sy}", (sx * 3.0, y_br, 1.3), (MOTOR[2], MOTOR[1], MOTOR[0]), M["motor"], kit="motor", collection=RA))
        A.append(est("cyl", f"Standoff 1in {sx}{sy}", (sx * 3.0 + 0.6, sy * (CH_W / 2 + 0.1), FLOOR_A - 0.5), 0.12, 1.0, M["hub"], kit="standoff1", collection=RA))
        A += mecanum(RA, f"Mecanum {'F' if sx > 0 else 'R'}{'L' if sy > 0 else 'R'}", (sx * 3.0, sy * (CH_W / 2 + 0.9 + MEC_W / 2), MEC_D / 2), (math.pi / 2, 0, 0))
# lane walls: two 4x12 plates per side, on edge, 2.5" tall, from the ground up to the floor
for sy in (-1, 1):
    for i, x in enumerate((-2.75, 2.75)):
        A.append(stl_part(f"Lane wall plate {'L' if sy > 0 else 'R'}{i+1}", "Plate 4x12.STL", (x, sy * (LANE_W / 2 + 0.04), 0.15), M["metal"], RA,
                          rot=(math.pi / 2, 0, 0), origin="center", kit=KIT["plate"], note="on edge; overlap 2.5in, bolted together"))
    A.append(stl_part(f"Strap 1x10 splice {'L' if sy > 0 else 'R'}", "Strap 1x10.STL", (0, sy * (LANE_W / 2 + 0.16), 1.4), M["metal"], RA,
                      rot=(math.pi / 2, 0, 0), origin="center", kit=KIT["strap10"]))
A.append(stl_part("Angle bracket lane L", "Angle Bracket.STL", (0, LANE_W / 2 + 0.6, FLOOR_A - 0.9), M["metal"], RA, kit=KIT["angle"]))
A.append(stl_part("Angle bracket lane R", "Angle Bracket.STL", (0, -LANE_W / 2 - 0.6, FLOOR_A - 0.9), M["metal"], RA, rot=(0, 0, math.pi), kit=KIT["angle"]))
# intake funnel: two bent 1x19 straps
FUN = math.radians(35)
for sy in (-1, 1):
    f = stl_part(f"Funnel strap 1x10 {'L' if sy > 0 else 'R'}", "Strap 1x10.STL",
                 (LANE_L / 2 + 3.15 * math.cos(FUN), sy * (LANE_W / 2 + 0.04 + 3.15 * math.sin(FUN)), 0.9), M["metal"], RA,
                 rot=(math.pi / 2, 0, sy * FUN), origin="center", kit=KIT["strap10"], note="bolted to the wall end, flared 35deg")
    A.append(f)
# three flap gates: servo on top of the wall, 1x5 horn hanging down across the lane
for name, x, micro, sy in (("intake C", LANE_L / 2 - 0.4, False, 1), ("pin B", -LANE_L / 2 + 2.6, True, -1), ("exit A", -LANE_L / 2 + 0.4, False, 1)):
    sv = servo_box(RA, f"Servo gate {name}", (x, sy * (LANE_W / 2 + 0.55), 2.65 + 0.4), micro=micro, rot=(0, 0, math.pi / 2))
    A.append(sv)
    if micro:
        A.append(stl_part(f"Micro servo mount {name}", "Micro Servo Mount.STL", (x, sy * (LANE_W / 2 + 0.55), 2.65 + 0.05), M["metal"], RA, kit=KIT["micromount"]))
    A.append(stl_part(f"Flap horn {name}", "1 x 5 Servo Horn.STL", (x, sy * (LANE_W / 2 - 0.1), 1.3), M["metal"], RA,
                      rot=(0, math.pi / 2, math.pi / 2), origin="center", kit=KIT["horn"], note="flap: horn rotates 90deg to open"))
A += wombat(RA, -0.4, 0, FLOOR_A + 1.2, yaw=0)
A.append(est("box", "Battery", (-3.6, 0, FLOOR_A + 1.2 + 0.5), (BATT[1], BATT[0], BATT[2]), M["battery"], kit="battery", collection=RA))
A.append(est("box", "Tophat (tape edge)", (LANE_L / 2 + 0.3, -(LANE_W / 2 + 0.6), 0.45), (0.6, 0.45, 0.5), M["sensor"], kit="tophat", collection=RA))
A.append(est("box", "Tophat (tape edge) 2", (LANE_L / 2 + 0.3, LANE_W / 2 + 0.6, 0.45), (0.6, 0.45, 0.5), M["sensor"], kit="tophat", collection=RA))
A.append(est("box", "Light sensor (start)", (2.6, -2.0, FLOOR_A + 1.2 + 0.2), (0.5, 0.5, 0.4), M["sensor"], kit="light", collection=RA))
A.append(est("box", "ET rangefinder (wall)", (CH_L / 2 + 0.2, 1.8, FLOOR_A + 0.6), (0.3, 1.1, 0.6), M["sensor"], kit="et", collection=RA))
A.append(est("box", "Touch (lane full)", (-LANE_L / 2 + 1.3, -(LANE_W / 2 - 0.15), 0.9), (0.45, 0.2, 0.4), M["sensor"], kit="touch", collection=RA))
rootA = bpy.data.objects.new("ROBOT_A_root", None)
RA.objects.link(rootA)
for o in A:
    o.parent = rootA
rootA.location = (54.3, 5.6, 0)      # small start box, facing east

# ---- Robot B: Point Scorer --------------------------------------------------
RB = coll("Robot B - Point Scorer")
Bp = []
FLOOR_B = 1.0
Bp.append(stl_part("Chassis", "Chassis.STL", (0, 0, FLOOR_B - 0.08), M["metal"], RB, kit=KIT["chassis"]))
for sy in (-1, 1):
    Bp.append(est("box", f"Gear motor {'L' if sy > 0 else 'R'}", (-2.0, sy * (CH_W / 2 - 0.55), FLOOR_B + 0.75), (MOTOR[0], MOTOR[1], MOTOR[2]), M["motor"], kit="motor", collection=RB))
    Bp.append(est("cyl", f"Solarbotics wheel {'L' if sy > 0 else 'R'}", (-2.0, sy * (CH_W / 2 + 0.35), SOL_D / 2), SOL_D / 2, SOL_W, M["rubber"], kit="solar", collection=RB, rot=(math.pi / 2, 0, 0)))
    Bp.append(est("cyl", f"Wheel hub {'L' if sy > 0 else 'R'}", (-2.0, sy * (CH_W / 2 + 0.35), SOL_D / 2), SOL_D / 2 - 0.3, SOL_W + 0.02, M["hub"], kit="solar", collection=RB, rot=(math.pi / 2, 0, 0)))
Bp.append(est("sphere", "Caster ball", (3.6, 0, 0.5), 0.5, M["hub"], kit="caster", collection=RB))
Bp.append(est("box", "Caster housing", (3.6, 0, FLOOR_B - 0.1), (1.1, 1.1, 0.35), M["metal"], kit="caster", collection=RB))
Bp += wombat(RB, -1.2, 0, FLOOR_B + 1.25)
Bp.append(est("box", "Battery", (-3.4, 0, FLOOR_B + 1.25 + WOMBAT[2] + 0.5), (BATT[1], BATT[0], BATT[2]), M["battery"], kit="battery", collection=RB))
# arm: servo demobot shoulder + paralleling arm + claw (build guides)
Bp.append(stl_part("Servo bracket shoulder", "Servo Bracket.STL", (3.2, 1.6, FLOOR_B + 1.2), M["metal"], RB, kit=KIT["bracket"]))
Bp.append(servo_box(RB, "Servo shoulder", (3.2, 1.6, FLOOR_B + 1.2 + 0.71)))
ARM_ANG = math.radians(25)
for k, dy in enumerate((0.95, 2.25)):
    Bp.append(stl_part(f"Paralleling arm liftarm 1x11 {k+1}", "1 x 11 Liftarm.STL", (3.2 + 2.1 * math.cos(ARM_ANG), dy, FLOOR_B + 2.0 + 2.1 * math.sin(ARM_ANG)), M["lego"], RB,
                       rot=(0, -ARM_ANG, math.pi / 2), origin="center", kit=KIT["liftarm"]))
Bp.append(stl_part("Servo horn shoulder", "1 x 5 Servo Horn.STL", (3.2 + 1.0, 1.6, FLOOR_B + 2.0 + 0.5), M["metal"], RB, rot=(0, -ARM_ANG, math.pi / 2), origin="center", kit=KIT["horn"]))
CLAW_X = 3.2 + 4.2 * math.cos(ARM_ANG) + 0.8
CLAW_Z = FLOOR_B + 2.0 + 4.2 * math.sin(ARM_ANG)
Bp.append(stl_part("Servo bracket claw", "Servo Bracket.STL", (CLAW_X, 1.6, CLAW_Z - 0.6), M["metal"], RB, kit=KIT["bracket"]))
Bp.append(servo_box(RB, "Servo claw (micro)", (CLAW_X + 0.3, 1.6, CLAW_Z + 0.2), micro=True))
for d in (-1, 1):
    Bp.append(stl_part(f"Claw finger {'L' if d > 0 else 'R'}", "1 x 9 Liftarm Bent (3 x 7).STL", (CLAW_X + 1.6, 1.6 + d * 0.9, CLAW_Z - 0.3), M["lego"], RB,
                       rot=(0, 0, d * math.radians(25)), origin="center", kit=KIT["liftarm"]))
# V plow: two 4x12 plates bent, bolted to the chassis front corners
for sy in (-1, 1):
    Bp.append(stl_part(f"Plow wing {'L' if sy > 0 else 'R'}", "Plate 4x12.STL", (4.3 + 1.6, sy * 2.6, 0.2), M["metal"], RB,
                       rot=(math.pi / 2, 0, -sy * math.radians(32)), origin="center", kit=KIT["plate"], note="bent 90deg 2.5in from one end; short leg bolted to the chassis flange"))
# cup hook: servo on the right flange with a bent 1x19 strap
Bp.append(stl_part("Servo bracket hook", "Servo Bracket.STL", (0.8, -(CH_W / 2 + 0.9), FLOOR_B + 0.3), M["metal"], RB, rot=(0, 0, math.pi / 2), kit=KIT["bracket"]))
Bp.append(servo_box(RB, "Servo cup hook", (0.8, -(CH_W / 2 + 0.9), FLOOR_B + 1.0), rot=(0, 0, math.pi / 2)))
Bp.append(stl_part("Hook strap 1x10", "Strap 1x10.STL", (1.3 + 3.15, -(CH_W / 2 + 1.4), FLOOR_B + 2.2), M["metal"], RB,
                   rot=(0, 0, 0), origin="center", kit=KIT["strap10"], note="bent 90deg 1.5in from the end: tip points down under the cup rim"))
Bp.append(est("box", "Hook tip (same strap, bent)", (1.3 + 6.3, -(CH_W / 2 + 1.4), FLOOR_B + 1.5), (0.08, 0.5, 1.4), M["metal"], kit="strap10", collection=RB))
# camera mast
Bp.append(stl_part("Camera mast channel 3x8", "Channel 3x8.STL", (-3.3, 1.9, FLOOR_B + 0.05), M["metal"], RB, rot=(0, math.pi / 2, 0), origin="bottom", kit=KIT["ch8"]))
Bp.append(est("box", "Camera", (-3.0, 1.9, FLOOR_B + 5.0 + 0.5), (1.0, 2.9, 1.1), M["camera"], kit="camera", collection=RB, rot=(0, math.radians(-35), 0)))
Bp.append(est("box", "Tophat L", (3.0, 1.0, 0.45), (0.6, 0.45, 0.5), M["sensor"], kit="tophat", collection=RB))
Bp.append(est("box", "Tophat R", (3.0, -1.0, 0.45), (0.6, 0.45, 0.5), M["sensor"], kit="tophat", collection=RB))
Bp.append(est("box", "Light sensor (start)", (-3.3, -1.8, FLOOR_B + 1.25 + WOMBAT[2] + 0.2), (0.5, 0.5, 0.4), M["sensor"], kit="light", collection=RB))
Bp.append(est("box", "Lever switch (plow)", (7.6, 0, 0.9), (0.3, 1.0, 0.5), M["sensor"], kit="lever", collection=RB))
Bp.append(est("box", "ET rangefinder", (CH_L / 2 + 0.2, -1.6, FLOOR_B + 0.7), (0.3, 1.1, 0.6), M["sensor"], kit="et", collection=RB))
rootB = bpy.data.objects.new("ROBOT_B_root", None)
RB.objects.link(rootB)
for o in Bp:
    o.parent = rootB
rootB.location = (35.0, 5.6, 0)      # zone 5 (the large start box), facing east

# robot envelopes vs the start-box limit 21.125 x 11.25 x 12
bpy.context.view_layer.update()
def envelope(root):
    inv = root.matrix_world.inverted()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for ch in root.children:
        for c in ch.bound_box:
            p = inv @ (ch.matrix_world @ Vector(c))
            mn = Vector(map(min, mn, p)); mx = Vector(map(max, mx, p))
    return mn, mx
ENV = {}
for root, name in ((rootA, "A"), (rootB, "B")):
    mn, mx = envelope(root)
    d = mx - mn
    ENV[name] = {"min": [round(v, 2) for v in mn], "max": [round(v, 2) for v in mx]}
    print(f"ENVELOPE {name}: {d.x:.2f} long x {d.y:.2f} wide x {d.z:.2f} tall (limit 21.125 x 11.25 x 12); local x {mn.x:.2f}..{mx.x:.2f}, y {mn.y:.2f}..{mx.y:.2f}")
with open(os.path.join(OUT, "envelopes.json"), "w") as f:
    json.dump(ENV, f)

# showcase copies off the table
SHOW = coll("Robot showcase (off table)")
def showcase(root, dx, name):
    nr = bpy.data.objects.new(name, None)
    SHOW.objects.link(nr)
    for ch in root.children:
        c = ch.copy(); c.data = ch.data
        SHOW.objects.link(c); c.parent = nr
    nr.location = (dx, -16, 0)
    return nr
showcase(rootA, 30, "SHOWCASE_A")
showcase(rootB, 55, "SHOWCASE_B")

# ---------------------------------------------------------------- lights, cameras, renders
scene = bpy.context.scene
world = bpy.data.worlds.new("World"); world.color = (0.9, 0.9, 0.92); scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sun.data.energy = 3
sun.rotation_euler = (math.radians(40), math.radians(10), math.radians(30)); scene.collection.objects.link(sun)
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True; sh.show_object_outline = True
scene.render.resolution_x, scene.render.resolution_y = 1800, 1100

def camera(name, loc, target, ortho=None, lens=35):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    cam.data.lens = lens; cam.data.clip_end = 2000
    return cam
shots = [
    ("field_iso", camera("Cam iso", (10, -60, 70), (48, 20, 0), lens=30)),
    ("field_top", camera("Cam top", (IN_W / 2, 14.0, 150), (IN_W / 2, 14.0, 0), ortho=112)),
    ("robot_A", camera("Cam robot A", (30 + 18, -16 - 16, 14), (30, -16, 2.0), lens=50)),
    ("robot_A_low", camera("Cam robot A low", (30 + 22, -16 - 6, 2.5), (30, -16, 1.5), lens=50)),
    ("robot_B", camera("Cam robot B", (55 + 18, -16 - 16, 15), (55, -16, 3.0), lens=50)),
    ("start_box", camera("Cam start box", (50, -14, 26), (50, 8, 2), lens=40)),
]
os.makedirs(OUT, exist_ok=True)
for fname, cam in shots:
    scene.camera = cam
    scene.render.filepath = os.path.join(OUT, f"{fname}.png")
    bpy.ops.render.render(write_still=True)
scene.camera = shots[0][1]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fall_game_2026.blend"))

from collections import Counter
for root, title in ((rootA, "Robot A - Duck Runner"), (rootB, "Robot B - Point Scorer")):
    cnt = Counter(ch.get("kit", "NOT IN KIT: " + ch.name if ch.name.startswith("NOT_IN") else None) for ch in root.children if "roller" not in ch.name and "screen" not in ch.name)
    print(f"PARTS {title}:")
    for k, v in sorted((k, v) for k, v in cnt.items() if k):
        print(f"   {v} x {k}")
print("DONE", OUT)

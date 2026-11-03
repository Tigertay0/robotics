"""Export both robots as fine-grained, step-tagged 3D assemblies for the wordless build
manual, and check the bill of materials against the 2026 kit.

    blender -b --factory-startup --python tools/blender/export_build_manual.py -- docs/manual

Writes <out>/robot_a.glb, <out>/robot_b.glb, <out>/steps.json, <out>/bom.md.
Units mm; +X = robot forward, +Y = left, +Z = up from the floor.

Every mesh is named "<SS>.<ss>|<part name>" (step . sub-step). steps.json describes,
for every sub-step: what goes in (callout: kit name, qty, kind, screw length), how it
goes in (each item's insertion direction, used for the fly-in arrows), an optional
close-up point (for the magnifier inset), sub-assemblies built on the side, and
pictogram hints ("mecanum_x", "gate_open_closed", "repeat_x3", "rotate").

Rules enforced (exit with an error otherwise): every part / screw / nut is an item of
data/kit_2026.json (exact names from the official 2026 kit lists) or one of the 4 team
prints; both robots together never use more than the kit holds; <= 4 printed parts.
Kit parts are simple stand-in shapes sized from the Blender table model and the part
scripts; the 4 printed parts are the real STLs from parts/team4.
"""
import json
import math
import os
import sys
from collections import Counter

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(ROOT, "docs", "manual"))
os.makedirs(OUT, exist_ok=True)
TEAM4 = os.path.join(ROOT, "parts", "team4")
KIT = json.load(open(os.path.join(ROOT, "data", "kit_2026.json"), encoding="utf-8"))
IN = 25.4
S14, S12, S34 = 'Screw 8-32 x 1/4" (black)', 'Screw 8-32 x 1/2" (black)', 'Screw 8-32 x 3/4" (black)'
SLEN = {S14: 0.25 * IN, S12: 0.5 * IN, S34: 0.75 * IN}
KEPS = "Nut 8-32 Keps (black)"
M3S, M3N = "Silver Servo Horn Machine Screw (M3)", "Silver Servo Horn Nut (M3)"
HORNS = "Short Silver Servo Horn Screw (M3)"
ZIP = 'Zip tie 4" (white), structural'
PRINTS = {"Printed chassis (print 1)", "Geared claw (print 2)", "Pocket plow (print 3)", "Cup hook (print 4)"}

bpy.ops.wm.read_factory_settings(use_empty=True)
MATS = {}


def mat(name, rgb, metal=0.0, rough=0.5):
    if name not in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*rgb, 1)
        b.inputs["Metallic"].default_value = metal
        b.inputs["Roughness"].default_value = rough
        MATS[name] = m
    return MATS[name]


C = {
    "pla": ((0.62, 0.64, 0.68), 0.0, 0.6), "metal": ((0.78, 0.79, 0.81), 0.8, 0.35),
    "motor": ((0.06, 0.06, 0.07), 0.0, 0.6), "servo": ((0.10, 0.10, 0.12), 0.0, 0.5),
    "sensor": ((0.13, 0.42, 0.85), 0.0, 0.4), "wombat": ((0.05, 0.05, 0.06), 0.0, 0.4),
    "screen": ((0.12, 0.45, 0.62), 0.0, 0.2), "battery": ((0.18, 0.22, 0.62), 0.0, 0.5),
    "roller": ((0.25, 0.25, 0.27), 0.0, 0.7), "lego": ((0.55, 0.57, 0.60), 0.0, 0.5),
    "screw": ((0.12, 0.12, 0.13), 0.6, 0.35), "silver": ((0.80, 0.80, 0.82), 0.9, 0.25),
    "hub": ((0.85, 0.85, 0.85), 0.2, 0.4), "zip": ((0.95, 0.95, 0.93), 0.0, 0.6),
    "tyre": ((0.08, 0.08, 0.08), 0.0, 0.8), "brass": ((0.78, 0.62, 0.25), 0.8, 0.3),
    "hole": ((0.02, 0.02, 0.02), 0.0, 0.9), "label": ((0.93, 0.93, 0.90), 0.0, 0.6),
    "wire_r": ((0.80, 0.10, 0.08), 0.0, 0.5), "wire_b": ((0.20, 0.13, 0.08), 0.0, 0.5),
    "wire_y": ((0.95, 0.62, 0.10), 0.0, 0.5), "lens": ((0.04, 0.07, 0.12), 0.3, 0.1),
    "dome": ((0.92, 0.86, 0.55), 0.0, 0.2), "can": ((0.42, 0.42, 0.45), 0.8, 0.35),
    "button": ((0.85, 0.12, 0.10), 0.0, 0.4), "claw_finger": ((0.95, 0.55, 0.15), 0.0, 0.5),
}


def M(k):
    rgb, metal, rough = C[k]
    return mat(k, rgb, metal, rough)


coll = bpy.data.collections.new("manual_export")
bpy.context.scene.collection.children.link(coll)
CUR = {"tag": "00.0", "items": None}


def put(o, name, material, dir_=None):
    """material: one material, or a list (a composite part whose faces carry material indices)."""
    o.name = f"{CUR['tag']}|{name}"
    if o.data is not None and hasattr(o.data, "materials"):
        o.data.materials.clear()
        for mm in (material if isinstance(material, list) else [material]):
            o.data.materials.append(mm)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    coll.objects.link(o)
    if CUR["items"] is not None:
        CUR["items"].append({"mesh": o.name, "dir": [round(v, 3) for v in (dir_ or (0, 0, -1))]})
    return o


def box(name, lo, hi, m, tf=None, dir_=None, shaft=None):
    """A kit part filling the box lo..hi. Recognisable kit parts (servos, motors, liftarms,
    horns, sensors, Wombat...) are drawn with their real features inside that box;
    shaft = (direction, point) for servos."""
    shape = SHAPES.get(name)
    if shape is not None:
        cp = Comp()
        shape(cp, [min(a, b) for a, b in zip(lo, hi)], [max(a, b) for a, b in zip(lo, hi)],
              name=name, dir_=dir_ or (0, 0, -1), shaft=shaft, m=m)
        return cp.finish(name, tf, dir_)
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.data.transform(Matrix.Translation([(a + b) / 2 for a, b in zip(lo, hi)]) @ Matrix.Diagonal((*[b - a for a, b in zip(lo, hi)], 1)))
    if tf is not None:
        o.data.transform(tf)
    return put(o, name, M(m), dir_)


def _axis_rot(axis_vec):
    v = Vector(axis_vec).normalized()
    return Vector((0, 0, 1)).rotation_difference(v).to_matrix().to_4x4()


def cyl(name, c, d, h, axis, m, verts=32, dir_=None, tf=None):
    """Cylinder centred at c; axis is 'X'/'Y'/'Z' or a vector."""
    vec = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}.get(axis, axis) if isinstance(axis, str) else axis
    shape = ROUND_SHAPES.get(name)
    if shape is not None:
        cp = Comp()
        shape(cp, Vector(c), d, h, Vector(vec).normalized(), m)
        return cp.finish(name, tf, dir_)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=d / 2, depth=h)
    o = bpy.context.active_object
    o.data.transform(Matrix.Translation(c) @ _axis_rot(vec))
    if tf is not None:
        o.data.transform(tf)
    return put(o, name, M(m), dir_)


def screw(kind, head_at, dir_, tf=None):
    """A kit screw: head sitting on the surface at head_at, shank going along dir_ (= insertion)."""
    d = Vector(dir_).normalized()
    L = SLEN.get(kind, 0.5 * IN)
    hd, hh, sd = (7.2, 2.8, 4.1) if "8-32" in kind else (5.6, 2.2, 3.0) if "M3" in kind else (4.4, 1.8, 2.2)
    m = "silver" if ("M3" in kind or "2-56" in kind) else "brass" if "Brass" in kind else "screw"
    hp = Vector(head_at) - d * (hh / 2)
    a = cyl(kind, tuple(hp), hd, hh, tuple(d), m, 14, dir_, tf)
    sp = Vector(head_at) + d * (L / 2)
    b = cyl(kind + " (shank)", tuple(sp), sd, L, tuple(d), m, 10, dir_, tf)
    target("screw", kind, head_at, d, L, tf)
    return a, b


def target(kind, name, at, d, length, tf=None):
    """Record where a fastener goes (for the viewer's pulsing ring + arrow into the hole)."""
    if CUR.get("targets") is None:
        return
    p = Vector(at)
    if tf is not None:
        p = tf @ p
        d = (tf.to_3x3() @ Vector(d)).normalized()
    CUR["targets"].append({"kind": kind, "name": name, "at": [round(v, 2) for v in p],
                           "dir": [round(v, 3) for v in d], "len_mm": round(length, 1)})


def nut(kind, at, dir_, tf=None):
    d = Vector(dir_).normalized()
    af, t = (8.7, 3.2) if "8-32" in kind else (5.5, 2.4)
    target("nut", kind, at, d, t, tf)
    return cyl(kind, tuple(at), af * 1.1547, t, tuple(d), "screw" if "8-32" in kind else "silver", 6, dir_, tf)


def stl(name, file, m, rot_z=0.0, x=None, y=None, z=None, ref=("min", "center", "min"), dir_=(0, 0, -1)):
    bpy.ops.wm.stl_import(filepath=os.path.join(TEAM4, file))
    o = bpy.context.selected_objects[0]
    if rot_z:
        o.data.transform(Matrix.Rotation(math.radians(rot_z), 4, "Z"))
    vs = [v.co for v in o.data.vertices]
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    dlt = [0.0, 0.0, 0.0]
    for i, (t, r) in enumerate(zip((x, y, z), ref)):
        if t is not None:
            dlt[i] = t - (lo[i] if r == "min" else hi[i] if r == "max" else (lo[i] + hi[i]) / 2)
    o.data.transform(Matrix.Translation(dlt))
    LAST_STL["tf"] = Matrix.Translation(dlt) @ Matrix.Rotation(math.radians(rot_z), 4, "Z")
    return put(o, name, M(m), dir_)


LAST_STL = {"tf": Matrix.Identity(4)}


def mecanum(name, cx, cy, cz, d=60.0, w=28.0, dir_=None):
    cyl(name, (cx, cy, cz), d - 12, w * 0.7, "Y", "hub", 28, dir_)
    for k in range(10):
        a = 2 * math.pi * k / 10
        r = d / 2 - 6
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=6, depth=w * 0.95)
        o = bpy.context.active_object
        o.data.transform(Matrix.Translation((cx + r * math.cos(a), cy, cz + r * math.sin(a)))
                         @ Matrix.Rotation(-a, 4, "Y") @ Matrix.Rotation(math.radians(45 if cy > 0 else -45), 4, "X")
                         @ Matrix.Rotation(math.radians(90), 4, "X"))
        put(o, name + " roller", M("roller"), dir_)


# ---------------------------------------------------------------- recognisable kit-part shapes
class Comp:
    """One mesh built from boxes and cylinders, each with its own material."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, key):
        if key not in self.mats:
            self.mats.append(key)
        return self.mats.index(key)

    def _tag(self, verts, key):
        mi = self._mi(key)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mi

    def box(self, lo, hi, key):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        c = [(a + b) / 2 for a, b in zip(lo, hi)]
        s = [abs(b - a) for a, b in zip(lo, hi)]
        for v in r["verts"]:
            v.co = Vector((c[0] + v.co.x * s[0], c[1] + v.co.y * s[1], c[2] + v.co.z * s[2]))
        self._tag(r["verts"], key)

    def cyl(self, c, d, h, axis, key, segs=20):
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs, radius1=d / 2, radius2=d / 2,
                                  depth=h, matrix=Matrix.Translation(Vector(c)) @ _axis_rot(tuple(axis)))
        self._tag(r["verts"], key)

    def finish(self, name, tf, dir_):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        if tf is not None:
            me.transform(tf)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return put(o, name, [M(k) for k in self.mats], dir_)


def _ax(i, s=1.0):
    v = [0.0, 0.0, 0.0]
    v[i] = s
    return v


def _place(vals):
    p = [0.0, 0.0, 0.0]
    for i, v in vals.items():
        p[i] = v
    return p


def _split_axes(lo, hi):
    d = [b - a for a, b in zip(lo, hi)]
    order = sorted(range(3), key=lambda i: d[i])
    return d, order                   # order[0] thinnest .. order[2] longest


def shape_liftarm(cp, lo, hi, name, dir_, m, **_):
    """LEGO beam: rounded ends and a row of pin holes."""
    d, order = _split_axes(lo, hi)
    La = order[2]
    shorts = [i for i in range(3) if i != La]
    ha = max(shorts, key=lambda i: abs(dir_[i]))          # pins go in along the insertion direction
    wa = [i for i in shorts if i != ha][0]
    n = int(name.split("x")[1].split()[0]) if "x" in name else 5
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    w = d[wa]
    lo2, hi2 = list(lo), list(hi)
    lo2[La], hi2[La] = lo[La] + w / 2, hi[La] - w / 2
    cp.box(lo2, hi2, "lego")
    for e in (lo[La] + w / 2, hi[La] - w / 2):
        cp.cyl(_place({La: e, wa: c[wa], ha: c[ha]}), w, d[ha], _ax(ha), "lego", 20)
    pitch = d[La] / n
    for k in range(n):
        cp.cyl(_place({La: lo[La] + (k + 0.5) * pitch, wa: c[wa], ha: c[ha]}), min(4.8, 0.6 * w), d[ha] + 0.3, _ax(ha), "hole", 14)


def shape_horn_bar(cp, lo, hi, **_):
    """1 x 5 servo horn: flat bar, 5 holes, centre hub on the servo spline."""
    d, order = _split_axes(lo, hi)
    ta, wa, La = order
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    lo2, hi2 = list(lo), list(hi)
    lo2[La], hi2[La] = lo[La] + d[wa] / 2, hi[La] - d[wa] / 2
    cp.box(lo2, hi2, "metal")
    for e in (lo2[La], hi2[La]):
        cp.cyl(_place({La: e, wa: c[wa], ta: c[ta]}), d[wa], d[ta], _ax(ta), "metal", 18)
    cp.cyl(c, 10, d[ta] + 2.0, _ax(ta), "metal", 20)
    pitch = min(12.7, d[La] / 5)
    for k in range(-2, 3):
        cp.cyl(_place({La: c[La] + k * pitch, wa: c[wa], ta: c[ta]}), 3.4, d[ta] + 2.3, _ax(ta), "hole", 12)


def shape_servo(cp, lo, hi, name, shaft, **_):
    """Servo: body, mounting ears with holes, round boss + output spline, label, 3-wire lead."""
    micro = name.startswith("Micro")
    sdir, sat = shaft if shaft else ((0, 0, 1), None)
    a = max(range(3), key=lambda i: abs(sdir[i]))
    s = 1.0 if sdir[a] > 0 else -1.0
    others = [i for i in range(3) if i != a]
    d = [b - x for x, b in zip(lo, hi)]
    La = max(others, key=lambda i: d[i])
    Wa = [i for i in others if i != La][0]
    c = [(x + b) / 2 for x, b in zip(lo, hi)]
    cp.box(lo, hi, "servo")
    face = hi[a] if s > 0 else lo[a]
    ear = 4.5 if micro else 7.0
    ez = face - s * 0.22 * d[a]
    lo_e, hi_e = list(lo), list(hi)
    lo_e[La], hi_e[La] = lo[La] - ear, hi[La] + ear
    lo_e[a], hi_e[a] = ez - 1.25, ez + 1.25
    cp.box(lo_e, hi_e, "servo")
    for e in (lo[La] - ear / 2, hi[La] + ear / 2):
        for w in (-0.25, 0.25):
            cp.cyl(_place({La: e, Wa: c[Wa] + w * d[Wa], a: ez}), 2.2 if micro else 3.2, 2.8, _ax(a), "hole", 10)
    sp = list(c)
    sp[La] = sat[La] if sat is not None else lo[La] + 0.72 * d[La]
    sp[Wa] = sat[Wa] if sat is not None else c[Wa]
    boss = dict(enumerate(sp))
    boss[a] = face + s * 0.75
    cp.cyl(_place(boss), 0.7 * d[Wa], 1.5, _ax(a), "servo", 20)
    boss[a] = face + s * 3.0
    cp.cyl(_place(boss), 4.8 if micro else 6.0, 4.5, _ax(a), "silver", 16)
    lab_lo, lab_hi = list(lo), list(hi)
    lab_lo[Wa], lab_hi[Wa] = hi[Wa] - 0.1, hi[Wa] + 0.4
    lab_lo[La], lab_hi[La] = c[La] - 0.32 * d[La], c[La] + 0.32 * d[La]
    lab_lo[a], lab_hi[a] = c[a] - 0.25 * d[a], c[a] + 0.15 * d[a]
    cp.box(lab_lo, lab_hi, "label")
    tail = lo[La] if sp[La] > c[La] else hi[La]
    sgn = -1.0 if sp[La] > c[La] else 1.0
    for k, key in enumerate(("wire_b", "wire_r", "wire_y")):
        cp.cyl(_place({La: tail + sgn * 6, Wa: c[Wa] + (k - 1) * 1.6, a: c[a] - s * 0.3 * d[a]}), 1.5, 12, _ax(La), key, 8)


def shape_motor(cp, lo, hi, dir_, **_):
    """Black gear motor: gearbox block + round motor can + label + 2 wires; shaft faces -dir_."""
    a = max(range(3), key=lambda i: abs(dir_[i]))
    s = -1.0 if dir_[a] > 0 else 1.0                   # shaft side
    d = [b - x for x, b in zip(lo, hi)]
    c = [(x + b) / 2 for x, b in zip(lo, hi)]
    others = [i for i in range(3) if i != a]
    front = hi[a] if s > 0 else lo[a]
    split = front - s * 0.55 * d[a]
    g_lo, g_hi = list(lo), list(hi)
    g_lo[a], g_hi[a] = sorted((front, split))
    cp.box(g_lo, g_hi, "motor")
    can_d = 0.95 * min(d[i] for i in others)
    back = lo[a] if s > 0 else hi[a]
    can_c = list(c)
    can_c[a] = (split + back) / 2
    cp.cyl(can_c, can_d, abs(split - back), _ax(a), "can", 24)
    lab_lo, lab_hi = list(g_lo), list(g_hi)
    o0 = max(others, key=lambda i: d[i])
    lab_lo[o0], lab_hi[o0] = c[o0] - 0.3 * d[o0], c[o0] + 0.3 * d[o0]
    o1 = [i for i in others if i != o0][0]
    lab_lo[o1], lab_hi[o1] = hi[o1] - 0.1, hi[o1] + 0.4
    cp.box(lab_lo, lab_hi, "label")
    for k, key in enumerate(("wire_r", "wire_b")):
        p = list(can_c)
        p[a] = back - s * 5
        p[o0] += (k - 0.5) * 4
        cp.cyl(p, 1.6, 10, _ax(a), key, 8)


def shape_wombat(cp, lo, hi, **_):
    """Wombat controller: case, button row, USB/motor/servo port blocks, power switch."""
    cp.box(lo, hi, "wombat")
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    for k in range(3):
        cp.cyl((x1 - 14, -14 + 14 * k, z1 + 0.8), 6, 1.6, (0, 0, 1), "button", 14)
    for k in range(6):
        cp.box((x0 + 12 + 14 * k, y0 - 1.2, z0 + 8), (x0 + 22 + 14 * k, y0 + 0.2, z0 + 15), "silver")
        cp.box((x0 + 12 + 14 * k, y1 - 0.2, z0 + 8), (x0 + 22 + 14 * k, y1 + 1.2, z0 + 15), "motor")
    cp.box((x0 - 1.2, -8, z0 + 10), (x0 + 0.2, 8, z0 + 22), "silver")
    cp.box((x1 - 0.2, 20, z0 + 12), (x1 + 2.0, 30, z0 + 20), "button")


def shape_battery(cp, lo, hi, **_):
    cp.box(lo, hi, "battery")
    d, order = _split_axes(lo, hi)
    La = order[2]
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    lab_lo, lab_hi = [v - 0.2 for v in lo], [v + 0.2 for v in hi]
    lab_lo[La], lab_hi[La] = c[La] - 0.18 * d[La], c[La] + 0.18 * d[La]
    cp.box(lab_lo, lab_hi, "label")
    for k, key in enumerate(("wire_r", "wire_b")):
        p = list(c)
        p[La] = hi[La] + 7
        p[order[1]] += (k - 0.5) * 4
        cp.cyl(p, 2.0, 14, _ax(La), key, 8)
    p = list(c)
    p[La] = hi[La] + 16
    cp.box([v - 3.5 for v in p], [v + 3.5 for v in p], "wombat")


def shape_zip(cp, lo, hi, **_):
    cp.box(lo, hi, "zip")
    d, order = _split_axes(lo, hi)
    La = order[2]
    h_lo, h_hi = [v - 1.0 for v in lo], [v + 1.0 for v in hi]
    h_lo[La], h_hi[La] = hi[La] - 4.5, hi[La] + 0.5
    cp.box(h_lo, h_hi, "zip")


def shape_et(cp, lo, hi, **_):
    """ET rangefinder: blue board, two round lenses on the +X (sensing) face, 3-pin plug."""
    cp.box(lo, hi, "sensor")
    cy, cz = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
    dy = 0.27 * (hi[1] - lo[1])
    for y in (cy - dy, cy + dy):
        cp.cyl((hi[0] + 1.5, y, cz), 8.0, 3.0, (1, 0, 0), "lens", 18)
    cp.box((lo[0] - 3, cy - 4, cz - 2), (lo[0], cy + 4, cz + 2), "motor")


def shape_light(cp, lo, hi, **_):
    """Light sensor: small board with a round light-dependent cell facing up."""
    zt = lo[2] + 0.45 * (hi[2] - lo[2])
    cp.box(lo, (hi[0], hi[1], zt), "sensor")
    c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
    cp.cyl((c[0], c[1], (zt + hi[2]) / 2), 0.75 * (hi[0] - lo[0]), hi[2] - zt, (0, 0, 1), "dome", 18)


def shape_touch(cp, lo, hi, **_):
    """Small touch switch: body with a red push button on the +Y face (into the lane)."""
    cp.box(lo, hi, "sensor")
    cp.cyl(((lo[0] + hi[0]) / 2, hi[1] + 1.5, (lo[2] + hi[2]) / 2), 5.0, 3.0, (0, 1, 0), "button", 14)


def shape_lever(cp, lo, hi, **_):
    """Lever switch: body at the back, metal lever reaching forward (+X) with a roller."""
    xm = lo[0] + 0.45 * (hi[0] - lo[0])
    cp.box(lo, (xm, hi[1], hi[2]), "sensor")
    zc = (lo[2] + hi[2]) / 2
    cp.box((xm, lo[1] + 2, zc - 0.4), (hi[0] - 2, hi[1] - 2, zc + 0.4), "silver")
    cp.cyl((hi[0] - 2.5, (lo[1] + hi[1]) / 2, zc), 5.0, 4.0, (0, 0, 1), "silver", 14)


def shape_camera(cp, lo, hi, **_):
    """Camera: dark body, lens with a silver ring on the +X face, USB lead at the back."""
    cp.box(lo, hi, "motor")
    cy, cz = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
    cp.cyl((hi[0] + 2.0, cy, cz), 18, 4.0, (1, 0, 0), "silver", 24)
    cp.cyl((hi[0] + 3.0, cy, cz), 12, 4.5, (1, 0, 0), "lens", 24)
    cp.cyl((lo[0] - 6, cy, cz), 3.0, 12, (1, 0, 0), "wombat", 8)


def shape_caster(cp, lo, hi, **_):
    """Ball caster: square mounting flange on top, round housing below (ball added separately)."""
    cp.box((lo[0], lo[1], hi[2] - 2), (hi[0], hi[1], hi[2]), "metal")
    c = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
    cp.cyl((c[0], c[1], (lo[2] + hi[2] - 2) / 2), 0.8 * (hi[0] - lo[0]), hi[2] - 2 - lo[2], (0, 0, 1), "metal", 24)


def shape_channel(cp, lo, hi, **_):
    """Channel 3 x 8: U-section, back plate on the +X side, flanges toward -X, hole grid in the back."""
    cp.box((hi[0] - 2, lo[1], lo[2]), hi, "metal")
    for y0, y1 in ((lo[1], lo[1] + 2), (hi[1] - 2, hi[1])):
        cp.box((lo[0], y0, lo[2]), (hi[0], y1, hi[2]), "metal")
    py, pz = (hi[1] - lo[1]) / 3, (hi[2] - lo[2]) / 8
    for j in range(3):
        for k in range(8):
            cp.cyl((hi[0] - 1, lo[1] + (j + 0.5) * py, lo[2] + (k + 0.5) * pz), 4.0, 2.4, (1, 0, 0), "hole", 10)


def round_horn(cp, c, d, h, ax, m):
    """Round servo horn: disc, raised hub, ring of 8 holes."""
    cp.cyl(c, d, h, ax, "metal", 28)
    cp.cyl(c + ax * (h / 2), 9, 2.0, ax, "metal", 20)
    ref = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(ref).normalized()
    v = ax.cross(u)
    for k in range(8):
        a = 2 * math.pi * k / 8
        cp.cyl(c + (u * math.cos(a) + v * math.sin(a)) * 7.0, 2.6, h + 0.4, ax, "hole", 10)
    cp.cyl(c, 3.2, h + 2.4, ax, "hole", 10)


def tophat(cp, c, d, h, ax, m):
    """Tophat reflectance sensor: barrel, brim on top, IR emitter + receiver under it."""
    cp.cyl(c, d * 0.75, h, ax, "sensor", 20)
    cp.cyl(c + ax * (h / 2 - 1), d * 1.25, 2.0, ax, "sensor", 24)
    ref = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = ax.cross(ref).normalized()
    for sgn in (-1, 1):
        cp.cyl(c - ax * (h / 2 + 0.4) + u * (sgn * d * 0.18), 3.5, 1.2, ax, "lens", 12)


def friction_pin(cp, c, d, h, ax, m):
    """LEGO friction pin: black shaft with a collar in the middle."""
    cp.cyl(c, d, h, ax, "motor", 14)
    cp.cyl(c, d + 1.6, 1.4, ax, "motor", 14)


SHAPES = {"1 x 3 Liftarm": shape_liftarm, "1 x 5 Liftarm": shape_liftarm, "1 x 7 Liftarm": shape_liftarm,
          "1 x 11 Liftarm": shape_liftarm, "1 x 5 Servo Horn": shape_horn_bar, "Servo": shape_servo,
          "Micro Servo": shape_servo, "Black Gear Motor": shape_motor, "Wombat": shape_wombat,
          "Wombat Battery": shape_battery, "Zip tie": shape_zip, "ET (Rangefinder)": shape_et, "Light": shape_light,
          "Small Touch": shape_touch, "Lever": shape_lever, "Black Camera": shape_camera, "Caster": shape_caster,
          "Channel 3 x 8": shape_channel}
ROUND_SHAPES = {"Round Servo Horn": round_horn, "Tophat (Reflectance)": tophat, "Pin w/ Friction": friction_pin}

STEPS = {"A": [], "B": []}
ROBOT = {"cur": "A"}


def step(title, hint=None):
    """Start a numbered step (big number on the page). Title is a short English label (optional on the page)."""
    S = STEPS[ROBOT["cur"]]
    S.append({"n": len(S) + 1, "title": title, "hint": hint, "subs": []})


def sub(note, parts, zoom=None, hint=None, subassembly=None):
    """Start a sub-step: one action. parts = [(kit name, qty)]."""
    st = STEPS[ROBOT["cur"]][-1]
    k = len(st["subs"]) + 1
    CUR["tag"] = f"{st['n']:02d}.{k}"
    items, targets = [], []
    CUR["items"], CUR["targets"] = items, targets
    callout = []
    for name, q in parts:
        e = {"name": name, "qty": q, "kind": "print" if name in PRINTS else "kit"}
        if name in PRINTS:
            e["badge"] = "3D PRINTED"
        if name in SLEN:
            e["length_mm"] = round(SLEN[name], 1)
        callout.append(e)
    if any(n in PRINTS for n, _ in parts) and not note.startswith("3D PRINTED"):
        note = "3D PRINTED part. " + note
    st["subs"].append({"tag": CUR["tag"], "note": note, "parts": callout, "items": items, "targets": targets,
                       "zoom": [round(v, 1) for v in zoom] if zoom else None, "hint": hint, "subassembly": subassembly})


def export(path):
    for o in bpy.context.scene.objects:
        o.select_set(o.name in coll.objects)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)


# ============================================================================ ROBOT A
ROBOT["cur"] = "A"
L, W = 214.0, 180.0
DECK_Z, DECK_T = 46.0, 5.0
half, LANE_T = 1.8 * IN / 2, 3.5
side_y = W / 2
top = DECK_Z + DECK_T

step("Printed chassis")
sub("Print 1, deck side down. Clear every 4.4 mm hole with a drill.", [("Printed chassis (print 1)", 1)], hint="print_check")
stl("Printed chassis (print 1)", "p1_chassis_a.stl", "pla", x=0, y=0, z=4.0, ref=("center", "center", "min"))


def motor_corner(xw, sy, detailed):
    out_end = xw + (10.2 if xw > 0 else -10.2)
    x0, x1 = sorted((out_end, out_end - (40.6 if xw > 0 else -40.6)))
    cx = (x0 + x1) / 2
    inward = (0, -sy, 0)
    ya, yb = sy * (side_y + 12.0), sy * (side_y + 12.0 - 38.0)
    if detailed:
        sub("Slide the motor into the window from outside, shaft facing out.", [("Black Gear Motor", 1)],
            zoom=(cx, sy * side_y, 30))
    box("Black Gear Motor", (x0, min(ya, yb), 19.85), (x1, max(ya, yb), 40.15), "motor", dir_=inward)
    box("Black Gear Motor (ear)", (x0 - 7, min(sy * side_y, sy * (side_y + 2.4)), 17), (x1 + 7, max(sy * side_y, sy * (side_y + 2.4)), 43), "motor", dir_=inward)
    cyl("Black Gear Motor (shaft)", (xw, sy * (side_y + 15), 30), 5, 8, "Y", "metal", 16, inward)
    if detailed:
        sub("4 screws through the motor ears into the wall.", [(S12, 4)], zoom=(cx, sy * side_y, 30))
    for dx in (-24.25, 24.25):
        for dz in (-5, 5):
            screw(S12, (cx + dx, sy * (side_y + 2.4), 30 + dz), inward)
    if detailed:
        sub("4 Keps nuts on the inside, tighten.", [(KEPS, 4)], zoom=(cx, sy * (side_y - 8), 30))
    for dx in (-24.25, 24.25):
        for dz in (-5, 5):
            nut(KEPS, (cx + dx, sy * (side_y - SIDE_T - 1.6), 30 + dz), (0, sy, 0))


SIDE_T = 4.0
step("Drive motors", hint="repeat_x4")
motor_corner(88.0, +1, True)
sub("Same for the other 3 corners.", [("Black Gear Motor", 3), (S12, 12), (KEPS, 12)], hint="repeat_x3")
for xw, sy in ((88.0, -1), (-88.0, +1), (-88.0, -1)):
    motor_corner(xw, sy, False)

step("Mecanum wheels", hint="mecanum_x")
sub("Wheels on the shafts. Look from above: the rollers must make an X.", [("Mecanum Wheel", 4)], hint="mecanum_x")
for xw in (88.0, -88.0):
    for sy in (-1, 1):
        mecanum("Mecanum Wheel", xw, sy * (side_y + 32), 30, dir_=(0, -sy, 0))
sub("One wheel screw in each hub.", [('M3 x 0.5" x 6" Mecanum Wheel Screw', 4)], zoom=(88, side_y + 46, 30))
for xw in (88.0, -88.0):
    for sy in (-1, 1):
        screw('M3 x 0.5" x 6" Mecanum Wheel Screw', (xw, sy * (side_y + 47), 30), (0, -sy, 0))

step("Intake extension")
for sy in (+1, -1):
    y0 = sy * (half + LANE_T)
    side = "left" if sy > 0 else "right"
    sub(f"Plate on the outside of the {side} lane wall, front end.", [("Plate 4 x 12", 1)], zoom=(L / 2, y0, 25))
    box("Plate 4 x 12", (L / 2 - 26, min(y0, y0 + sy * 2), 4), (L / 2 + 80, max(y0, y0 + sy * 2), 46), "metal", dir_=(0, -sy, 0))
    sub("4 screws from INSIDE the lane, heads stay inside.", [(S12, 4)], zoom=(L / 2 - 14, 0, 25))
    for dx in (8, 20):
        for z in (15, 35):
            screw(S12, (L / 2 - dx, sy * half, z), (0, sy, 0))
    sub("4 Keps nuts outside, tighten.", [(KEPS, 4)], zoom=(L / 2 - 14, y0, 25))
    for dx in (8, 20):
        for z in (15, 35):
            nut(KEPS, (L / 2 - dx, y0 + sy * 3.6, z), (0, -sy, 0))
for sy in (+1, -1):
    y0 = sy * (half + LANE_T)
    sub("Strap on the front end of the plate (2 screws + 2 nuts), then bend it 35 degrees out.",
        [("Strap 1 x 10", 1), (S12, 2), (KEPS, 2)], zoom=(L / 2 + 78, y0, 14), hint="bend_35")
    a = math.radians(sy * 35)
    tf = Matrix.Translation((L / 2 + 66, y0 + sy * 3.0, 0)) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((50.8, 0, 0))
    box("Strap 1 x 10", (-63.5, -1.0, 8), (63.5, 1.0, 20.7), "metal", tf, dir_=(0, -sy, 0))
    for xs in (L / 2 + 62, L / 2 + 74):
        screw(S12, (xs, sy * half, 14.4), (0, sy, 0))
        nut(KEPS, (xs, y0 + sy * 5.2, 14.4), (0, -sy, 0))


def gate(label, gx, servo_kind, z_deck, x_side, note_place):
    """One duck gate: servo stands on a bracket with its shaft along X over the lane centre;
    the horn + liftarm flap hangs through the slot to 10 mm above the floor (closed) and
    swings up flat over the deck (open)."""
    micro = servo_kind == "Micro Servo"
    sb = (23.0, 12.2, 29.0) if micro else (40.6, 20.3, 36.0)        # body: length (Z), width (Y), depth (X)
    shaft_z = z_deck + 4 + (6.0 if micro else 10.0)
    xb0 = gx + x_side * 3.0                                       # body starts 3 mm from the slot
    xs = sorted((xb0, xb0 + x_side * sb[2]))
    # ---- sub-assembly on the side: bracket + servo + horn + flap
    if micro:
        sub(f"{label}: micro servo into the micro servo mount, 2 small screws.",
            [("Micro Servo", 1), ("Micro Servo Mount", 1), ('2-56 3/8" Micro Servo Mount Screw', 2)], subassembly=label,
            zoom=(gx, 0, shaft_z))
        box("Micro Servo Mount", (xs[0] - 2, -16, z_deck), (xs[1] + 2, 16, z_deck + 4), "metal", dir_=(0, 0, -1))
    else:
        sub(f"{label}: servo into the servo bracket, 2 screws + 2 nuts through the servo ears.",
            [("Servo", 1), ("Servo Bracket", 1), (S12, 2), (KEPS, 2)], subassembly=label, zoom=(gx, 0, shaft_z))
        box("Servo Bracket", (xs[0] - 2, -24, z_deck), (xs[1] + 2, 24, z_deck + 2), "metal", dir_=(0, 0, -1))
        for sy_ in (-1, 1):
            box("Servo Bracket", (xs[0] - 2, sy_ * 12.2 - 1, z_deck), (xs[1] + 2, sy_ * 12.2 + 1, z_deck + sb[0] + 4), "metal", dir_=(0, 0, -1))
    box(servo_kind, (xs[0], -sb[1] / 2, z_deck + 4), (xs[1], sb[1] / 2, z_deck + 4 + sb[0]), "servo", dir_=(0, 0, -1),
        shaft=((-x_side, 0, 0), (gx, 0, shaft_z)))
    if micro:
        for z in (z_deck + 8, z_deck + 22):
            screw('2-56 3/8" Micro Servo Mount Screw', (xs[0] + sb[2] / 2, 8.5, z), (0, -1, 0))
    else:
        for z in (z_deck + 10, z_deck + 30):
            screw(S12, (xs[0] + sb[2] / 2, 13.2, z), (0, -1, 0))
            nut(KEPS, (xs[0] + sb[2] / 2, -13.8, z), (0, 1, 0))
    hx = gx + x_side * 1.4
    if micro:
        sub(f"{label}: 1x5 liftarm flap on the servo's own horn, tied with 1 zip tie. Flap points DOWN.",
            [("1 x 5 Liftarm", 1), (ZIP, 1)], subassembly=label, hint="gate_open_closed", zoom=(hx, 0, shaft_z - 20))
        box("1 x 5 Liftarm", (hx - 1.0 - 3.6, -4, 10), (hx - 1.0 + 3.6, 4, shaft_z + 4), "lego", dir_=(-x_side, 0, 0))
        box("Zip tie", (hx - 5, -5, shaft_z - 3), (hx + 5, 5, shaft_z - 1.8), "zip", dir_=(-x_side, 0, 0))
    else:
        sub(f"{label}: 1x5 servo horn on the shaft, pointing DOWN; 1 horn screw in the middle.",
            [("1 x 5 Servo Horn", 1), (HORNS, 1)], subassembly=label, hint="gate_open_closed", zoom=(hx, 0, shaft_z))
        box("1 x 5 Servo Horn", (hx - 1.3, -4.25, shaft_z - 32), (hx + 1.3, 4.25, shaft_z + 32), "metal", dir_=(-x_side, 0, 0))
        screw(HORNS, (hx - x_side * 1.3, 0, shaft_z), (x_side, 0, 0))
        sub(f"{label}: 1x7 liftarm on the lower 2 horn holes, 2 screws + 2 nuts. Its tip is 10 mm above the floor.",
            [("1 x 7 Liftarm", 1), (S12, 2), (KEPS, 2)], subassembly=label, zoom=(hx, 0, shaft_z - 25))
        box("1 x 7 Liftarm", (hx - x_side * 1.3 - 4, -4, 10), (hx - x_side * 1.3 + 4, 4, shaft_z - 6), "lego", dir_=(-x_side, 0, 0))
        for k in (1, 2):
            z = shaft_z - 12.7 * k
            screw(S12, (hx - x_side * 5.3, 0, z), (x_side, 0, 0))
            nut(KEPS, (hx + x_side * 1.3 + 1.6, 0, z), (-x_side, 0, 0))
    sub(f"{label}: {note_place}", [(S14, 2), (KEPS, 2)], zoom=(gx, 0, z_deck), hint="gate_open_closed")
    for sy_ in (-1, 1):
        screw(S14, (xs[0] + sb[2] / 2, sy_ * 20, z_deck + (4 if micro else 2)), (0, 0, -1))
        nut(KEPS, (xs[0] + sb[2] / 2, sy_ * 20, z_deck - DECK_T - 1.6 if z_deck == top else z_deck - 4), (0, 0, 1))


step("Duck gates", hint="gate_open_closed")
gate("Exit gate A", X_REAR := -L / 2 + 10.0, "Servo", top, +1,
     "bracket on the deck over the REAR slot, flap through the slot. 2 screws down, 2 nuts under the deck.")
gate("Pin gate B", -L / 2 + 66.0, "Micro Servo", top, +1,
     "mount on the deck over the MIDDLE slot. 2 screws down, 2 nuts under the deck.")
# intake gate C: on a bridge across the two extension plates, just behind the funnel
sub("Intake gate C: a 1x5 liftarm bridge across the two plates (2 screws + 2 nuts).", [("1 x 5 Liftarm", 1), (S12, 2), (KEPS, 2)], zoom=(L / 2 + 50, 0, 46))
box("1 x 5 Liftarm", (L / 2 + 46, -half - LANE_T - 4, 46), (L / 2 + 54, half + LANE_T + 4, 54), "lego", dir_=(0, 0, -1))
for sy in (-1, 1):
    screw(S12, (L / 2 + 50, sy * (half + LANE_T + 1), 54), (0, 0, -1))
    nut(KEPS, (L / 2 + 50, sy * (half + LANE_T + 1), 41), (0, 0, 1))
gate("Intake gate C", L / 2 + 50.0, "Servo", 54.0, +1, "bracket on the liftarm bridge, flap down into the lane. 2 screws, 2 nuts.")

step("Sensors")
sub("Lane-full touch switch into the window in the right lane wall, 2 brass screws.", [("Small Touch", 1), ("Brass Screws", 2)],
    zoom=(-76, -half - LANE_T, 16))
box("Small Touch", (-83, -half - LANE_T - 7, 11), (-69, -half - LANE_T, 21), "sensor", dir_=(0, 1, 0))
for dx in (-9.5, 9.5):
    screw("Brass Screws", (-76 + dx, -half - LANE_T - 7, 16), (0, 1, 0))
sub("Angle bracket on the front bumper, 2 screws + 2 nuts.", [("Angle Bracket", 1), (S12, 2), (KEPS, 2)], zoom=(L / 2, 0, 22))
box("Angle Bracket", (L / 2 - 1, -40, 18), (L / 2 + 1, -26, 34), "metal", dir_=(-1, 0, 0))
box("Angle Bracket", (L / 2 - 1, 26, 18), (L / 2 + 1, 40, 34), "metal", dir_=(-1, 0, 0))
box("Angle Bracket", (L / 2, -40, 18), (L / 2 + 14, 40, 20), "metal", dir_=(-1, 0, 0))
for sy in (-1, 1):
    screw(S12, (L / 2 + 1, sy * 33, 28), (-1, 0, 0))
    nut(KEPS, (L / 2 - 5.6, sy * 33, 28), (1, 0, 0))
sub("Two tophats under the bracket, looking down, 1 screw each.", [("Tophat (Reflectance)", 2), (S14, 2), (KEPS, 2)], zoom=(L / 2 + 8, 30, 14))
for sy in (-1, 1):
    cyl("Tophat (Reflectance)", (L / 2 + 8, sy * 30, 12), 16, 10, "Z", "sensor", 20, (0, 0, 1))
    screw(S14, (L / 2 + 8, sy * 30, 20 + 2.8), (0, 0, -1))
    nut(KEPS, (L / 2 + 8, sy * 30, 18.4 - 6.35), (0, 0, 1))
sub("Rangefinder (ET) on the front bumper grid, 2 screws + 2 nuts.", [("ET (Rangefinder)", 1), (S12, 2), (KEPS, 2)], zoom=(L / 2, 54, 30))
box("ET (Rangefinder)", (L / 2, 40, 22), (L / 2 + 10, 68, 38), "sensor", dir_=(-1, 0, 0))
for dy in (44, 64):
    screw(S12, (L / 2 + 10, dy, 30), (-1, 0, 0))
    nut(KEPS, (L / 2 - 5.6, dy, 30), (1, 0, 0))
sub("Start light sensor on the deck, front left, facing up, 1 screw + 1 nut.", [("Light", 1), (S14, 1), (KEPS, 1)], zoom=(76, 58, top))
box("Light", (70, 52, top), (82, 64, top + 10), "sensor", dir_=(0, 0, -1))
screw(S14, (76, 58, top + 10), (0, 0, -1))
nut(KEPS, (76, 58, DECK_Z - 1.6), (0, 0, 1))

step("Wombat and battery")
WZ = top + 50.8                      # Wombat raised 2 in so the gate servos fit under it
POSTS = [(-15 + sx * 56.35, sy * 41.9) for sx in (-1, 1) for sy in (-1, 1)]
sub("Front 2 posts: 2 in standoffs on the deck's Wombat holes, 1 short screw each from under the deck.",
    [('Standoff 8-32 x 2"', 2), (S14, 2)], zoom=(41.35, 41.9, top + 25))
for (x, y) in POSTS[2:]:
    cyl('Standoff 8-32 x 2"', (x, y, top + 25.4), 6.4, 50.8, "Z", "metal", 6, (0, 0, -1))
    screw(S14, (x, y, DECK_Z), (0, 0, 1))
sub("Rear 2 posts: two 1 in standoffs joined by a 1 in threaded rod, 1 short screw each from under the deck.",
    [('Standoff 8-32 x 1"', 4), ('Threaded Rod 8-32 x 1"', 2), (S14, 2)], zoom=(-71.35, 41.9, top + 25))
for (x, y) in POSTS[:2]:
    cyl('Standoff 8-32 x 1"', (x, y, top + 12.7), 6.4, 25.4, "Z", "metal", 6, (0, 0, -1))
    cyl('Standoff 8-32 x 1"', (x, y, top + 38.1), 6.4, 25.4, "Z", "metal", 6, (0, 0, -1))
    screw(S14, (x, y, DECK_Z), (0, 0, 1))
sub("Wombat on the 4 posts, screen up, 4 screws from above.", [("Wombat", 1), (S14, 4)], zoom=(-15, 0, WZ + 20))
box("Wombat", (-85, -51, WZ), (55, 51, WZ + 33), "wombat", dir_=(0, 0, -1))
box("Wombat (screen)", (-70, -40, WZ + 33), (30, 40, WZ + 34), "screen", dir_=(0, 0, -1))
for (x, y) in POSTS:
    screw(S14, (x, y, WZ + 34), (0, 0, -1))
sub("Battery on the deck in front of the gates, 1 zip tie through the grid.", [("Wombat Battery", 1), (ZIP, 1)], zoom=(80, -52, top + 12))
box("Wombat Battery", (60, -70, top), (100, -34, top + 25), "battery", dir_=(0, 0, -1))
box("Zip tie", (78, -73, top), (81, -31, top + 26.5), "zip", dir_=(0, 0, -1))

step("Wiring", hint="wiring")
sub("Motors FR 0, FL 1, BR 2, BL 3. Servos: intake C 0, pin B 1, exit A 2. Analog: tophat L 0, R 1, ET 2, light 3. Digital 0: lane-full switch.",
    [], hint="wiring")
export(os.path.join(OUT, "robot_a.glb"))

# ============================================================================ ROBOT B
ROBOT["cur"] = "B"
PL0, PL1 = 22.0, 24.0
CL, CW = 234.0, 127.0
WOM = (-100.0, 40.0)

step("Chassis")
sub("KIPR chassis, flanges down.", [("Chassis", 1)])
box("Chassis", (-CL / 2, -CW / 2, PL0), (CL / 2, CW / 2, PL1), "metal", dir_=(0, 0, -1))
for sy in (-1, 1):
    box("Chassis (flange)", (-CL / 2, min(sy * CW / 2, sy * (CW / 2 - 2)), 10), (CL / 2, max(sy * CW / 2, sy * (CW / 2 - 2)), PL0), "metal", dir_=(0, 0, -1))


def drive_corner(sy, detailed):
    yf, yi = sy * 65.5, sy * 27.5
    yb = sy * 53.5
    side = "left" if sy > 0 else "right"
    if detailed:
        sub(f"Servo bracket at the rear {side}, 2 screws down + 2 nuts under the plate.", [("Servo Bracket", 1), (S14, 2), (KEPS, 2)], zoom=(-70, yb, PL1))
    box("Servo Bracket", (-97, min(yb, yb - sy * 18), PL1), (-43, max(yb, yb - sy * 18), PL1 + 2), "metal", dir_=(0, 0, -1))
    for xs in ((-97.0, -90.3), (-49.7, -43.0)):
        box("Servo Bracket", (xs[0], min(yb, yb + sy * 2), PL1), (xs[1], max(yb, yb + sy * 2), 50), "metal", dir_=(0, 0, -1))
    for x in (-90.0, -50.0):
        screw(S14, (x, sy * 44, PL1 + 2), (0, 0, -1))
        nut(KEPS, (x, sy * 44, PL0 - 1.6), (0, 0, 1))
    if detailed:
        sub("Motor into the bracket, shaft out through the side.", [("Black Gear Motor", 1)], zoom=(-70, sy * 46, 35))
    box("Black Gear Motor", (-90.3, min(yf, yi), 24.8), (-49.7, max(yf, yi), 45.1), "motor", dir_=(0, -sy, 0))
    if detailed:
        sub("4 screws through the motor ears into the bracket, 4 nuts.", [(S12, 4), (KEPS, 4)], zoom=(-70, sy * 56, 35))
    for x in (-94.0, -46.0):
        for z in (30.0, 40.0):
            screw(S12, (x, sy * 55.5, z), (0, -sy, 0))
            nut(KEPS, (x, sy * 51.9, z), (0, sy, 0))
    if detailed:
        sub("Wheel on the shaft.", [("Solarbotics Wheel", 1)], zoom=(-70, sy * 77, 35))
    cyl("Solarbotics Wheel", (-70, sy * 77, 34.9), 69.85, 13, "Y", "tyre", 32, (0, -sy, 0))
    cyl("Solarbotics Wheel (hub)", (-70, sy * 84.5, 34.9), 22, 3, "Y", "hub", 24, (0, -sy, 0))


step("Drive", hint="repeat_x2")
drive_corner(+1, True)
sub("Same on the right side.", [("Servo Bracket", 1), ("Black Gear Motor", 1), ("Solarbotics Wheel", 1), (S14, 2), (S12, 4), (KEPS, 6)], hint="repeat_x1")
drive_corner(-1, False)
sub("Caster under the front, 2 caster screws from the top.", [("Caster", 1), ('2-56 1" Caster Screw', 2)], zoom=(96, 0, PL0))
box("Caster", (83, -13, 12), (109, 13, PL0), "metal", dir_=(0, 0, 1))
cyl("Caster (ball)", (96, 0, 8), 16, 16, "Z", "hub", 24, (0, 0, 1))
for dx in (-9, 9):
    screw('2-56 1" Caster Screw', (96 + dx, 0, PL1), (0, 0, -1))

step("Wombat and battery")
wcx = (WOM[0] + WOM[1]) / 2
sub("4 standoffs (1/2 in) on the plate, screws from below.", [('Standoff 8-32 x 1/2"', 4), (S14, 4)], zoom=(wcx + 56, 42, PL1))
for sx in (-1, 1):
    for sy in (-1, 1):
        cyl('Standoff 8-32 x 1/2"', (wcx + sx * 56.35, sy * 41.9, PL1 + 6.35), 6.4, 12.7, "Z", "metal", 6, (0, 0, -1))
        screw(S14, (wcx + sx * 56.35, sy * 41.9, PL0), (0, 0, 1))
wz0 = PL1 + 12.7
sub("Wombat on the standoffs, screen up, 4 screws from above.", [("Wombat", 1), (S12, 4)], zoom=(wcx, 0, wz0 + 30))
box("Wombat", (WOM[0], -51, wz0), (WOM[1], 51, wz0 + 33), "wombat", dir_=(0, 0, -1))
box("Wombat (screen)", (WOM[0] + 50, -40, wz0 + 33), (WOM[1] - 10, 40, wz0 + 34), "screen", dir_=(0, 0, -1))
for sx in (-1, 1):
    for sy in (-1, 1):
        screw(S12, (wcx + sx * 56.35, sy * 41.9, wz0 + 34), (0, 0, -1))
sub("Battery on the rear of the Wombat, 1 zip tie around both.", [("Wombat Battery", 1), (ZIP, 1)], zoom=(WOM[0] + 18, 0, wz0 + 45))
box("Wombat Battery", (WOM[0], -40, wz0 + 33), (WOM[0] + 36, 41, wz0 + 58), "battery", dir_=(0, 0, -1))
box("Zip tie", (WOM[0] + 16, -53, wz0 - 1), (WOM[0] + 19, 53, wz0 + 59.5), "zip", dir_=(0, 0, -1))

step("Arm")
sub("Shoulder: servo bracket at the front left, 2 screws + 2 nuts.", [("Servo Bracket", 1), (S14, 2), (KEPS, 2)], zoom=(72, 32, PL1))
box("Servo Bracket", (50, 20, PL1), (94, 22, 62), "metal", dir_=(0, 0, -1))
box("Servo Bracket", (50, 20, PL1), (94, 44, PL1 + 2), "metal", dir_=(0, 0, -1))
for x in (58.0, 86.0):
    screw(S14, (x, 33, PL1 + 2), (0, 0, -1))
    nut(KEPS, (x, 33, PL0 - 1.6), (0, 0, 1))
sub("Servo into the bracket, shaft to the left (outside). 2 screws + 2 nuts through the ears.", [("Servo", 1), (S12, 2), (KEPS, 2)], zoom=(72, 32, 45))
box("Servo", (52, 22, PL1 + 2), (92.6, 42.3, PL1 + 38), "servo", dir_=(0, 0, -1), shaft=((0, 1, 0), (82, 0, 50)))
for x in (54.0, 90.6):
    screw(S12, (x, 22, 50), (0, 1, 0))
    nut(KEPS, (x, 18.4, 50), (0, -1, 0))
sub("Round servo horn on the shaft, 1 horn screw.", [("Round Servo Horn", 1), (HORNS, 1)], zoom=(82, 44, 50))
cyl("Round Servo Horn", (82, 43.6, 50), 24, 2.6, "Y", "metal", 24, (0, -1, 0))
screw(HORNS, (82, 45, 50), (0, -1, 0))
ang = math.radians(25)
sub("Upper 1x11 liftarm on the horn: 2 M3 screws + 2 M3 nuts.", [("1 x 11 Liftarm", 1), (M3S, 2), (M3N, 2)], zoom=(90, 49, 54))
tfu = Matrix.Translation((82, 49, 50)) @ Matrix.Rotation(-ang, 4, "Y") @ Matrix.Translation((40, 0, 0))
box("1 x 11 Liftarm", (-44, -4, -4), (44, 4, 4), "lego", tfu, dir_=(0, -1, 0))
for k in (0, 1):
    p = tfu @ Vector((-40 + 8 * k, 4, 0))
    screw(M3S, tuple(p), (0, -1, 0))
    nut(M3N, tuple(tfu @ Vector((-40 + 8 * k, -6.8, 0))), (0, 1, 0))
sub("1x3 liftarm bolted upright on the bracket (2 screws + 2 nuts), lower 1x11 liftarm on its top hole with a friction pin.",
    [("1 x 3 Liftarm", 1), ("1 x 11 Liftarm", 1), ("Pin w/ Friction", 1), (S12, 2), (KEPS, 2)], zoom=(82, 57, 34))
box("1 x 3 Liftarm", (78, 53, 26), (86, 61, 50), "lego", dir_=(0, -1, 0))
for z in (30.0, 38.0):
    screw(S12, (82, 61, z), (0, -1, 0))
    nut(KEPS, (82, 18.4, z), (0, 1, 0))
tfl = Matrix.Translation((82, 57, 34)) @ Matrix.Rotation(-ang, 4, "Y") @ Matrix.Translation((40, 0, 0))
box("1 x 11 Liftarm", (-44, -4, -4), (44, 4, 4), "lego", tfl, dir_=(0, -1, 0))
cyl("Pin w/ Friction", (82, 57, 34), 4.8, 16, "Y", "motor", 12, (0, -1, 0))
tip_x, tip_z = 82 + 80 * math.cos(ang), 50 + 80 * math.sin(ang)
sub("1x5 liftarm joins both arm tips, 2 friction pins. The claw will stay level.", [("1 x 5 Liftarm", 1), ("Pin w/ Friction", 2)], zoom=(tip_x, 57, tip_z - 8))
box("1 x 5 Liftarm", (tip_x - 4, 61, tip_z - 24), (tip_x + 4, 69, tip_z + 12), "lego", dir_=(0, -1, 0))
for z in (tip_z, tip_z - 16):
    cyl("Pin w/ Friction", (tip_x, 61, z), 4.8, 16, "Y", "motor", 12, (0, -1, 0))



def split_claw(o):
    """Split print 2 into base / finger L / finger R so the manual can show and animate them."""
    old = o.name
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    bodies = list(bpy.context.selected_objects)
    assert len(bodies) == 3, f"claw has {len(bodies)} bodies, expected 3"
    zmin = {b.name: min(v.co.z for v in b.data.vertices) for b in bodies}
    base = min(bodies, key=lambda b: zmin[b.name])
    fingers = sorted((b for b in bodies if b is not base),
                     key=lambda b: sum(v.co.y for v in b.data.vertices) / len(b.data.vertices))
    items = CUR["items"]
    dir_ = next(i["dir"] for i in items if i["mesh"] == old)
    items[:] = [i for i in items if i["mesh"] != old]
    for b, nm, mk in ((base, "Geared claw (print 2)", "pla"), (fingers[1], "Geared claw (print 2) (finger L)", "claw_finger"),
                      (fingers[0], "Geared claw (print 2) (finger R)", "claw_finger")):
        put(b, nm, M(mk), dir_)
    tf = LAST_STL["tf"]
    zc = 4.0 + 0.4 + 4.0                                       # p2: BASE_T + CLR + HUB_T / 2
    piv = [tf @ Vector((x, 0.0, zc)) for x in (-12.6, 12.6)]    # p2: xL, xR = -/+ CENTRE / 2
    left, right = sorted(piv, key=lambda p: -p.y)
    return {"meshes": {"base": base.name, "finger_L": fingers[1].name, "finger_R": fingers[0].name},
            "pivots": {"finger_L": [round(v, 2) for v in left], "finger_R": [round(v, 2) for v in right]},
            "axis": [0, 0, 1], "open_deg": 25, "driven": "finger_R (servo) turns finger_L through the gears, opposite way"}


step("Geared claw")
cb_z = tip_z - 24
sub("Claw (print 2): servo bracket under its base, 4 short screws + 4 nuts through the 4.4 mm grid.",
    [("Geared claw (print 2)", 1), ("Servo Bracket", 1), (S14, 4), (KEPS, 4)], subassembly="Claw", zoom=(tip_x + 66, 57, cb_z))
claw = stl("Geared claw (print 2)", "p2_geared_claw.stl", "pla", rot_z=-90, x=tip_x + 4, y=57, z=cb_z, dir_=(0, 0, -1))
CLAW = split_claw(claw)
px, py = CLAW["pivots"]["finger_R"][:2]              # the servo shaft sits right under the right finger's hub
box("Servo Bracket", (px - 31, py - 19, cb_z - 2), (px + 13, py + 19, cb_z), "metal", dir_=(0, 0, 1))
for dx in (-25.0, 7.0):
    for dy in (-15.0, 15.0):
        screw(S14, (px + dx, py + dy, cb_z + 4), (0, 0, -1))
        nut(KEPS, (px + dx, py + dy, cb_z - 3.6), (0, 0, 1))
sub("Claw servo into the bracket, shaft UP under the right finger. 2 screws + 2 nuts.", [("Servo", 1), (S12, 2), (KEPS, 2)], subassembly="Claw",
    zoom=(px - 9, py, cb_z - 20))
box("Servo", (px - 29.2, py - 10.15, cb_z - 38), (px + 11.4, py + 10.15, cb_z - 2), "servo", dir_=(0, 0, 1),
    shaft=((0, 0, 1), (px, py, 0)))
for dx in (-27.2, 9.4):
    screw(S12, (px + dx, py + 10.15, cb_z - 12), (0, -1, 0))
    nut(KEPS, (px + dx, py - 11.75, cb_z - 12), (0, 1, 0))
sub("Round servo horn in the pocket under the right finger: 1 horn screw, then 3 M3 screws + 3 M3 nuts (nuts go in the hex holes on top).",
    [("Round Servo Horn", 1), (HORNS, 1), (M3S, 3), (M3N, 3)], subassembly="Claw", zoom=(px, py, cb_z + 8))
cyl("Round Servo Horn", (px, py, cb_z + 6.15), 24, 3.5, "Z", "metal", 24, (0, 0, 1))
screw(HORNS, (px, py, cb_z + 7.9), (0, 0, -1))
for adeg in (-90, 0, 180):                          # p2 HORN_SCREW_ANGLES (0, 90, 270) turned -90 deg with the print
    a = math.radians(adeg)
    p = (px + 7 * math.cos(a), py + 7 * math.sin(a))
    screw(M3S, (p[0], p[1], cb_z + 4.4), (0, 0, 1))
    nut(M3N, (p[0], p[1], cb_z + 11.2), (0, 0, -1))
sub("Bolt the claw to the 1x5 liftarm at the arm tip: 2 screws + 2 nuts through the rear holes.", [(S12, 2), (KEPS, 2)], zoom=(tip_x + 6, 61, cb_z + 2))
for dx in (8.0, 16.0):
    screw(S12, (tip_x + dx + 4, 57, cb_z + 6), (0, 0, -1))
    nut(KEPS, (tip_x + dx + 4, 57, cb_z - 5.2), (0, 0, 1))

step("Pocket plow")
face_x = CL / 2 + 8
sub("Plow (print 3): slide its 2 tabs under the front of the chassis.", [("Pocket plow (print 3)", 1)], zoom=(face_x - 15, 0, PL0))
stl("Pocket plow (print 3)", "p3_pocket_plow.stl", "pla", x=face_x - 28, y=0, z=3, dir_=(-1, 0, 0))
sub("4 screws down through plate and tabs, 4 Keps nuts under the tabs.", [(S12, 4), (KEPS, 4)], zoom=(face_x - 16, 18, PL1))
for xo in (-22.0, -22.0 + 12.7):
    for sy in (-1, 1):
        screw(S12, (face_x + xo, sy * 18, PL1), (0, 0, -1))
        nut(KEPS, (face_x + xo, sy * 18, 16 - 1.6), (0, 0, 1))
sub("Lever switch in the centre pocket, 2 brass screws.", [("Lever", 1), ("Brass Screws", 2)], zoom=(CL / 2 + 4, 0, 27))
box("Lever", (CL / 2, -10, 21), (face_x, 10, 33), "sensor", dir_=(1, 0, 0))
for dy in (-7, 7):
    screw("Brass Screws", (face_x + 4, dy, 27), (-1, 0, 0))

step("Cup hook")
sub("Servo bracket on the right flange, 2 screws + 2 nuts.", [("Servo Bracket", 1), (S12, 2), (KEPS, 2)], zoom=(30, -62, 18))
box("Servo Bracket", (8, -63.7, 10), (52, -61.7, PL1 + 38), "metal", dir_=(0, 1, 0))
for x in (14.0, 46.0):
    screw(S12, (x, -63.7, 16), (0, 1, 0))
    nut(KEPS, (x, -57.9, 16), (0, -1, 0))
sub("Hook servo into the bracket, shaft to the RIGHT (outside). 2 screws + 2 nuts.", [("Servo", 1), (S12, 2), (KEPS, 2)], zoom=(30, -74, 42))
box("Servo", (10, -84.0, PL1), (50.6, -63.7, PL1 + 36), "servo", dir_=(0, 1, 0), shaft=((0, -1, 0), (40, 0, 50.8)))
for x in (12.0, 48.6):
    screw(S12, (x, -84.0, 50), (0, 1, 0))
    nut(KEPS, (x, -60.1, 50), (0, -1, 0))
sub("1x5 servo horn on the shaft, pointing forward, 1 horn screw.", [("1 x 5 Servo Horn", 1), (HORNS, 1)], zoom=(40, -86, 50))
box("1 x 5 Servo Horn", (40 - 33, -86.6, 46), (40 + 33, -84, 55.5), "metal", dir_=(0, 1, 0))
screw(HORNS, (40, -86.6, 50.8), (0, 1, 0))
sub("Hook (print 4) on the horn, lip pointing IN: 2 M3 screws + 2 M3 nuts (nuts in the hex holes outside).",
    [("Cup hook (print 4)", 1), (M3S, 2), (M3N, 2)], zoom=(40, -92, 50))
stl("Cup hook (print 4)", "p4_cup_hook.stl", "pla", x=40 - 17, y=-86.6, z=50.8 + 17, ref=("min", "max", "max"), dir_=(0, 1, 0))
for dx in (-12.7, 12.7):
    screw(M3S, (40 + dx, -86.6, 50.8), (0, -1, 0))
    nut(M3N, (40 + dx, -95.0, 50.8), (0, 1, 0))

step("Camera mast")
sub("Channel 3x8 upright at the rear-left corner, 2 screws + 2 nuts.", [("Channel 3 x 8", 1), (S12, 2), (KEPS, 2)], zoom=(-110, 41, PL1 + 15))
box("Channel 3 x 8", (-117, 22, PL1), (-104, 60, PL1 + 102), "metal", dir_=(0, 0, -1))
for z in (PL1 + 10, PL1 + 22):
    screw(S12, (-104, 41, z), (-1, 0, 0))
    nut(KEPS, (-118.6, 41, z), (1, 0, 0))
sub("Camera clipped on top, tilted 35 degrees down toward the front, 1 zip tie.", [("Black Camera", 1), (ZIP, 1)], zoom=(-104, 41, PL1 + 112))
cam_tf = Matrix.Translation((-104, 41, PL1 + 116)) @ Matrix.Rotation(math.radians(35), 4, "Y")
box("Black Camera", (-12, -36, -15), (13, 36, 16), "motor", cam_tf, dir_=(0, 0, -1))
box("Zip tie", (-118, 20, PL1 + 96), (-103, 62, PL1 + 98), "zip", dir_=(0, 0, -1))

step("Sensors")
sub("Angle bracket under the front of the plate, 2 screws + 2 nuts.", [("Angle Bracket", 1), (S14, 2), (KEPS, 2)], zoom=(103, 0, PL0))
box("Angle Bracket", (96, -32, PL0 - 2), (110, 32, PL0), "metal", dir_=(0, 0, 1))
for sy in (-1, 1):
    screw(S14, (103, sy * 28, PL1), (0, 0, -1))
    nut(KEPS, (103, sy * 28, PL0 - 3.6), (0, 0, 1))
sub("Two tophats on the bracket, looking down, 1 screw + 1 nut each.", [("Tophat (Reflectance)", 2), (S14, 2), (KEPS, 2)], zoom=(103, 18, 13))
for sy in (-1, 1):
    cyl("Tophat (Reflectance)", (103, sy * 18, 13), 16, 14, "Z", "sensor", 20, (0, 0, 1))
    screw(S14, (103, sy * 18, PL0 - 2), (0, 0, 1))
    nut(KEPS, (103, sy * 18, PL1 + 1.6), (0, 0, -1))
sub("Rangefinder (ET) on the plate, front right, 1 screw + 1 nut.", [("ET (Rangefinder)", 1), (S14, 1), (KEPS, 1)], zoom=(105, -46, PL1))
box("ET (Rangefinder)", (100, -60, PL1), (110, -32, PL1 + 16), "sensor", dir_=(0, 0, -1))
screw(S14, (105, -46, PL1 + 16), (0, 0, -1))
nut(KEPS, (105, -46, PL0 - 1.6), (0, 0, 1))
sub("Start light sensor on the plate, 1 screw + 1 nut.", [("Light", 1), (S14, 1), (KEPS, 1)], zoom=(46, -54, PL1))
box("Light", (40, -60, PL1), (52, -48, PL1 + 10), "sensor", dir_=(0, 0, -1))
screw(S14, (46, -54, PL1 + 10), (0, 0, -1))
nut(KEPS, (46, -54, PL0 - 1.6), (0, 0, 1))

step("Wiring", hint="wiring")
sub("Motors: left 0, right 2. Servos: shoulder 1, claw 2, hook 3. Analog: tophat L 0, R 1, ET 2, light 3. Digital 0: plow lever. Camera on USB.",
    [], hint="wiring")
export(os.path.join(OUT, "robot_b.glb"))

# ============================================================================ part cards
CARDS = {
    "Printed chassis (print 1)": "Our 3D print 1: Robot A's frame. The duck channel runs down the middle; 4 motor windows; 4.4 mm holes everywhere.",
    "Geared claw (print 2)": "Our 3D print 2: the claw. Grey base + 2 fingers with gear teeth (shown orange). The servo turns the right finger; the gears turn the left one the other way, so the claw opens and closes.",
    "Pocket plow (print 3)": "Our 3D print 3: a wide scoop on Robot B's nose. Pushes pom stacks and the pickleball.",
    "Cup hook (print 4)": "Our 3D print 4: long arm with a hook lip at the tip. Catches the cup rim.",
    "Black Gear Motor": "Black KIPR drive motor: rectangular gearbox + round motor can, shaft on the side, 2 wires.",
    "Mecanum Wheel": "Wheel with angled rollers. Rollers must form an X when seen from above.",
    "Solarbotics Wheel": "Round black rubber wheel, pushes onto the motor shaft.",
    "Servo": "Standard servo: black box with 2 ears (screw holes) and a spline shaft on top. 3 wires.",
    "Micro Servo": "Small servo, same shape as the standard servo but half size.",
    "Round Servo Horn": "Disc with a ring of small holes. Pushes onto a servo shaft.",
    "1 x 5 Servo Horn": "Flat bar with 5 holes. The middle hole goes on the servo shaft.",
    "1 x 3 Liftarm": "LEGO beam with 3 round holes.",
    "1 x 5 Liftarm": "LEGO beam with 5 round holes.",
    "1 x 7 Liftarm": "LEGO beam with 7 round holes.",
    "1 x 11 Liftarm": "LEGO beam with 11 round holes.",
    "Pin w/ Friction": "Black LEGO pin with a ridge in the middle. Push it through 2 beams.",
    "Servo Bracket": "Bent metal plate that holds a servo by its ears.",
    "Micro Servo Mount": "Small metal plate that holds the micro servo.",
    "Angle Bracket": "Metal L-shaped bracket (90 degree corner).",
    "Plate 4 x 12": "Flat metal plate, 4 holes by 12 holes.",
    "Strap 1 x 10": "Flat metal strip with 10 holes in a row.",
    "Channel 3 x 8": "U-shaped metal channel, 3 holes wide, 8 holes long.",
    "Chassis": "Big flat KIPR metal plate with folded edges: Robot B's base.",
    "Caster": "Small ball caster: square plate with a free-rolling ball underneath.",
    "Wombat": "KIPR Wombat controller: black box with a touch screen; ports on the sides.",
    "Wombat Battery": "Battery pack with red + black wires and a plug.",
    "Small Touch": "Small push-button switch (red button).",
    "Lever": "Switch with a long metal lever and a roller at its tip.",
    "Tophat (Reflectance)": "Small round blue sensor that looks down at the floor tape.",
    "ET (Rangefinder)": "Blue distance sensor with 2 round eyes.",
    "Light": "Small light sensor with a round yellow cell on top.",
    "Black Camera": "USB camera: black box with a round lens.",
    'Standoff 8-32 x 1/2"': "Silver hex post, 1/2 inch long, threaded inside at both ends.",
    'Standoff 8-32 x 1"': "Silver hex post, 1 inch long.",
    'Standoff 8-32 x 2"': "Silver hex post, 2 inches long.",
    'Threaded Rod 8-32 x 1"': "Short threaded rod: joins two standoffs end to end.",
    S14: "Black screw, 1/4 inch (6 mm) long.",
    S12: "Black screw, 1/2 inch (13 mm) long.",
    S34: "Black screw, 3/4 inch (19 mm) long.",
    KEPS: "Black nut with a toothed washer on one side (teeth face the part).",
    M3S: "Small silver M3 screw (for servo horns).",
    M3N: "Small silver M3 nut.",
    HORNS: "Short silver screw: holds a horn on the servo shaft.",
    "Brass Screws": "Tiny brass screws for switches.",
    '2-56 3/8" Micro Servo Mount Screw': "Tiny silver screw for the micro servo mount.",
    '2-56 1" Caster Screw': "Long thin silver screw for the caster.",
    'M3 x 0.5" x 6" Mecanum Wheel Screw': "Screw that holds a mecanum wheel on its shaft.",
    ZIP: "White zip tie. Pull tight, cut the tail.",
}
missing = sorted(n for r_ in "AB" for st in STEPS[r_] for u in st["subs"] for pp in u["parts"] if pp["name"] not in CARDS)
assert not missing, f"no card for {set(missing)}"

# ============================================================================ BOM check
use = {r: Counter() for r in "AB"}
for r in "AB":
    for s in STEPS[r]:
        for u in s["subs"]:
            for p in u["parts"]:
                use[r][p["name"]] += p["qty"]
total = use["A"] + use["B"]
problems = []
for name, qty in sorted(total.items()):
    if name in PRINTS:
        continue
    if name not in KIT["parts"]:
        problems.append(f"'{name}' is not in the 2026 kit list")
    elif qty > KIT["parts"][name]:
        problems.append(f"'{name}': {qty} used > {KIT['parts'][name]} in the kit")
printed = sum(q for n, q in total.items() if n in PRINTS)
if printed > KIT["printed_limit"]:
    problems.append(f"{printed} printed parts > {KIT['printed_limit']}")
lines = ["# Bill of materials vs the 2026 kit (generated by tools/blender/export_build_manual.py)", "",
         "| Part | Robot A | Robot B | Total | In kit | OK |", "|---|---:|---:|---:|---:|---|"]
for name in sorted(total, key=lambda n: (n not in PRINTS, n)):
    kit = "print" if name in PRINTS else KIT["parts"].get(name, "NOT IN KIT")
    ok = name in PRINTS or (isinstance(kit, int) and total[name] <= kit)
    lines.append(f"| {name} | {use['A'][name]} | {use['B'][name]} | {total[name]} | {kit} | {'yes' if ok else 'NO'} |")
lines += ["", f"Printed parts: {printed}/{KIT['printed_limit']}", "", "Problems: " + ("none" if not problems else "")]
lines += [f"- {p}" for p in problems]
open(os.path.join(OUT, "bom.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
nsub = {r: sum(len(s["subs"]) for s in STEPS[r]) for r in "AB"}
with open(os.path.join(OUT, "steps.json"), "w", encoding="utf-8") as f:
    json.dump({"version": 2, "units": "mm; +X forward, +Y left, +Z up from the floor",
               "mesh_naming": "'<SS>.<ss>|<part name>' = step . sub-step; '(...)' suffix = a sub-mesh of the same part",
               "items_dir": "insertion direction of each mesh (robot frame): the fly-in comes from -dir and travels along dir",
               "hints": {"mecanum_x": "top-view pictogram: rollers form an X", "gate_open_closed": "pictogram: flap DOWN = closed, flap UP (90 deg) = open",
                         "repeat_x3": "do the shown corner 3 more times", "repeat_x4": "x4", "repeat_x2": "x2", "repeat_x1": "mirror on the other side",
                         "bend_35": "bend the strap 35 degrees outward", "print_check": "check the print", "wiring": "port map card"},
               "robot_a": {"name": "Robot A - Duck Runner", "glb": "robot_a.glb", "steps": STEPS["A"], "substeps": nsub["A"]},
               "robot_b": {"name": "Robot B - Point Scorer", "glb": "robot_b.glb", "steps": STEPS["B"], "substeps": nsub["B"]},
               "claw": CLAW, "cards": CARDS,
               "bom": {r: dict(use[r]) for r in "AB"}}, f, indent=1)
print("\n".join(lines))
print("SUBSTEPS", nsub)
if problems:
    raise SystemExit("BOM problems: " + "; ".join(problems))

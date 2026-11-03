"""Shared helpers for generating printable Botball parts with the Blender CLI.

Units: 1 Blender unit = 1 mm. STL files are written in mm (what slicers expect).

Usage from a part script (run headless):
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/parts/<part>.py -- --out parts/out

Each part script should:
    sys.path.insert(0, <tools/blender>); import partlib as pl
    pl.reset()
    body = pl.box(...); pl.difference(body, pl.cyl(...))
    pl.finish(body, "part_name", out_dir, print_class="mid")

pl.finish() exports <name>.stl, renders <name>.png, and writes <name>.json with the
bounding box and the KIPR 3D-print class check (see check_print_class()).
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

MM_PER_IN = 25.4

# KIPR 2026 Fall Game 3D-print classes (Rule Summary p.12). Count = how many parts
# of that class a team may use. Dims in mm.
PRINT_CLASSES = {
    "small": {"count": 6, "dims_mm": (60.0, 60.0, 20.0)},
    "mid": {"count": 2, "dims_mm": (220.0, 220.0, 80.0)},
    "large": {"count": 1, "dims_mm": (220.0, 220.0, 250.0)},
    # Team rule (2026-11-03): 4 printed parts in total, any size up to the printer bed;
    # a moving assembly printed in one go counts as one part.
    "team": {"count": 4, "dims_mm": (220.0, 220.0, 250.0)},
}
# A single part may never exceed the Ender 3 V3 SE build volume.
PRINTER_MAX_MM = (220.0, 220.0, 250.0)

# Common Botball interface dimensions (mm). Verify against real parts before printing.
LEGO_PITCH = 8.0           # Technic hole spacing
LEGO_HOLE_D = 4.9          # Technic pin hole (4.8 nominal + print clearance)
LEGO_AXLE_CROSS = 4.9      # Technic axle cross width incl. clearance
M3_CLEAR_D = 3.4           # clearance hole for KIPR metal-part screws (assumed M3/4-40 class)
SERVO_HORN_SCREW_D = 2.2   # small self-tapping screw into a printed boss


def script_args():
    """Arguments after the `--` separator on the Blender command line."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def out_dir_from_args(default="parts/out"):
    args = script_args()
    if "--out" in args and args.index("--out") + 1 < len(args):
        out = os.path.abspath(args[args.index("--out") + 1])
    else:
        out = os.path.abspath(default)
    os.makedirs(out, exist_ok=True)
    return out


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"


# ---------------------------------------------------------------- primitives

def _link(bm, name):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _axis_matrix(axis):
    if axis == "X":
        return Matrix.Rotation(math.radians(90), 4, "Y")
    if axis == "Y":
        return Matrix.Rotation(math.radians(90), 4, "X")
    return Matrix.Identity(4)


def box(sx, sy, sz, center=(0, 0, 0), name="box"):
    """Axis-aligned box of size sx*sy*sz mm centred at `center`."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _link(bm, name)


def box_from(min_xyz, max_xyz, name="box"):
    """Box spanning two corners (mm)."""
    size = [b - a for a, b in zip(min_xyz, max_xyz)]
    center = [(a + b) / 2 for a, b in zip(min_xyz, max_xyz)]
    return box(*size, center=center, name=name)


def cyl(d, h, center=(0, 0, 0), axis="Z", segments=64, name="cyl", d2=None):
    """Cylinder (or cone frustum if d2 given) of diameter d, height h along `axis`."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=segments,
        radius1=d / 2, radius2=(d2 if d2 is not None else d) / 2, depth=h,
    )
    bmesh.ops.transform(bm, matrix=_axis_matrix(axis), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return _link(bm, name)


def tube(od, id_, h, center=(0, 0, 0), axis="Z", segments=96, name="tube"):
    outer = cyl(od, h, center, axis, segments, name)
    inner = cyl(id_, h + 2, center, axis, segments, name + "_cut")
    return difference(outer, inner)


def rounded_plate(sx, sy, t, r, center=(0, 0, 0), segments=24, name="plate"):
    """Flat plate with rounded corners (radius r) in the XY plane, thickness t."""
    r = min(r, sx / 2 - 0.01, sy / 2 - 0.01)
    core = box(sx - 2 * r, sy, t, center, name)
    union(core, box(sx, sy - 2 * r, t, center, name + "_b"))
    cx, cy, cz = center
    for dx in (-1, 1):
        for dy in (-1, 1):
            union(core, cyl(2 * r, t, (cx + dx * (sx / 2 - r), cy + dy * (sy / 2 - r), cz),
                            segments=segments, name=name + "_c"))
    return core


def wedge(length, width, h0, h1, center=(0, 0, 0), name="wedge"):
    """Ramp along +X: height h0 at -X end, h1 at +X end, width along Y. Base at z=center.z."""
    cx, cy, cz = center
    x0, x1 = cx - length / 2, cx + length / 2
    y0, y1 = cy - width / 2, cy + width / 2
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in (
        (x0, y0, cz), (x1, y0, cz), (x1, y1, cz), (x0, y1, cz),
        (x0, y0, cz + h0), (x1, y0, cz + h1), (x1, y1, cz + h1), (x0, y1, cz + h0))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _link(bm, name)


def prism(points_xy, z0, z1, name="prism"):
    """Vertical prism from a convex XY polygon (counter-clockwise), between z0 and z1."""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in points_xy]
    hi = [bm.verts.new((x, y, z1)) for x, y in points_xy]
    n = len(points_xy)
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _link(bm, name)


def hole_grid(obj, centers, d, depth, axis="Z", segments=24):
    """Cut many holes in ONE boolean (fast). centers = [(x, y, z), ...]; holes run along `axis`."""
    if not centers:
        return obj
    bm = bmesh.new()
    rot = _axis_matrix(axis)
    for c in centers:
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                              radius1=d / 2, radius2=d / 2, depth=depth,
                              matrix=Matrix.Translation(Vector(c)) @ rot)
    return difference(obj, _link(bm, "hole_grid"))


def hole_row(obj, n, pitch, d, start, axis="Z", depth=30, direction=(1, 0, 0)):
    """Cut n holes of diameter d, `pitch` apart along `direction`, starting at `start`."""
    sx, sy, sz = start
    dx, dy, dz = direction
    for i in range(n):
        c = (sx + dx * pitch * i, sy + dy * pitch * i, sz + dz * pitch * i)
        difference(obj, cyl(d, depth, c, axis, 32, "hole"))
    return obj


def lego_axle_hole(obj, center, axis="Z", depth=200):
    """Cut a Technic cross-axle hole."""
    w, t = LEGO_AXLE_CROSS, 1.9
    cx, cy, cz = center
    if axis == "Z":
        a = box(w, t, depth, center)
        b = box(t, w, depth, center)
    elif axis == "X":
        a = box(depth, w, t, center)
        b = box(depth, t, w, center)
    else:
        a = box(w, depth, t, center)
        b = box(t, depth, w, center)
    difference(obj, a)
    difference(obj, b)
    return obj


# ------------------------------------------------------------------ booleans

def _bbox_overlap(a, b):
    (alo, ahi), (blo, bhi) = bbox_mm(a), bbox_mm(b)
    return all(alo[i] < bhi[i] and blo[i] < ahi[i] for i in range(3))


def _apply_boolean(target, other, op):
    """Apply a boolean and RAISE if it silently did nothing.

    Blender's MANIFOLD solver does not raise on non-manifold input - it logs and
    returns the mesh unchanged - so the solver is chosen up front and the result
    is checked.
    """
    manifold = is_manifold(target)[0] and is_manifold(other)[0]
    overlaps = _bbox_overlap(target, other)
    obox = bbox_mm(other) if overlaps else None
    before = (len(target.data.vertices), len(target.data.polygons))
    mod = target.modifiers.new(name="bool", type="BOOLEAN")
    mod.operation = op
    mod.object = other
    mod.solver = "MANIFOLD" if manifold else "EXACT"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    after = (len(target.data.vertices), len(target.data.polygons))
    other_mesh = other.data
    bpy.data.objects.remove(other, do_unlink=True)
    if other_mesh.users == 0:
        bpy.data.meshes.remove(other_mesh)
    if overlaps and before == after:
        raise RuntimeError(f"boolean {op} on {target.name!r} was a no-op (solver {mod.solver}); "
                           f"operand bbox {[tuple(round(v, 1) for v in c) for c in obox]}")
    return target


def union(target, *others):
    for o in others:
        _apply_boolean(target, o, "UNION")
    return target


def difference(target, *cutters):
    for c in cutters:
        _apply_boolean(target, c, "DIFFERENCE")
    return target


def intersect(target, other):
    return _apply_boolean(target, other, "INTERSECT")


def move(obj, dx=0, dy=0, dz=0):
    obj.data.transform(Matrix.Translation((dx, dy, dz)))
    return obj


def rotate(obj, deg, axis="Z", pivot=(0, 0, 0)):
    p = Matrix.Translation(Vector(pivot))
    obj.data.transform(p @ Matrix.Rotation(math.radians(deg), 4, axis) @ p.inverted())
    return obj


def mirror_copy(obj, axis="X", name=None):
    """Return a mirrored duplicate (not joined)."""
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = name or obj.name + "_mirror"
    bpy.context.scene.collection.objects.link(dup)
    s = {"X": (-1, 1, 1), "Y": (1, -1, 1), "Z": (1, 1, -1)}[axis]
    dup.data.transform(Matrix.Diagonal((*s, 1)))
    dup.data.flip_normals()
    return dup


# -------------------------------------------------------------- inspection

def bbox_mm(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def dims_mm(obj, ndigits=2):
    """Bounding-box size. ndigits=None returns unrounded values (use for checks)."""
    lo, hi = bbox_mm(obj)
    size = tuple(h - l for l, h in zip(lo, hi))
    return size if ndigits is None else tuple(round(d, ndigits) for d in size)


def island_count(obj):
    """Number of disconnected pieces (a severed cut or a face-only union shows as > 1)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        islands += 1
        stack = [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                nxt = e.other_vert(cur)
                if nxt.index not in seen:
                    seen.add(nxt.index)
                    stack.append(nxt)
    bm.free()
    return islands


def is_manifold(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return bad_edges == 0, bad_edges


def volume_cm3(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return round(vol / 1000.0, 2)   # negative = inverted normals


TOL_MM = 0.01   # parts must be at least this far inside a limit


def check_print_class(dims, cls):
    """KIPR rule (p.12): each bbox dimension is rounded UP to a whole inch.

    Pass UNROUNDED dims. Three readings are reported because the rule text is
    ambiguous:
      * strict      - the part fits the class box in millimetres as written
                      (small 60x60x20, mid 220x220x80, large 220x220x250) AS
                      EXPORTED: Z is the height, only an X/Y swap is allowed.
                      Passes under every reading -> design to this.
      * inch_box    - the part's whole-inch box fits the class's whole-inch box
                      in any orientation (reading used in docs/rules-digest.md).
      * lenient     - rounded part volume <= rounded class volume.
    margin_mm = class minus part per axis (best X/Y assignment); < 1 mm is flagged.
    """
    cls_dims = PRINT_CLASSES[cls]["dims_mm"]
    part_in = [math.ceil(d / MM_PER_IN) for d in dims]
    cls_in = [math.ceil(d / MM_PER_IN) for d in cls_dims]
    part_vol_in3 = math.prod(part_in)
    cls_round_in3 = math.prod(cls_in)
    fits_printer = all(p <= c - TOL_MM for p, c in zip(sorted(dims), sorted(PRINTER_MAX_MM)))
    best_margin = None
    for xy in ((dims[0], dims[1]), (dims[1], dims[0])):
        m = [cls_dims[0] - xy[0], cls_dims[1] - xy[1], cls_dims[2] - dims[2]]
        if best_margin is None or min(m) > min(best_margin):
            best_margin = m
    fits_mm = min(best_margin) >= TOL_MM
    fits_in = all(p <= c for p, c in zip(sorted(part_in), sorted(cls_in)))
    return {
        "class": cls,
        "part_dims_mm": [round(d, 3) for d in dims],
        "part_dims_rounded_in": part_in,
        "part_volume_rounded_in3": part_vol_in3,
        "class_dims_mm": list(cls_dims),
        "class_dims_rounded_in": cls_in,
        "margin_mm": [round(m, 2) for m in best_margin],
        "low_margin": min(best_margin) < 1.0,
        "fits_printer": fits_printer,
        "pass_strict": fits_printer and fits_mm,
        "pass_inch_box": fits_printer and fits_in,
        "pass_lenient": fits_printer and part_vol_in3 <= cls_round_in3,
    }


def _overlap_volume(a, b):
    """Volume (mm^3) shared by two bodies, via an EXACT boolean on throwaway copies."""
    ca, cb = a.copy(), b.copy()
    ca.data, cb.data = a.data.copy(), b.data.copy()
    for c in (ca, cb):
        bpy.context.scene.collection.objects.link(c)
    try:
        mod = ca.modifiers.new(name="isect", type="BOOLEAN")
        mod.operation, mod.object, mod.solver = "INTERSECT", cb, "EXACT"
        bpy.context.view_layer.objects.active = ca
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bm = bmesh.new()
        bm.from_mesh(ca.data)
        vol = abs(bm.calc_volume()) if bm.faces else 0.0
        bm.free()
        return vol
    finally:
        for c in (ca, cb):
            m = c.data
            bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.meshes.remove(m)


def _surface_points(obj, step=0.25, max_per_edge=400):
    """Every vertex plus points every `step` mm along every edge (world space).

    Vertex-only sampling misses edge-to-edge and face-to-edge contacts; edges don't.
    """
    mw = obj.matrix_world
    vs = [mw @ v.co for v in obj.data.vertices]
    yield from vs
    for e in obj.data.edges:
        p, q = vs[e.vertices[0]], vs[e.vertices[1]]
        n = min(int((q - p).length / step), max_per_edge)
        for k in range(1, n):
            yield p.lerp(q, k / n)


def min_gaps(objs):
    """Smallest distance (mm) between each pair of separate bodies; 0.0 if they overlap.

    For print-in-place parts: anything under the print clearance fuses on the bed.
    Overlap is measured with an exact boolean (volume > 0.001 mm^3); the gap by
    sampling each body's vertices AND edges against the other's surface.
    """
    from mathutils.bvhtree import BVHTree
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, depsgraph) for o in objs]
    result = {}
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            key = f"{objs[i].name}~{objs[j].name}"
            if _overlap_volume(objs[i], objs[j]) > 1e-3:
                result[key] = 0.0
                continue
            best = float("inf")
            for a, tb in ((objs[i], trees[j]), (objs[j], trees[i])):
                for p in _surface_points(a):
                    hit = tb.find_nearest(p)
                    if hit[0] is not None and hit[3] < best:
                        best = hit[3]
            result[key] = round(best, 3)
    return result


# ------------------------------------------------------------------- output

def join(objs, name):
    """Join several objects into one mesh object (no boolean; for multi-body exports)."""
    objs = [o for o in objs if o is not None]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def drop_to_bed(obj):
    """Translate so the part sits on z=0 and is centred in XY (print-bed ready)."""
    lo, hi = bbox_mm(obj)
    move(obj, -(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    return obj


def export_stl(obj, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                          apply_modifiers=True, global_scale=1.0, ascii_format=False)


def render_preview(obj, path, size=900, view=(1.0, -1.25, 0.9)):
    """Workbench render from a 3/4 view, auto-framed to the part."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE"
    shading.single_color = (0.62, 0.64, 0.68)
    shading.show_cavity = True
    shading.show_object_outline = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")

    lo, hi = bbox_mm(obj)
    center = Vector([(a + b) / 2 for a, b in zip(lo, hi)])
    radius = max((Vector(hi) - Vector(lo)).length / 2, 1.0)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = radius * 2.3
    cam_data.clip_end = radius * 50
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    direction = Vector(view).normalized()
    cam.location = center + direction * radius * 6
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def finish(obj, name, out_dir, print_class=None, notes="", render=True, extra=None):
    """Export STL + preview PNG + JSON report for one printable part."""
    os.makedirs(out_dir, exist_ok=True)
    drop_to_bed(obj)
    obj.name = name
    dims = dims_mm(obj)
    manifold, bad = is_manifold(obj)
    report = {
        "name": name,
        "dims_mm": dims,
        "islands": island_count(obj),
        "volume_cm3": volume_cm3(obj),
        "manifold": manifold,
        "non_manifold_edges": bad,
        "triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons),
        "notes": notes,
        **(extra or {}),
    }
    if print_class:
        report["print_check"] = check_print_class(dims_mm(obj, ndigits=None), print_class)
    stl = os.path.join(out_dir, name + ".stl")
    export_stl(obj, stl)
    report["stl"] = stl
    if render:
        png = os.path.join(out_dir, name + ".png")
        render_preview(obj, png)
        report["preview"] = png
        top = os.path.join(out_dir, name + "_top.png")
        render_preview(obj, top, size=700, view=(0.0, -0.0001, 1.0))
        report["preview_top"] = top
        under = os.path.join(out_dir, name + "_under.png")
        render_preview(obj, under, size=700, view=(-1.0, -1.25, -0.8))
        report["preview_under"] = under
    with open(os.path.join(out_dir, name + ".json"), "w") as f:
        json.dump(report, f, indent=2)
    print("PART_REPORT " + json.dumps(report))
    return report

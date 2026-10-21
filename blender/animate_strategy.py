"""Animate STRATEGY.md on top of fall_game_2026.blend (official table + robots).

Run:  Blender -b --factory-startup --python animate_strategy.py -- <out_dir>
Set NO_RENDER=1 to only bake, check collisions and save (fast).

Moves: both robot roots, the 5 ducks, the 5 pom stacks, the hidden poms, both cups,
pickleball 1 and the red pom. Adds a timer/score HUD. Checks every frame that the robots never
overlap each other or a duck that has already been placed, and prints any violation.
"""
import bpy, math, os, sys, json
from mathutils import Vector, Matrix

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "fall_game_2026.blend"))
PIECES = json.load(open(os.path.join(OUT, "pieces.json")))
ENV = json.load(open(os.path.join(OUT, "envelopes.json")))

FPS = 12
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
MATCH, END = 120, 124
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 0, END * FPS
O = bpy.data.objects
A_ROOT, B_ROOT = O["ROBOT_A_root"], O["ROBOT_B_root"]
TAPE_Y = 25.62
A_MOUTH, A_EXIT = 6.25, -7.3        # lane mouth / where a released duck sits (robot-local x)
B_PLOW, B_CLAW = 7.6, 8.4           # plow tip / claw, ahead of B's root
PLAT_Z = PIECES["Platform top"]["max"][2]

def lerp(a, b, u): return a + (b - a) * u

# ---------------------------------------------------------------- robot paths
def path_pose(wps, t):
    """wps: (t, x, y[, 'rev']). Heading = direction of travel; 'rev' keeps the heading while
    backing up; during holds the heading turns toward the next move."""
    t = min(max(t, wps[0][0]), wps[-1][0] - 1e-6)
    heads = []
    for i in range(len(wps) - 1):
        (t0, x0, y0), (t1, x1, y1) = wps[i][:3], wps[i + 1][:3]
        if abs(x1 - x0) + abs(y1 - y0) < 1e-6:
            heads.append(None)
        else:
            h = math.atan2(y1 - y0, x1 - x0)
            heads.append(h + math.pi if (len(wps[i + 1]) > 3 and wps[i + 1][3] == 'rev') else h)
    first = next((h for h in heads if h is not None), 0.0)
    prev, filled = first, []
    for i, h in enumerate(heads):
        if h is None:
            nxt = next((hh for hh in heads[i + 1:] if hh is not None), prev)
            filled.append(('turn', prev, nxt)); prev = nxt
        else:
            filled.append(('move', h, h)); prev = h
    for i in range(len(wps) - 1):
        (t0, x0, y0), (t1, x1, y1) = wps[i][:3], wps[i + 1][:3]
        if t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            kind, h0, h1 = filled[i]
            d = (h1 - h0 + math.pi) % (2 * math.pi) - math.pi
            if kind == 'turn':                       # turn in place during the last 1.5 s of the hold
                tw = min(1.5, t1 - t0)
                ut = min(1.0, max(0.0, (t - (t1 - tw)) / tw))
                return x0, y0, h0 + d * ut
            return lerp(x0, x1, u), lerp(y0, y1, u), h1

# Robot A (mecanum: heading fixed east, strafes freely). Lane mouth at +6.25, exit at -7.3.
A_WPS = [
    (0, 54.3, 5.6), (16, 54.3, 5.6),
    (20, 54.3, 19.5), (24, 44.0, TAPE_Y),          # out of the box, onto the centre lane
    (41, 80.0, TAPE_Y),                            # collects red, green, lavender, blue, yellow
    (49, 79.5, 34.5), (51, 81.0, 34.5),            # zone 2 drop, creep forward
    (57, 80.9, 23.5), (59, 81.6, 23.5),            # zone 4 drop, creep forward
    (62, 81.6, 17.0), (69, 56.0, 17.0), (74, 56.0, 17.0),   # west, hold while B works the cups
    (76, 54.0, 19.5), (82, 33.8, 19.5), (84, 37.8, 19.5),   # zone 3 drop, forward
    (87, 48.0, 19.5), (92, 48.0, 34.6),            # north through the centre column
    (98, 33.8, 34.6), (100, 36.0, 34.6),           # zone 1 drop, forward
    (103, 48.0, 34.6), (111, 48.0, 5.6),           # back east, south through the centre column
    (115, 34.0, 5.6), (117, 36.0, 5.6), (END, 36.0, 5.6),   # zone 5 drop, forward, stop
]
DROPS = [49, 57, 82, 98, 115]       # red, green, lavender, blue, yellow (collection order)
def pose_A(t):
    x, y, _ = path_pose(A_WPS, t); return x, y, 0.0

# Robot B (differential drive). Starts in zone 5 facing east.
B_WPS = [
    (0, 33.0, 5.6), (2, 36.0, 8.5), (11, 48.5, 21.0),        # arcs out of zone 5 heading NE
    (16, 57.0, 29.5), (17.5, 64.0, 32.0),          # left plow wing flips/pushes the upper cup to (59.5, 34)
    (22, 74.0, 27.0), (27, 68.0, 16.0), (28, 68.0, 16.0),    # loops down the east side, faces west
    (50, 68.0, 16.0),                              # waits for A's duck run and drops
    (52, 56.6, 16.0), (58, 28.7, 16.0),            # right plow wing flips the lower cup, pushes it west into zone 5
    (59, 29.7, 16.0, 'rev'), (63, 29.7, 16.0),     # grabs the red pom (camera + claw)
    (64.5, 39.8, 13.0, 'rev'), (65.5, 39.8, 13.0), (66.5, 39.8, 15.5),
    (68, 39.8, 19.0), (70, 31.9, 15.5, 'rev'), (72.5, 31.9, 19.0),        # red, green stacks -> zone 1
    (74.5, 23.9, 15.5, 'rev'), (77, 23.9, 19.0), (79, 15.9, 15.5, 'rev'), (81.5, 15.9, 19.0),
    (83.5, 7.9, 15.5, 'rev'), (86, 7.9, 19.0),     # turquoise, gold stacks
    (87, 6.5, 14.0, 'rev'), (88, 6.5, 14.0),
    (91, 34.0, 14.0), (93.5, 42.0, 8.0), (95.5, 45.0, 5.3),     # down to the bottom wall
    (97.5, 47.5, 5.3),                             # hook knocks pickleball 1 off its post
    (103.5, 66.0, 5.3), (END, 66.0, 5.3),          # pushes it under the platform, places the red pom
]
def pose_B(t): return path_pose(B_WPS, t)

# ---------------------------------------------------------------- pieces (GLB empties moved by world-space deltas)
def rest(name):
    o = O[name]
    return o, o.matrix_world.copy(), Vector(PIECES[name]["center"])
DUCKS = ["Rubber Duck Red 2.25in-1", "Rubber Duck Green 2.25in-1", "Rubber Duck Lavender 2.25in-2", "Rubber Duck Blue 2.25in-1", "Rubber Duck Yellow 2.25in-1"]
STACKS = ["Pom Stack All Red-1", "Pom Stack All Green-1", "Pom Stack All Lavender-2", "Pom Stack All Turquoise-1", "Pom Stack All Gold-1"]
HIDDEN4, RED_POM = "Pom Stack Multicolor OYGB-1", "pom-red-1 2"
CUP_UP, CUP_LOW, BALL1 = "Cup - Black-2", "Cup - Black-1", "pickle ball 2-4"
R = {n: rest(n) for n in DUCKS + STACKS + [HIDDEN4, RED_POM, CUP_UP, CUP_LOW, BALL1]}
for n in R:
    R[n][0].rotation_mode = 'XYZ'

def set_world(name, center, flip=0.0):
    """place a piece so its bbox centre is at `center`; flip = rotation about the world X axis through the centre"""
    o, m0, c0 = R[name]
    m = Matrix.Translation(Vector(center) - c0) @ m0
    if flip:
        m = Matrix.Translation(Vector(center)) @ Matrix.Rotation(flip, 4, 'X') @ Matrix.Translation(-Vector(center)) @ m
    o.matrix_world = m

# ducks
def collect_time(i):
    dx = R[DUCKS[i]][2].x
    for f in range(int(24 * FPS), int(42 * FPS)):
        t = f / FPS
        ax, ay, _ = pose_A(t)
        if abs(ay - TAPE_Y) < 0.5 and ax + A_MOUTH >= dx:
            return t
    return 40
T_COLLECT = [collect_time(i) for i in range(5)]
DROP_POS = {}
def slot_x(i): return -5.0 + 2.5 * i
def duck_center(i, t):
    c0 = R[DUCKS[i]][2]
    tc, td = T_COLLECT[i], DROPS[i]
    if t < tc:
        return c0
    ax, ay, _ = pose_A(t)
    if t >= td:
        if i not in DROP_POS:
            dx, dy, _ = pose_A(td); DROP_POS[i] = Vector((dx + A_EXIT, dy, c0.z))
        return DROP_POS[i]
    dropped = sum(1 for k in range(i) if t >= DROPS[k])
    slot = i - dropped
    sx = slot_x(slot)
    if t - tc < 1.0:
        sx = lerp(A_MOUTH, slot_x(i), t - tc)
    else:
        for k in range(i):
            if 0 <= t - DROPS[k] < 1.0:
                sx = lerp(slot_x(slot + 1), slot_x(slot), t - DROPS[k])
    return Vector((ax + sx, ay, c0.z))

# pom stacks: pushed north by B's plow, one at a time
STACK_T = [66.5, 70, 74.5, 79, 83.5]     # start of each push (red, green, lavender, turquoise, gold)
STACK_END = [68, 72.5, 77, 81.5, 86]     # B stops pushing here and backs away
def stack_center(k, t):
    c0 = R[STACKS[k]][2]
    t0 = STACK_T[k]
    if t < t0:
        return c0
    bx, by, bh = pose_B(min(t, STACK_END[k]))
    y = max(c0.y, by + B_PLOW + 1.2)
    return Vector((c0.x, y, c0.z))

def hidden4_center(t):
    c0 = R[HIDDEN4][2]
    if t < 11: return c0
    if t < 13.5: return c0.lerp(Vector((48.5, 29.0, c0.z)), (t - 11) / 2.5)
    if t < 16: return Vector((48.5, 29.0, c0.z)).lerp(Vector((58.5, 30.0, c0.z)), (t - 13.5) / 2.5)
    return Vector((58.5, 30.0, c0.z))

def cup_up(t):
    c0 = R[CUP_UP][2]
    if t < 11: return c0, 0.0
    flip = math.pi * min(1.0, (t - 11) / 2.0)
    if t < 13.5: return c0.lerp(Vector((46.5, 30.0, c0.z)), (t - 11) / 2.5), flip
    if t < 16: return Vector((46.5, 30.0, c0.z)).lerp(Vector((59.5, 34.0, c0.z)), (t - 13.5) / 2.5), flip
    return Vector((59.5, 34.0, c0.z)), flip
def cup_low(t):
    c0 = R[CUP_LOW][2]
    if t < 52: return c0, 0.0
    flip = math.pi * min(1.0, (t - 52) / 2.0)
    if t < 58: return c0.lerp(Vector((18.5, 7.3, c0.z)), (t - 52) / 6.0), flip
    return Vector((18.5, 7.3, c0.z)), flip

def red_pom(t):
    c0 = R[RED_POM][2]
    spill = Vector((21.3, 14.4, c0.z))
    if t < 52: return c0
    if t < 55: return c0.lerp(spill, (t - 52) / 3.0)
    if t < 60: return spill
    if t < 63:                                      # lifted into the claw
        bx, by, bh = pose_B(t)
        claw = Vector((bx + B_CLAW * math.cos(bh) - 1.6 * math.sin(bh), by + B_CLAW * math.sin(bh) + 1.6 * math.cos(bh), 3.2))
        return spill.lerp(claw, (t - 60) / 3.0)
    if t < 105.5:                                   # carried
        bx, by, bh = pose_B(t)
        return Vector((bx + B_CLAW * math.cos(bh) - 1.6 * math.sin(bh), by + B_CLAW * math.sin(bh) + 1.6 * math.cos(bh), 3.2))
    bx, by, bh = pose_B(105.5)
    start = Vector((bx + B_CLAW, by + 1.6, 3.2))
    top = Vector((bx + 6.7, by + 1.6, 7.0))
    end = Vector((bx + 6.7, by + 1.6, PLAT_Z + 0.75))
    if t < 109.5: return start.lerp(top, (t - 105.5) / 4.0)
    if t < 111.5: return top.lerp(end, (t - 109.5) / 2.0)
    return end

def ball1(t):
    c0 = R[BALL1][2]
    r = 1.44
    if t < 96: return c0
    land = Vector((pose_B(97.5)[0] + B_PLOW + r + 0.3, 5.3, r))
    if t < 97.5: return c0.lerp(land, (t - 96) / 1.5)
    bx, by, bh = pose_B(min(t, 103.5))
    return Vector((bx + B_PLOW + r + 0.3, 5.3, r))

# ---------------------------------------------------------------- score
EVENTS = [
    (16, 21, 0, "upper cup upright + off tape"),
    (49, 1, 1, "duck in zone 2"), (57, 1, 1, "duck in zone 4"),
    (58, 21, 0, "lower cup upright + off tape"),
    (68, 8, 0, "red stack: group of 4 in zone 1"), (72.5, 8, 0, "green stack in zone 1"),
    (77, 8, 0, "lavender stack in zone 1"), (81.5, 8, 0, "turquoise stack in zone 1"), (86, 8, 0, "gold stack in zone 1"),
    (82, 1, 1, "duck in zone 3"), (98, 1, 1, "duck in zone 1"),
    (103.5, 8, 0, "pickleball under the platform"),
    (111.5, 51, 0, "red pom alone on the platform"),
    (115, 1, 1, "duck in zone 5"),
]
def score(t):
    sub = sum(e[1] for e in EVENTS if t >= e[0]); ducks = sum(e[2] for e in EVENTS if t >= e[0])
    return sub, ducks, sub * max(1, min(5, ducks))

# ---------------------------------------------------------------- bake
def key(obj, f):
    obj.keyframe_insert("location", frame=f); obj.keyframe_insert("rotation_euler", frame=f)
a_z, b_z = A_ROOT.location.z, B_ROOT.location.z
for f in range(0, END * FPS + 1):
    t = f / FPS
    ax, ay, _ = pose_A(t); A_ROOT.location = (ax, ay, a_z); key(A_ROOT, f)
    bx, by, bh = pose_B(t); B_ROOT.location = (bx, by, b_z); B_ROOT.rotation_euler = (0, 0, bh); key(B_ROOT, f)
    for i, n in enumerate(DUCKS):
        set_world(n, duck_center(i, t)); key(O[n], f)
    for k, n in enumerate(STACKS):
        set_world(n, stack_center(k, t)); key(O[n], f)
    set_world(HIDDEN4, hidden4_center(t)); key(O[HIDDEN4], f)
    c, fl = cup_up(t); set_world(CUP_UP, c, fl); key(O[CUP_UP], f)
    c, fl = cup_low(t); set_world(CUP_LOW, c, fl); key(O[CUP_LOW], f)
    set_world(RED_POM, red_pom(t)); key(O[RED_POM], f)
    set_world(BALL1, ball1(t)); key(O[BALL1], f)

# ---------------------------------------------------------------- collision check (2D footprints from the built envelopes)
def rect(cx, cy, h, xmin, xmax, ymin, ymax):
    c, s = math.cos(h), math.sin(h)
    return [(cx + lx * c - ly * s, cy + lx * s + ly * c) for lx, ly in ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax))]
def separated(p, q):
    for poly in (p, q):
        for i in range(4):
            x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % 4]
            nx, ny = y2 - y1, x1 - x2
            pa = [x * nx + y * ny for x, y in p]; qa = [x * nx + y * ny for x, y in q]
            if max(pa) < min(qa) or max(qa) < min(pa):
                return True
    return False
EA, EB = ENV["A"], ENV["B"]
def fpA(t):
    ax, ay, _ = pose_A(t); return rect(ax, ay, 0, EA["min"][0], EA["max"][0], EA["min"][1], EA["max"][1])
def fpB(t):
    bx, by, bh = pose_B(t); return rect(bx, by, bh, EB["min"][0], EB["max"][0], EB["min"][1], EB["max"][1])
bad = set()
for f in range(0, MATCH * FPS):
    t = f / FPS
    if not separated(fpA(t), fpB(t)):
        bad.add(("A-B", round(t, 1)))
    for i in range(5):
        if t > DROPS[i] + 1.5:
            d = duck_center(i, t); duck = rect(d.x, d.y, 0, -1.2, 1.2, -0.65, 0.65)
            for name, fp in (("A", fpA(t)), ("B", fpB(t))):
                if not separated(fp, duck):
                    bad.add((f"{name}-duck{i}", round(t, 1)))
    for k in range(5):
        if t > STACK_T[k] + 3:
            s = stack_center(k, t); st = rect(s.x, s.y, 0, -1.3, 1.3, -1.3, 1.3)
            if not separated(fpA(t), st):
                bad.add((f"A-stack{k}", round(t, 1)))
print("COLLISIONS:", sorted(bad)[:40] if bad else "none")
for i, n in enumerate(DUCKS):
    print("DROP", n.split()[2], [round(v, 1) for v in duck_center(i, 119)])

# ---------------------------------------------------------------- HUD + render
if os.environ.get("NO_RENDER"):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fall_game_2026_animated.blend")); print("DONE (no render)"); sys.exit(0)
HUD = bpy.data.collections.new("HUD"); scene.collection.children.link(HUD)
hud_mat = bpy.data.materials.new("HUD text"); hud_mat.diffuse_color = (0.02, 0.02, 0.02, 1)
cam = O["Cam top"]; cam.data.ortho_scale = 112; cam.location = (46.5, 14.0, 150); scene.camera = cam
def hud_text(body, loc, size, name):
    bpy.ops.object.text_add(location=loc)
    o = bpy.context.object; o.name = name
    o.data.body = body; o.data.size = size; o.data.materials.append(hud_mat)
    for c in o.users_collection: c.objects.unlink(o)
    HUD.objects.link(o); return o
def vis_keys(o, pairs):
    for frame, hidden in pairs:
        o.hide_render = hidden; o.hide_viewport = hidden
        o.keyframe_insert("hide_render", frame=frame); o.keyframe_insert("hide_viewport", frame=frame)
hud_text("2026 Fall Game - plan v2     A: Duck Runner (mecanum)     B: Point Scorer", (-2, -6.0, 0.1), 2.6, "HUD title")
for s in range(0, END + 1):
    sub, ducks, tot = score(min(s, MATCH))
    o = hud_text(f"t = {min(s, MATCH):3d} s     subtotal {sub:3d}  x{max(1, min(ducks, 5))} (zones with 1 duck: {ducks})  =  {tot:4d}", (-2, -10.5, 0.1), 2.6, f"HUD {s:03d}")
    vis_keys(o, [(0, s > 0), (s * FPS, False), ((s + 1) * FPS, True)])
for i, (te, _, _, label) in enumerate(EVENTS):
    o = hud_text(f"+ {label}", (-2, -14.5, 0.1), 2.2, f"HUD event {i}")
    vis_keys(o, [(0, True), (int(te * FPS), False), (int((te + 4) * FPS), True)])
bpy.context.view_layer.layer_collection.children["Robot showcase (off table)"].exclude = True
bpy.context.view_layer.layer_collection.children["Zone labels"].exclude = False

scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.image_settings.media_type = 'VIDEO'
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'; scene.render.ffmpeg.codec = 'H264'; scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.filepath = os.path.join(OUT, "strategy_animation.mp4")
bpy.ops.render.render(animation=True)
scene.render.image_settings.media_type = 'IMAGE'; scene.render.image_settings.file_format = 'PNG'
for f, name in ((30 * FPS, "anim_30s"), (57 * FPS, "anim_57s"), (76 * FPS, "anim_76s"), (110 * FPS, "anim_110s")):
    scene.frame_set(f); scene.render.filepath = os.path.join(OUT, f"{name}.png"); bpy.ops.render.render(write_still=True)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fall_game_2026_animated.blend"))
print("DONE")

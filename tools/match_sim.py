"""Match simulator: robot routes + piece motion + collision checks (no Blender needed).

    python tools/match_sim.py            # run the plan in tools/match_plan.py, print every violation
    python tools/match_sim.py --export   # also write docs/animation/match_data.json for the video

Frame = the one used by STRATEGY.md / code/ / blender/: inches, origin at the inside
corner of the bottom-left PVC, x along the long side (0..93.08), y toward Botguy (0..40.2).

Checks every DT seconds:
  * Robot A vs Robot B (true footprints, rotated rectangles, separating-axis test);
  * each robot vs the PVC walls, the raised platform and the ring posts / pickleballs;
  * each robot vs every game piece it is NOT allowed to touch at that moment. A piece
    may be touched only inside a contact window declared in the plan (a push, a grab,
    the duck lane swallowing a duck). Ducks on the lane are protected until A collects them.
Low pieces (ducks, pom stacks, poms <= 2.75 in) are checked against a robot's LOW
footprint (B's raised claw passes over them); tall ones (cups, pickleballs on posts,
the bottle enclosure, the other robot) against the FULL footprint. The PVC border
(1.3 in OD) and the raised platform edge are also checked against the LOW footprint:
B's raised claw reaches over them (that is how the red pom goes onto the platform).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DT = 0.05
MARGIN = 0.25          # inches of clearance required everywhere
FIELD = (0.0, 0.0, 93.08, 40.2)
PLATFORM = (70.54, -2.0, 96.0, 11.04)            # robots stay out of the raised platform block


# ------------------------------------------------------------------ geometry
def rect_pts(cx, cy, h, x0, x1, y0, y1):
    c, s = math.cos(h), math.sin(h)
    return [(cx + lx * c - ly * s, cy + lx * s + ly * c) for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]


def sat_gap(p, q):
    """Separating distance between two convex polygons (negative = overlap depth)."""
    best = -1e9
    for poly in (p, q):
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            nx, ny = y2 - y1, x1 - x2
            L = math.hypot(nx, ny) or 1.0
            nx, ny = nx / L, ny / L
            pa = [x * nx + y * ny for x, y in p]
            qa = [x * nx + y * ny for x, y in q]
            best = max(best, min(qa) - max(pa), min(pa) - max(qa))
    return best


def poly_circle_gap(poly, cx, cy, r):
    """Distance from a circle to a convex polygon (negative = overlap)."""
    inside = True
    dmin = 1e9
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((cx - x1) * ex + (cy - y1) * ey) / (ex * ex + ey * ey)))
        px, py = x1 + t * ex, y1 + t * ey
        dmin = min(dmin, math.hypot(cx - px, cy - py))
        if (ex * (cy - y1) - ey * (cx - x1)) < 0:
            inside = False
    return -(dmin + r) if inside else dmin - r


def box_gap(poly, bx0, by0, bx1, by1):
    return sat_gap(poly, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)])


# ------------------------------------------------------------------ motion
def lerp(a, b, u):
    return a + (b - a) * u


def ang_lerp(a, b, u):
    d = (b - a + 180) % 360 - 180
    return a + d * u


def pose(keys, t):
    """keys: [(t, x, y, heading_deg), ...] strictly increasing t."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for k0, k1 in zip(keys, keys[1:]):
        if k0[0] <= t <= k1[0]:
            u = (t - k0[0]) / (k1[0] - k0[0]) if k1[0] > k0[0] else 1.0
            return lerp(k0[1], k1[1], u), lerp(k0[2], k1[2], u), ang_lerp(k0[3], k1[3], u)
    return keys[-1][1:]


class Path:
    """Build a keyframed route from motion primitives (times in seconds, inches, degrees)."""

    def __init__(self, t, x, y, h, speed=8.0, turn_rate=120.0):
        self.keys = [(t, x, y, h)]
        self.speed, self.turn_rate = speed, turn_rate
        self.labels = []     # (t0, t1, label) = which code line/function runs

    @property
    def t(self):
        return self.keys[-1][0]

    @property
    def state(self):
        return self.keys[-1][1:]

    def _add(self, t, x, y, h, label):
        t0 = self.t
        self.keys.append((t, x, y, h))
        if label:
            self.labels.append((t0, t, label))
        return self

    def wait_until(self, t, label=None):
        x, y, h = self.state
        return self._add(max(t, self.t + 1e-3), x, y, h, label)

    def wait(self, dt, label=None):
        return self.wait_until(self.t + dt, label)

    def go(self, x, y, speed=None, label=None, h=None):
        """Straight move to (x, y). Heading stays (mecanum strafe) unless h is given."""
        x0, y0, h0 = self.state
        d = math.hypot(x - x0, y - y0)
        return self._add(self.t + max(d / (speed or self.speed), 0.05), x, y, h0 if h is None else h, label)

    def fwd(self, dist, speed=None, label=None):
        """Differential drive: move along the current heading (negative = reverse)."""
        x0, y0, h0 = self.state
        r = math.radians(h0)
        return self._add(self.t + max(abs(dist) / (speed or self.speed), 0.05),
                         x0 + dist * math.cos(r), y0 + dist * math.sin(r), h0, label)

    def turn(self, dh, label=None):
        x0, y0, h0 = self.state
        return self._add(self.t + max(abs(dh) / self.turn_rate, 0.05), x0, y0, h0 + dh, label)

    def arc(self, radius, dh, speed=None, label=None, steps=None):
        """Arc of `radius` turning by dh degrees (+ = left/CCW), driving forward."""
        x0, y0, h0 = self.state
        steps = steps or max(2, int(abs(dh) / 7.5))
        r = math.radians(h0)
        sgn = 1 if dh > 0 else -1
        cx, cy = x0 - sgn * radius * math.sin(r), y0 + sgn * radius * math.cos(r)
        length = abs(math.radians(dh)) * radius
        t0 = self.t
        dur = max(length / (speed or self.speed), abs(dh) / self.turn_rate)
        for k in range(1, steps + 1):
            hk = h0 + dh * k / steps
            rk = math.radians(hk)
            self.keys.append((t0 + dur * k / steps, cx + sgn * radius * math.sin(rk), cy - sgn * radius * math.cos(rk), hk))
        if label:
            self.labels.append((t0, self.t, label))
        return self


def interp_track(track, t):
    """track: [(t, x, y), ...]"""
    if t <= track[0][0]:
        return track[0][1:]
    for a, b in zip(track, track[1:]):
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 1.0
            return lerp(a[1], b[1], u), lerp(a[2], b[2], u)
    return track[-1][1:]


# ------------------------------------------------------------------ simulation
def run(plan, export=False):
    robots, pieces, statics, events, meta = plan["robots"], plan["pieces"], plan["statics"], plan["events"], plan["meta"]
    end = meta["end"]
    worst = {}
    first = {}
    n = int(end / DT) + 1

    def note(key, t, gap):
        if key not in worst or gap < worst[key][1]:
            worst[key] = (t, gap)
        if gap < MARGIN and key not in first:
            first[key] = (t, gap)

    for i in range(n):
        t = i * DT
        polys = {}
        for name, r in robots.items():
            x, y, h = pose(r["keys"], t)
            hr = math.radians(h)
            polys[name] = {"full": rect_pts(x, y, hr, *r["full"]), "low": rect_pts(x, y, hr, *r["low"])}
        # robot vs robot
        note("A~B", t, sat_gap(polys["A"]["full"], polys["B"]["full"]))
        # robot vs field
        fx0, fy0, fx1, fy1 = FIELD
        for name, pp in polys.items():
            poly, low = pp["full"], pp["low"]
            xs, ys = [p[0] for p in low], [p[1] for p in low]
            note(f"{name}~walls", t, min(min(xs) - fx0, min(ys) - fy0, fx1 - max(xs), fy1 - max(ys)))
            note(f"{name}~platform", t, box_gap(low, *PLATFORM))
            for s in statics:
                note(f"{name}~{s['name']}", t, poly_circle_gap(poly, s["x"], s["y"], s["r"]) if "r" in s
                     else box_gap(poly, *s["box"]))
        # robot vs pieces
        for pc in pieces:
            px, py = interp_track(pc["track"], t)
            if pc.get("carried_by") and pc["carried_from"] <= t <= pc.get("carried_to", 1e9):
                continue                        # inside A's lane / B's claw
            for name, pp in polys.items():
                if any(w["robot"] == name and w["t0"] <= t <= w["t1"] for w in pc.get("contact", [])):
                    continue
                poly = pp["low"] if pc["h"] <= 2.75 else pp["full"]
                note(f"{name}~{pc['name']}", t, poly_circle_gap(poly, px, py, pc["r"]))
    ok = not first
    print(f"simulated {end:.0f} s at {DT} s steps, margin {MARGIN} in")
    if ok:
        print("NO CONTACTS: every pair stayed at least", MARGIN, "in apart (outside declared contact windows)")
    else:
        print("CONTACTS (first time each pair came closer than the margin):")
        for k, (t, g) in sorted(first.items(), key=lambda kv: kv[1][0]):
            print(f"  t={t:6.2f}s  {k:28s} gap {g:+.2f} in")
    tight = sorted(((k, v) for k, v in worst.items() if k not in first and v[1] < 1.0), key=lambda kv: kv[1][1])
    if tight:
        print("closest passes (ok, but < 1 in):")
        for k, (t, g) in tight[:12]:
            print(f"  t={t:6.2f}s  {k:28s} gap {g:+.2f} in")
    score = 0
    for ev in sorted(events, key=lambda e: e[0]):
        pass
    if export:
        write_export(plan)
    return ok


def write_export(plan):
    out = {
        "frame": "inches; origin = inside corner of bottom-left PVC; x along the 93.08 in long side, y toward Botguy (0..40.2)",
        "generated_by": "tools/match_sim.py --export (collision-checked)",
        "robot_A": {"name": "Duck Runner", "footprint_in": plan["robots"]["A"]["full"], "keys_t_x_y_h": plan["robots"]["A"]["keys"],
                    "code_labels": plan["robots"]["A"]["labels"]},
        "robot_B": {"name": "Point Scorer", "footprint_in": plan["robots"]["B"]["full"], "low_footprint_in": plan["robots"]["B"]["low"],
                    "keys_t_x_y_h": plan["robots"]["B"]["keys"], "code_labels": plan["robots"]["B"]["labels"]},
        "pieces": [{k: v for k, v in pc.items() if k in ("name", "kind", "color", "r", "h", "track", "carried_by", "carried_from", "carried_to")}
                   for pc in plan["pieces"]],
        "score_events_t_points_duckzone_label": plan["events"],
        "score_formula": "total = subtotal x min(5, max(1, zones holding exactly one duck))",
        "field": plan["meta"]["field"],
    }
    path = os.path.join(ROOT, "docs", "animation", "match_data.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    print("wrote", path)


if __name__ == "__main__":
    import match_plan
    ok = run(match_plan.build(), export="--export" in sys.argv)
    sys.exit(0 if ok else 1)

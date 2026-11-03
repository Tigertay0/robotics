#!/usr/bin/env python
"""Geometry helper for the 2026 Botball Fall Game field map (data/field_map.json, inches).

Coordinates: X along the 96 in length (left -> right), Y across the 48 in width (bottom -> top), Z above the FRP.

Library use
-----------
    from field_geom import FieldMap
    fm = FieldMap.load()
    fm.zone_at(59.5, 7.0)                 # 'start_box'
    fm.zone_at(80, 6)                     # 'under_platform'
    fm.zone_at(80, 6, z=6.0)              # 'raised_platform'
    fm.zone_at(48.0, 20.0)                # 'tape'
    fm.zone_detail(48.0, 13.6)            # region under the tape + every tape strip touched
    fm.distance("start_box", "cup1")                  # centre to centre
    fm.distance("start_box", "cup1", mode="edge")     # nearest edge to nearest edge
    fm.segment_crossings((59.5, 7.0), (74.8, 5.75))   # tape / PVC met by a straight path

Command line
------------
    python tools/field_geom.py                      # summary tables
    python tools/field_geom.py --selftest           # assertions against the rules, PDF and CAD numbers
    python tools/field_geom.py --zone 59.5 7 [Z]    # which zone is this point in
    python tools/field_geom.py --dist start_box cup1 [--edge]
    python tools/field_geom.py --path start_box botguy
    python tools/field_geom.py --md-distances       # markdown distance table used in docs/field-map.md
    python tools/field_geom.py --items              # list named items
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

DEFAULT_MAP = Path(__file__).resolve().parents[1] / "data" / "field_map.json"
EPS = 1e-6
TAPE_TOUCH_MAX_Z = 0.1  # a point higher than this is not touching the tape

Point = tuple[float, float]


def _in_rect(rect: dict, x: float, y: float, pad: float = 0.0) -> bool:
    return rect["x"][0] - pad <= x <= rect["x"][1] + pad and rect["y"][0] - pad <= y <= rect["y"][1] + pad


def _in_polygon(poly: list[list[float]], x: float, y: float) -> bool:
    """Ray casting; points exactly on an edge count as inside."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        # on-edge test
        if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 1e-9 and \
                min(x1, x2) - EPS <= x <= max(x1, x2) + EPS and min(y1, y2) - EPS <= y <= max(y1, y2) + EPS:
            return True
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi >= x:
                inside = not inside
    return inside


def _rect_gap(a: dict, b: dict) -> float:
    dx = max(a["x"][0] - b["x"][1], b["x"][0] - a["x"][1], 0.0)
    dy = max(a["y"][0] - b["y"][1], b["y"][0] - a["y"][1], 0.0)
    return math.hypot(dx, dy)


def _clip_segment(p: Point, q: Point, rect: dict) -> tuple[float, float] | None:
    """Liang-Barsky: parameter interval of segment p->q inside rect, or None."""
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for pk, qk in ((-dx, p[0] - rect["x"][0]), (dx, rect["x"][1] - p[0]),
                   (-dy, p[1] - rect["y"][0]), (dy, rect["y"][1] - p[1])):
        if abs(pk) < EPS:
            if qk < 0:
                return None
        else:
            r = qk / pk
            if pk < 0:
                if r > t1:
                    return None
                t0 = max(t0, r)
            else:
                if r < t0:
                    return None
                t1 = min(t1, r)
    return (t0, t1) if t0 <= t1 else None


class FieldMap:
    """Read-only view over data/field_map.json."""

    def __init__(self, data: dict):
        self.data = data
        self.zones = data["zones"]
        self.tapes = data["tape"]
        self.items = data["named_items"]
        self.edges = data["derived_edges"]
        plat = data["raised_platform"]
        self.platform_rect = plat["footprint"]
        self.platform_underside_z = plat["underside_z"]
        self.platform_top_z = plat["top_z"]
        self.board = data["board"]["outline"]
        self.tape_lower_y0 = data["derived_edges"]["tape_lower_y"][0]
        self.enclosure_rect = data["bottle_ring_enclosure"]["outer_footprint"]
        self.start_box = data["start_box_small"]
        self.strip = data["botguy_strip"]["bbox"]
        self._obstacles = (
            [(p["id"], "pvc", p["box"]) for p in data["pvc"]["pipes"]]
            + [(f["id"], "pvc", f["box"]) for f in data["pvc"]["fittings"]]
            + [("skirt", "skirt", data["skirt"]["box"])]
        )

    @classmethod
    def load(cls, path: str | Path | None = None) -> "FieldMap":
        with open(path or DEFAULT_MAP, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    # ------------------------------------------------------------------ zone lookup
    def tapes_at(self, x: float, y: float, z: float | None = None) -> list[str]:
        if z is not None and z > TAPE_TOUCH_MAX_Z:
            return []
        return [t["id"] for t in self.tapes if _in_rect(t["rect"], x, y)]

    def obstacle_at(self, x: float, y: float, z: float | None = None) -> tuple[str, str] | None:
        """(id, 'pvc'|'skirt') of the PVC / skirt solid containing the point, if any. z=None means floor plan."""
        for oid, kind, box in self._obstacles:
            if not _in_rect(box, x, y):
                continue
            if z is None or box["z"][0] - EPS <= z <= box["z"][1] + EPS:
                return oid, kind
        return None

    def region_at(self, x: float, y: float, z: float | None = None) -> str:
        """Region ignoring tape and PVC: zone1..zone5, start_box, bottle_enclosure, under_platform,
        raised_platform, skirt_gap (0.026 in sliver), botguy_strip, margin (board surface in no scoring area)
        or off_board."""
        if not _in_rect(self.board, x, y):
            return "off_board"
        if _in_rect(self.platform_rect, x, y):
            if z is not None and z >= self.platform_underside_z - 0.01:
                return "raised_platform"
            return "under_platform"
        # 0.026 in CAD sliver between the skirt's outer face (y 12.687) and the lower tape's bottom edge (y 12.713)
        if self.platform_rect["x"][0] <= x <= self.platform_rect["x"][1] and                 self.platform_rect["y"][1] < y < self.tape_lower_y0:
            return "skirt_gap"
        if _in_rect(self.enclosure_rect, x, y):
            return "bottle_enclosure"
        if _in_rect(self.start_box["bbox"], x, y):
            return "start_box"
        for zid, zone in self.zones.items():
            if _in_polygon(zone["polygon"], x, y):
                return zid
        if y >= self.edges["yt"]:
            return "botguy_strip"
        return "margin"

    def zone_detail(self, x: float, y: float, z: float | None = None) -> dict:
        obs = self.obstacle_at(x, y, z)
        return {"region": self.region_at(x, y, z), "tape": self.tapes_at(x, y, z),
                "solid": obs[0] if obs else None, "solid_kind": obs[1] if obs else None}

    def zone_at(self, x: float, y: float, z: float | None = None) -> str:
        """Single name for a point. Precedence: off_board > pvc/skirt > tape > region.
        z=None is a floor-plan lookup (PVC footprints count at any height; a point under the platform is
        'under_platform'); give z to ask about the platform top (z >= 5.5 over the platform)."""
        d = self.zone_detail(x, y, z)
        if d["region"] == "off_board":
            return "off_board"
        if d["solid"]:
            return d["solid_kind"]
        if d["tape"]:
            return "tape"
        return d["region"]

    # ------------------------------------------------------------------ distances
    def _item(self, ref: str | Point) -> dict:
        if isinstance(ref, str):
            if ref not in self.items:
                raise KeyError(f"unknown item {ref!r}; try --items")
            return self.items[ref]
        return {"xy": [ref[0], ref[1]], "rect": None, "z_top": None, "kind": "point"}

    def locate(self, ref: str | Point) -> Point:
        xy = self._item(ref)["xy"]
        return xy[0], xy[1]

    def distance(self, a: str | Point, b: str | Point, mode: str = "center") -> float:
        """Straight-line XY distance in inches. mode='center' (default) or 'edge' (gap between bounding rects;
        0 if they touch or overlap)."""
        ia, ib = self._item(a), self._item(b)
        if mode == "center":
            return math.dist(ia["xy"], ib["xy"])
        if mode != "edge":
            raise ValueError("mode must be 'center' or 'edge'")
        ra = ia["rect"] or {"x": [ia["xy"][0]] * 2, "y": [ia["xy"][1]] * 2}
        rb = ib["rect"] or {"x": [ib["xy"][0]] * 2, "y": [ib["xy"][1]] * 2}
        return _rect_gap(ra, rb)

    def segment_crossings(self, a: str | Point, b: str | Point) -> list[dict]:
        """Tape strips and PVC/skirt solids met by the straight path a -> b, in travel order.
        Each entry: id, kind ('tape'|'pvc'|'skirt'), t_enter (0..1), top_z for solids."""
        p, q = self.locate(a), self.locate(b)
        hits = []
        for t in self.tapes:
            c = _clip_segment(p, q, t["rect"])
            if c:
                hits.append({"id": t["id"], "kind": "tape", "t_enter": round(c[0], 3), "top_z": 0.008})
        for oid, kind, box in self._obstacles:
            c = _clip_segment(p, q, box)
            if c:
                hits.append({"id": oid, "kind": kind, "t_enter": round(c[0], 3), "top_z": box["z"][1]})
        return sorted(hits, key=lambda h: h["t_enter"])

    # ------------------------------------------------------------------ reports
    def distance_rows(self, ref: str, names: list[str]) -> list[tuple[str, float, float, float]]:
        large = "start_box_large"
        return [(n, self.distance(ref, n), self.distance(ref, n, "edge"), self.distance(large, n)) for n in names]

    def key_targets(self) -> list[str]:
        order = ["cup1", "cup2", "duck_red", "duck_green", "duck_lavender", "duck_blue", "duck_yellow",
                 "platform_opening", "under_platform", "pickleball1", "pickleball2", "pickleball3", "pickleball4",
                 "post_left", "post_bottom", "bottle1", "bottle2", "bottle3", "botguy", "big_duck"]
        order += [n for n in self.items if n.startswith("pom_stack_")]
        return [n for n in order if n in self.items]

    def summary(self) -> str:
        d = self.data
        lines = []
        w = lines.append
        w("2026 Botball Fall Game field map (inches; X left->right 0-96, Y bottom->top 0-48, Z above FRP)")
        w(f"  board {self.board['x'][1]:g} x {self.board['y'][1]:g}; playing interior x {self.edges['xl']}-{self.edges['xr']}, "
          f"y {self.edges['yb']}-{self.edges['yt']}")
        w("")
        w("Zones (bbox x0 x1 | y0 y1 | w x h)")
        for zid, z in self.zones.items():
            b = z["bbox"]
            w(f"  {zid:6s} {b['x'][0]:7.3f} {b['x'][1]:7.3f} | {b['y'][0]:7.3f} {b['y'][1]:7.3f} | {z['width_in']:6.2f} x {z['height_in']:5.2f}")
        sb = self.start_box
        w(f"  start_box {sb['bbox']['x'][0]:7.3f} {sb['bbox']['x'][1]:7.3f} | {sb['bbox']['y'][0]:7.3f} {sb['bbox']['y'][1]:7.3f} "
          f"| {sb['width_in']:6.2f} x {sb['height_in']:5.2f}  ceiling {sb['virtual_ceiling_in']}")
        w("")
        w("Tape")
        for t in self.tapes:
            r = t["rect"]
            w(f"  {t['id']:23s} x {r['x'][0]:7.3f}-{r['x'][1]:7.3f}  y {r['y'][0]:7.3f}-{r['y'][1]:7.3f}  {t['length_in']} x {t['width_in']}")
        up = d["under_platform"]
        en = up["entrance"]
        w("")
        w(f"Raised platform: x {self.platform_rect['x']} y {self.platform_rect['y']}  top Z {self.platform_top_z}  underside Z {self.platform_underside_z}")
        w(f"Under platform: open side at x={up['open_side']['plane_x']} (left); clear height {en['clear_height_under_beam_z']}; "
          f"floor-level width {en['floor_level_width_in']} (y {en['floor_level_gap_between_floor_fittings_y']}); "
          f"narrow {en['narrow_width_in']} (y {en['narrow_gap_between_top_elbows_y']}, Z {en['clear_height_under_elbows_z']}-{en['clear_height_under_beam_z']})")
        w("")
        w("Distances from the small Starting Box (centre-to-centre | nearest edges | from large-box centre)")
        w(f"  {'item':18s} {'X':>7s} {'Y':>7s} {'Ztop':>6s} {'ctr':>7s} {'edge':>7s} {'zone5ctr':>9s}")
        for n, c, e, l in self.distance_rows("start_box", self.key_targets()):
            it = self.items[n]
            zt = it["z_top"]
            w(f"  {n:18s} {it['xy'][0]:7.2f} {it['xy'][1]:7.2f} {('%.2f' % zt) if zt is not None else '   -':>6s} {c:7.2f} {e:7.2f} {l:9.2f}")
        return "\n".join(lines)

    def md_distances(self) -> str:
        rows = ["| Item | X | Y | Top Z | From small-box centre | From small-box nearest edge | From Zone 5 centre |",
                "|---|---|---|---|---|---|---|"]
        for n, c, e, l in self.distance_rows("start_box", self.key_targets()):
            it = self.items[n]
            zt = it["z_top"]
            rows.append(f"| {n} | {it['xy'][0]:.2f} | {it['xy'][1]:.2f} | {('%.2f' % zt) if zt is not None else '-'} | "
                        f"{c:.1f} | {e:.1f} | {l:.1f} |")
        return "\n".join(rows)


# ---------------------------------------------------------------------- self test
def selftest(fm: FieldMap) -> int:
    failures: list[str] = []
    passed = 0

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal passed
        if cond:
            passed += 1
        else:
            failures.append(f"FAIL {label} {detail}")

    def near(a: float, b: float, tol: float = 0.02) -> bool:
        return abs(a - b) <= tol

    d = fm.data
    p = d["pieces"]

    # counts stated in the rules / BOM
    check("5 numbered zones", len(fm.zones) == 5)
    check("4 tape strips", len(fm.tapes) == 4)
    check("BOM pipes 31", d["pvc"]["counts_in_cad"]["pipes"] == 31, str(d["pvc"]["counts_in_cad"]))
    check("BOM elbows 9", d["pvc"]["counts_in_cad"]["elbows"] == 9)
    check("BOM tees 17", d["pvc"]["counts_in_cad"]["tees"] == 17)
    check("5 small ducks", len(p["small_ducks"]) == 5)
    check("20 visible poms", sum(s["count"] for s in p["poms_visible_stacks"]) == 20)
    check("5 visible stacks of 4", all(s["count"] == 4 for s in p["poms_visible_stacks"]))
    check("5 hidden poms", len(p["poms_hidden"]) == 5)
    check("hidden poms one per colour", sorted(h["cad_color"] for h in p["poms_hidden"]) ==
          ["gold", "green", "lavender", "red", "turquoise"])
    check("2 cups, 3 bottles, 6 rings, 4 pickleballs", (len(p["cups"]), len(p["bottles"]), len(p["rings"]),
                                                          len(p["pickleballs"])) == (2, 3, 6, 4))
    check("2 ring posts with 3 rings each", sorted(sum(r["post"] == pid for r in p["rings"]) for pid in
                                                    ("post_left", "post_bottom")) == [3, 3])

    # dimensions stated in the rules (p.3) and build PDF (sheets 7, 8)
    sb = fm.start_box
    check("start box 21.125 wide", near(sb["width_in"], 21.125), str(sb["width_in"]))
    check("start box 11.25 tall", near(sb["height_in"], 11.25), str(sb["height_in"]))
    ib = d["board"]["playing_interior"]
    check("PDF 93.08 interior width", near(ib["x"][1] - ib["x"][0], 93.08), str(ib["x"]))
    check("PDF 40.20 interior height", near(ib["y"][1] - ib["y"][0], 40.20), str(ib["y"]))
    check("PDF 24.50 (PVC inner edge to upper tape lower edge)",
          near(fm.edges["tape_upper_y"][0] - fm.edges["yb"], 24.50), str(fm.edges))
    check("PDF 11.25 (PVC inner edge to lower tape lower edge)",
          near(fm.edges["tape_lower_y"][0] - fm.edges["yb"], 11.25))
    check("pieces spaced 8.00 in (ducks)", all(near(b["center_xy"][0] - a["center_xy"][0], 8.0, 0.05)
                                                 for a, b in zip(p["small_ducks"], p["small_ducks"][1:])))
    check("pieces spaced 8.00 in (pom stacks)", all(near(b["center_xy"][0] - a["center_xy"][0], 8.0, 0.05)
                                                     for a, b in zip(p["poms_visible_stacks"], p["poms_visible_stacks"][1:])))
    sk = d["skirt"]
    check("skirt 5.5 tall, 24 wide", near(sk["height_in"], 5.5) and near(sk["box"]["x"][1] - sk["box"]["x"][0], 24.0))
    check("skirt notch 1.625 x 1.625", near(sk["notch"]["size_in"][0], 1.625) and near(sk["notch"]["size_in"][1], 1.625))
    plat = d["raised_platform"]
    check("platform 24 x 12.5", near(plat["footprint"]["x"][1] - plat["footprint"]["x"][0], 24.0) and
          near(plat["footprint"]["y"][1] - plat["footprint"]["y"][0], 12.5))
    check("short tape flush with platform edge", near(fm.tapes[3]["rect"]["x"][1], plat["footprint"]["x"][0], 0.01))

    # zone lookup
    cx, cy = fm.items["start_box"]["xy"]
    cases = [
        ("start box centre", (cx, cy), None, "start_box"),
        ("zone 1 centre", (24.0, 34.7), None, "zone1"),
        ("zone 2 centre", (71.8, 34.7), None, "zone2"),
        ("zone 3 centre", (24.0, 20.3), None, "zone3"),
        ("zone 4 centre", (71.8, 20.3), None, "zone4"),
        ("zone 5 centre", (26.3, 7.1), None, "zone5"),
        ("centre tape", (48.06, 20.0), None, "tape"),
        ("upper tape", (30.0, 26.9), None, "tape"),
        ("lower tape", (60.0, 13.6), None, "tape"),
        ("short tape", (71.0, 6.0), None, "tape"),
        ("enclosure pocket", (2.9, 8.9), None, "bottle_enclosure"),
        ("under platform floor", (82.0, 6.0), None, "under_platform"),
        ("platform top", (82.0, 6.0), 6.5, "raised_platform"),
        ("under-platform floor pipe", (80.0, 0.8), None, "pvc"),
        ("skirt", (80.0, 12.6), None, "skirt"),
        ("left wall pipe", (0.8, 20.0), None, "pvc"),
        ("top strip (Botguy start)", (48.0, 46.5), None, "botguy_strip"),
        ("off board", (-1.0, 5.0), None, "off_board"),
        ("off board top", (10.0, 50.0), None, "off_board"),
    ]
    for label, (x, y), z, want in cases:
        got = fm.zone_at(x, y, z)
        check(f"zone_at {label}", got == want, f"got {got!r} want {want!r}")

    # every duck, pom stack and cup starts touching black tape (so scores nothing until moved)
    for dk in p["small_ducks"]:
        check(f"{dk['id']} starts on tape", "tape_upper_horizontal" in fm.tapes_at(*dk["center_xy"]))
    for st in p["poms_visible_stacks"]:
        check(f"{st['id']} starts on tape", all(fm.tapes_at(q["center"][0], q["center"][1], 0.0) for q in st["poms"]
                                                  if q["level"] == "floor"))
    for c in p["cups"]:
        check(f"{c['id']} starts on tape", len(fm.tapes_at(*c["center_xy"])) >= 2)
    bg = fm.items["botguy"]["xy"]
    check("Botguy starts beyond the top PVC wall", fm.region_at(*bg) == "botguy_strip")
    check("Botguy centred left-to-right", near(bg[0], 48.0, 0.05))

    # coverage: every board-surface sample inside the playing interior is a tape, a pvc solid or a named region
    unnamed = 0
    total = 0
    xl, xr, yb, yt = fm.edges["xl"], fm.edges["xr"], fm.edges["yb"], fm.edges["yt"]
    x = xl + 0.25
    while x < xr:
        y = yb + 0.25
        while y < yt:
            total += 1
            if fm.zone_at(x, y) == "margin":
                unnamed += 1
            y += 0.5
        x += 0.5
    check("playing interior fully classified", unnamed == 0, f"{unnamed}/{total} samples unclassified")

    # zones never overlap each other or the start box (sampled)
    overlap = 0
    for zx in range(0, 960):
        for zy in range(0, 480, 3):
            px, py = zx / 10 + 0.05, zy / 10 + 0.05
            hits = sum(_in_polygon(z["polygon"], px, py) for z in fm.zones.values())
            hits += int(_in_rect(sb["bbox"], px, py))
            if hits > 1:
                overlap += 1
    check("zones and start box disjoint", overlap == 0, f"{overlap} overlapping samples")

    # distances
    sbx, sby = fm.items["start_box"]["xy"]
    c1 = fm.items["cup1"]["xy"]
    check("distance centre start_box->cup1", near(fm.distance("start_box", "cup1"), math.hypot(sbx - c1[0], sby - c1[1]), 1e-6))
    check("edge distance <= centre distance", fm.distance("start_box", "cup1", "edge") <= fm.distance("start_box", "cup1"))
    check("start_box touches pickleball4 within 1.5 in (edge)", fm.distance("start_box", "pickleball4", "edge") < 1.5,
          str(fm.distance("start_box", "pickleball4", "edge")))
    check("platform opening 1.9 in from start box edge", near(fm.distance("start_box", "platform_opening", "edge"), 1.875, 0.01),
          str(fm.distance("start_box", "platform_opening", "edge")))
    check("symmetric distance", near(fm.distance("botguy", "big_duck"), fm.distance("big_duck", "botguy"), 1e-9))
    path = fm.segment_crossings("start_box", "platform_opening")
    check("start_box -> opening crosses only the short tape", [h["id"] for h in path] == ["tape_short_vertical"], str(path))
    path = fm.segment_crossings("start_box", "botguy")
    check("start_box -> Botguy crosses the lower and upper tapes and the top wall",
          {"tape_lower_horizontal", "tape_upper_horizontal"} <= {h["id"] for h in path}, str(path))

    # clearance sanity for the under-platform entrance
    en = d["under_platform"]["entrance"]
    check("pickleball fits under the entrance beam", d["pieces"]["pickleball_spec"]["diameter_in"] < en["clear_height_under_beam_z"])
    check("small duck fits the entrance", d["pieces"]["small_duck_spec"]["height_in"] < en["clear_height_under_elbows_z"])
    check("pickleball fits the narrow entrance width", d["pieces"]["pickleball_spec"]["diameter_in"] < en["narrow_width_in"])
    check("ring ID bigger than post OD", d["pieces"]["ring_spec"]["inner_diameter_in"] > d["pieces"]["ring_posts"][0]["pipe_od_in"])
    check("bottle fits the enclosure (3 in a row)",
          3 * d["pieces"]["bottle_spec"]["body_diameter_in"] <= d["bottle_ring_enclosure"]["interior"]["y"][1]
          - d["bottle_ring_enclosure"]["interior"]["y"][0] + 0.6)

    for f in failures:
        print(f)
    print(f"selftest: {passed} passed, {len(failures)} failed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", help="path to field_map.json (default data/field_map.json)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--zone", nargs="+", type=float, metavar=("X", "Y"), help="X Y [Z]")
    ap.add_argument("--dist", nargs=2, metavar=("A", "B"))
    ap.add_argument("--edge", action="store_true", help="with --dist: nearest-edge distance")
    ap.add_argument("--path", nargs=2, metavar=("A", "B"))
    ap.add_argument("--md-distances", action="store_true")
    ap.add_argument("--items", action="store_true")
    args = ap.parse_args(argv)
    fm = FieldMap.load(args.map)

    if args.selftest:
        return selftest(fm)
    if args.zone:
        if len(args.zone) not in (2, 3):
            ap.error("--zone needs X Y [Z]")
        z = args.zone[2] if len(args.zone) == 3 else None
        print(fm.zone_at(args.zone[0], args.zone[1], z), json.dumps(fm.zone_detail(args.zone[0], args.zone[1], z)))
        return 0
    if args.dist:
        print(f"{fm.distance(args.dist[0], args.dist[1], 'edge' if args.edge else 'center'):.3f} in")
        return 0
    if args.path:
        for h in fm.segment_crossings(*args.path):
            print(h)
        return 0
    if args.md_distances:
        print(fm.md_distances())
        return 0
    if args.items:
        for n, it in fm.items.items():
            print(f"{n:20s} {it['kind']:8s} xy={it['xy']} ztop={it['z_top']}")
        return 0
    print(fm.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())

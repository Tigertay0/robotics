#!/usr/bin/env python
"""Build data/field_map.json: the authoritative 2026 Botball Fall Game field map (inches).

Inputs (all in this repo):
  data/glb_objects_tight.json   vertex-tight world AABBs of every GLB mesh (made by tools/extract_glb_profiles.py)
  data/glb_profiles.json        radial profiles (bottle, ring, cup, ...) and the two corrugated-plastic meshes
  data/glb_objects_raw.json     original Object.bound_box dump (NOT used: inflated for rotated meshes)

Coordinates: X along the 96 in length (left -> right), Y across the 48 in width (bottom -> top), Z above the FRP
surface.  Origin is the bottom-left corner of the board in docs/official/Fall_Game_Table_Overhead.png.

Every section carries "src":
  "cad"       measured from the official GLB (Fall_Game_Table.glb)
  "rules"     stated in docs/official/Botball_Fall_Game_Rule_Summary.txt
  "pdf"       stated in Fall_Game_Table.pdf (build drawings)
  "derived"   computed from the above (e.g. a zone polygon from tape edges + PVC inner edges)
  "inferred"  our reading; not stated in any official document

Usage:  python tools/build_field_map.py
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIGHT = ROOT / "data" / "glb_objects_tight.json"
PROFILES = ROOT / "data" / "glb_profiles.json"
OUT = ROOT / "data" / "field_map.json"

BOARD_W, BOARD_H = 96.0, 48.0
START_CEILING_IN = 12.0
PVC_NOMINAL_OD_IN = 1.315  # 1 in SCH40 pipe; CAD pipe bbox measures 1.30
BOM_ITEM_BY_LENGTH = {
    1.75: 1, 2.5: 2, 8.0: 3, 9.5: 4, 10.0: 5, 12.0: 6, 12.875: 7, 13.875: 8, 14.0: 9,
    17.625: 10, 21.125: 11, 23.375: 12, 25.875: 13,
}


def r3(v: float) -> float:
    return round(float(v), 3) + 0.0  # + 0.0 turns -0.0 into 0.0


def make_box(o: dict) -> dict:
    return {
        "x": [r3(o["min_in"][0]), r3(o["max_in"][0])],
        "y": [r3(o["min_in"][1]), r3(o["max_in"][1])],
        "z": [r3(o["min_in"][2]), r3(o["max_in"][2])],
    }


def union_box(objs: list[dict]) -> dict:
    return {
        "x": [r3(min(o["min_in"][0] for o in objs)), r3(max(o["max_in"][0] for o in objs))],
        "y": [r3(min(o["min_in"][1] for o in objs)), r3(max(o["max_in"][1] for o in objs))],
        "z": [r3(min(o["min_in"][2] for o in objs)), r3(max(o["max_in"][2] for o in objs))],
    }


def center_xy(box: dict) -> list[float]:
    return [r3(sum(box["x"]) / 2), r3(sum(box["y"]) / 2)]


def rect(x0: float, x1: float, y0: float, y1: float) -> dict:
    return {"x": [r3(x0), r3(x1)], "y": [r3(y0), r3(y1)]}


def rect_poly(x0, x1, y0, y1) -> list[list[float]]:
    return [[r3(x0), r3(y0)], [r3(x1), r3(y0)], [r3(x1), r3(y1)], [r3(x0), r3(y1)]]


def inside_xy(box: dict, x: float, y: float, pad: float = 0.0) -> bool:
    return box["x"][0] - pad <= x <= box["x"][1] + pad and box["y"][0] - pad <= y <= box["y"][1] + pad


# --------------------------------------------------------------------------------------------------------------
def load_meshes() -> dict[str, dict]:
    return {o["name"]: o for o in json.loads(TIGHT.read_text())["objects"]}


def pick(meshes: dict[str, dict], prefix: str) -> list[dict]:
    return [m for n, m in sorted(meshes.items()) if n.startswith(prefix)]


# ---- PVC ---------------------------------------------------------------------------------------------------
def classify_pipe(length: float, axis: str, box: dict) -> tuple[str, str | None]:
    cx, cy = center_xy(box)
    z0, z1 = box["z"]
    if axis == "z":
        return ("ring_post", None) if z1 > 8 else ("platform_leg", None)
    if z0 > 3.0:
        return "platform_beam", None
    if length == 1.75:
        return "internal_spacer", None
    if cy < 2.0:
        return "border", "bottom"
    if cy > 40.0:
        return "border", "top"
    if cx < 2.0:
        return "border", "left"
    if cx > 94.0:
        return "border", "right"
    if 73 <= cx <= 92 and 10 < cy < 13:
        return "platform_inner_floor_pipe", None
    return "bottle_enclosure_wall", None


def build_pvc(meshes: dict[str, dict], pieces_for_carry: dict[str, list[tuple[str, dict]]]) -> dict:
    pipes = []
    for name, m in sorted(meshes.items()):
        mt = re.match(r"^([\d.]+) inch pvc-(\d+) - Part$", name)
        if not mt:
            continue
        length = float(mt.group(1))
        box = make_box(m)
        dims = {
            "x": box["x"][1] - box["x"][0],
            "y": box["y"][1] - box["y"][0],
            "z": box["z"][1] - box["z"][0],
        }
        axis = max(dims, key=dims.get)
        role, side = classify_pipe(length, axis, box)
        pipes.append({
            "id": f"pipe_{length:g}in_{mt.group(2)}",
            "mesh": name,
            "bom_item": BOM_ITEM_BY_LENGTH.get(length),
            "nominal_length_in": length,
            "axis": axis,
            "role": role,
            "side": side,
            "box": box,
            "top_z": box["z"][1],
            "od_in_cad": r3(min(d for d in dims.values())),
            "src": "cad",
        })
    fittings = []
    for name, m in sorted(meshes.items()):
        mt = re.match(r"^(T|Elbow) Connector-(\d+) - Part$", name)
        if not mt:
            continue
        kind = "T" if mt.group(1) == "T" else "elbow"
        box = make_box(m)
        top = box["z"][1]
        carries = []
        if top > 2.4 or box["z"][0] > 2.9:
            for pid, pbox in pieces_for_carry.get("carryable", []):
                cx, cy = center_xy(pbox)
                if inside_xy(box, cx, cy) and pbox["z"][0] >= box["z"][0] - 1e-6:
                    carries.append(pid)
        if kind == "T":
            role = "T_with_vertical_socket" if top > 2.4 else "T_in_plane"
        else:
            role = ("platform_beam_corner" if box["z"][0] > 2.9
                    else "floor_to_leg_elbow" if top > 2.4 else "elbow_in_plane")
        # outward-facing stub on the top wall (inferred: starting-light / camera holder; not stated anywhere)
        outward = kind == "T" and box["y"][1] >= 43.9 and top < 2.4
        fittings.append({
            "id": f"{kind}_{mt.group(2)}",
            "mesh": name,
            "type": kind,
            "role": role,
            "box": box,
            "top_z": top,
            "carries": carries,
            "outward_stub_past_top_wall": outward,
            "src": "cad",
        })
    return {
        "nominal_pipe": "1 in SCH 40 (BOM calls it '1 inch ID'); OD 1.315 in nominal, CAD pipe bbox ~1.30 in",
        "pipe_top_z_standard": 1.46,
        "fitting_top_z_in_plane": 1.623,
        "fitting_top_z_with_vertical_socket": 2.498,
        "bom_counts": {"pipes": 31, "elbows": 9, "tees": 17},
        "counts_in_cad": {"pipes": len(pipes), "elbows": sum(f["type"] == "elbow" for f in fittings),
                          "tees": sum(f["type"] == "T" for f in fittings)},
        "pipes": pipes,
        "fittings": fittings,
        "src": "cad",
    }


# ---- tape -------------------------------------------------------------------------------------------------
def build_tape(meshes: dict[str, dict]) -> list[dict]:
    spec = [
        ("tape_center_vertical", "Black duct tape 41.5 in-1 - Part", 41.5),
        ("tape_lower_horizontal", "Black duct tape 89.5 in-1 - Part", 89.5),
        ("tape_upper_horizontal", "Black duct tape 93.5 in-2 - Part", 93.5),
        ("tape_short_vertical", "Black duct tape 12 in-1 - Part", 12.0),
    ]
    tapes = []
    for tid, mesh, nominal in spec:
        b = make_box(meshes[mesh])
        w, h = b["x"][1] - b["x"][0], b["y"][1] - b["y"][0]
        tapes.append({
            "id": tid, "mesh": mesh, "nominal_length_in": nominal,
            "rect": {"x": b["x"], "y": b["y"]},
            "length_in": r3(max(w, h)), "width_in": r3(min(w, h)),
            "orientation": "vertical" if h > w else "horizontal",
            "thickness_in": r3(b["z"][1] - b["z"][0]),
            "src": "cad",
        })
    return tapes


# ---- zones ------------------------------------------------------------------------------------------------
def build_zones(pvc: dict, tapes: list[dict], meshes: dict[str, dict]) -> dict:
    by = {t["id"]: t["rect"] for t in tapes}
    border = {p["side"]: p["box"] for p in pvc["pipes"] if p["role"] == "border"}
    xl = max(p["box"]["x"][1] for p in pvc["pipes"] if p["role"] == "border" and p["side"] == "left")
    xr = min(p["box"]["x"][0] for p in pvc["pipes"] if p["role"] == "border" and p["side"] == "right")
    yb = max(p["box"]["y"][1] for p in pvc["pipes"] if p["role"] == "border" and p["side"] == "bottom")
    yt = min(p["box"]["y"][0] for p in pvc["pipes"] if p["role"] == "border" and p["side"] == "top")
    cv, lo, up, sh = (by["tape_center_vertical"], by["tape_lower_horizontal"],
                      by["tape_upper_horizontal"], by["tape_short_vertical"])
    cx0, cx1 = cv["x"]
    lo_y0, lo_y1 = lo["y"]
    up_y0, up_y1 = up["y"]
    sh_x0, sh_x1 = sh["x"]

    enc_elbows = [meshes["Elbow Connector-23 - Part"], meshes["Elbow Connector-24 - Part"]]
    enc_outer = {
        "x": [r3(min(m["min_in"][0] for m in enc_elbows) - 3.0), r3(max(m["max_in"][0] for m in enc_elbows))],
        "y": [r3(min(m["min_in"][1] for m in enc_elbows)), r3(max(m["max_in"][1] for m in enc_elbows))],
    }
    enc_outer["x"][0] = 0.0  # left side is the board-edge PVC wall; outer footprint starts at the board edge

    def zone(zid, name, x0, x1, y0, y1, note):
        return {
            "id": zid, "name": name, "bbox": rect(x0, x1, y0, y1), "polygon": rect_poly(x0, x1, y0, y1),
            "width_in": r3(x1 - x0), "height_in": r3(y1 - y0), "area_sq_in": r3((x1 - x0) * (y1 - y0)),
            "counts_for_overall_multiplier": True, "note": note, "src": "derived",
        }

    z1 = zone("zone1", "Zone 1 (top-left)", xl, cx0, up_y1, yt,
              "bounded by left PVC inner edge, center tape left edge, upper tape top edge, top PVC inner edge")
    z2 = zone("zone2", "Zone 2 (top-right)", cx1, xr, up_y1, yt, "mirror of Zone 1 across the center tape")
    z3 = zone("zone3", "Zone 3 (middle-left, pom side)", xl, cx0, lo_y1, up_y0,
              "between lower tape top edge and upper tape bottom edge; the 5 pom stacks sit on the upper tape (Z1/Z3 boundary)")
    z4 = zone("zone4", "Zone 4 (middle-right, duck side)", cx1, xr, lo_y1, up_y0,
              "between lower tape top edge and upper tape bottom edge; the 5 small ducks sit on the upper tape (Z2/Z4 boundary)")
    ex = enc_outer["x"][1]
    ey0 = enc_outer["y"][0]
    z5_poly = [[xl, yb], [cx0, yb], [cx0, lo_y0], [ex, lo_y0], [ex, ey0], [xl, ey0]]
    z5 = {
        "id": "zone5", "name": "Zone 5 / large Starting Box (lower-left)",
        "bbox": rect(xl, cx0, yb, lo_y0), "polygon": [[r3(a), r3(b)] for a, b in z5_poly],
        "width_in": r3(cx0 - xl), "height_in": r3(lo_y0 - yb),
        "area_sq_in": r3((cx0 - xl) * (lo_y0 - yb) - (ex - xl) * (lo_y0 - ey0)),
        "counts_for_overall_multiplier": True,
        "note": "L-shaped: rectangle minus the Bottle/Ring enclosure footprint on its left end. Doubles as the large Starting Box (rules p.3)",
        "usable_start_rect": rect(ex, cx0, yb, lo_y0),
        "src": "derived",
    }
    small = {
        "id": "start_box_small", "name": "Small Starting Box",
        "bbox": rect(cx1, sh_x0, yb, lo_y0), "polygon": rect_poly(cx1, sh_x0, yb, lo_y0),
        "width_in": r3(sh_x0 - cx1), "height_in": r3(lo_y0 - yb),
        "virtual_ceiling_in": START_CEILING_IN,
        "stated_size_in": [21.125, 11.25, 12],
        "counts_for_overall_multiplier": False,
        "note": "bounded by center tape right edge, short 12 in tape left edge, lower tape bottom edge and bottom PVC inner edge; matches the 21.125 x 11.25 stated in rules p.3 and PDF sheet 7",
        "src": "derived",
    }
    enclosure = {
        "id": "bottle_ring_enclosure", "name": "Bottle/Ring enclosure",
        "outer_footprint": enc_outer,
        "outer_polygon": rect_poly(0.0, ex, ey0, enc_outer["y"][1]),
        "counts_for_overall_multiplier": False,
        "src": "derived",
    }
    return {
        "interior_bounds": {"x": [r3(xl), r3(xr)], "y": [r3(yb), r3(yt)],
                            "note": "PVC inner edges; PDF sheet 8 gives 93.08 x 40.20 (checked)"},
        "zones": {"zone1": z1, "zone2": z2, "zone3": z3, "zone4": z4, "zone5": z5},
        "start_box_small": small,
        "start_box_large": {"same_as": "zone5", "usable_rect": z5["usable_start_rect"], "src": "rules"},
        "enclosure_outer": enclosure,
        "botguy_strip": {"bbox": rect(0.0, BOARD_W, yt, BOARD_H),
                         "note": "board surface beyond the top PVC wall (Y>41.66). Botguy and the Big Duck target sit here.",
                         "src": "derived"},
        "_edges": {"xl": r3(xl), "xr": r3(xr), "yb": r3(yb), "yt": r3(yt), "tape_center_x": [cx0, cx1],
                   "tape_lower_y": [lo_y0, lo_y1], "tape_upper_y": [up_y0, up_y1]},
    }


# ---- platform ---------------------------------------------------------------------------------------------
def build_platform(meshes, pvc, tapes, profiles) -> dict:
    top = make_box(meshes["12.5x24 No Holes-3 - Part"])
    skirt = make_box(meshes["5.5x24-1 - Part"])
    skirt_v = profiles["raw_vertices"]["5.5x24-1 - Part"]
    notch_x0 = min(v[0] for v in skirt_v if v[2] > 1.0 and v[2] < 1.7 and v[0] < 95)
    notch_h = max(v[2] for v in skirt_v if v[0] > 94 and v[2] < 3)
    foot = rect(top["x"][0], top["x"][1], top["y"][0], top["y"][1])
    beams = [p for p in pvc["pipes"] if p["role"] == "platform_beam"]
    legs = [p for p in pvc["pipes"] if p["role"] == "platform_leg"]
    left_beam = min(beams, key=lambda p: p["box"]["x"][0])
    left_legs = sorted([p for p in legs if p["box"]["x"][0] < 80], key=lambda p: p["box"]["y"][0])
    left_corner_elbows = sorted([f for f in pvc["fittings"] if f["role"] == "platform_beam_corner"
                                 and f["box"]["x"][0] < 80], key=lambda f: f["box"]["y"][0])
    floor_fit_left = [f for f in pvc["fittings"] if f["box"]["x"][0] < 76 and f["box"]["x"][1] > 71
                      and f["box"]["y"][0] < 13 and f["box"]["z"][0] < 0.1 and f["top_z"] > 2.4]
    floor_fit_left.sort(key=lambda f: f["box"]["y"][0])
    t3, e7 = floor_fit_left[0], floor_fit_left[-1]
    clear_y_floor = [t3["box"]["y"][1], e7["box"]["y"][0]]
    clear_y_elbow = [left_corner_elbows[0]["box"]["y"][1], left_corner_elbows[-1]["box"]["y"][0]]
    leg_gap = [left_legs[0]["box"]["y"][1], left_legs[-1]["box"]["y"][0]]
    beam_under = left_beam["box"]["z"][0]
    elbow_under = left_corner_elbows[0]["box"]["z"][0]
    inner_pipe = next(p for p in pvc["pipes"] if p["role"] == "platform_inner_floor_pipe")
    bottom_pipe = next(p for p in pvc["pipes"] if p["id"].startswith("pipe_17.625in") and p["box"]["y"][0] < 2)
    right_wall = next(p for p in pvc["pipes"] if p["role"] == "border" and p["side"] == "right"
                      and p["box"]["y"][0] < 5)
    tape_short = next(t for t in tapes if t["id"] == "tape_short_vertical")
    free_floor = rect(top["x"][0], right_wall["box"]["x"][0], clear_y_floor[0], clear_y_floor[1])
    return {
        "raised_platform": {
            "footprint": foot,
            "polygon": rect_poly(top["x"][0], top["x"][1], top["y"][0], top["y"][1]),
            "top_z": top["z"][1], "underside_z": top["z"][0], "thickness_in": r3(top["z"][1] - top["z"][0]),
            "size_in": [24.0, 12.5],
            "flush_edges": "right edge (x=96) and bottom edge (y=0) flush with the board edge",
            "supports": ("4 legs (2.5 in pipe, Z 1.5-4.0) at each corner of a 19 x 11 in rectangle on floor-level PVC, "
                         "each topped by an elbow carrying a 9.5 in beam (Z 4.04-5.34) along Y at x~72.8 and x~91.8"),
            "src": "cad",
        },
        "skirt": {
            "box": skirt, "height_in": r3(skirt["z"][1] - skirt["z"][0]), "thickness_in": r3(skirt["y"][1] - skirt["y"][0]),
            "face_y": skirt["y"][0],
            "notch": {"x": [r3(notch_x0), skirt["x"][1]], "z": [0.0, r3(notch_h)],
                      "size_in": [r3(skirt["x"][1] - notch_x0), r3(notch_h)],
                      "note": ("1.625 x 1.625 in cut (PDF sheet 6). In the CAD it is at the RIGHT end of the skirt (x 94.375-96), "
                               "clearing T-connector T_7 which passes through the skirt plane; the PDF sheet 6 flat pattern draws it at the left end (mirror). "
                               "It is not a usable gap (it is at the far right wall)."),
                      "src": "cad+pdf"},
            "src": "cad",
        },
        "under_platform": {
            "footprint": foot, "polygon": rect_poly(top["x"][0], top["x"][1], top["y"][0], top["y"][1]),
            "ceiling_z": top["z"][0],
            "open_side": {
                "side": "left (-X), at x=72.0 facing the small Starting Box",
                "plane_x": top["x"][0],
                "gap_from_start_box_in": r3(tape_short["rect"]["x"][1] - tape_short["rect"]["x"][0]),
                "gap_note": "the 12 in black tape (x 70.125-72.0) lies between the Starting Box and the opening",
            },
            "closed_sides": {
                "+Y (toward table interior)": "5.5 in corrugated skirt at y=12.5-12.687, Z 0-5.498 (full height; notch only at far right)",
                "-Y (bottom edge)": "board edge at y=0; floor-level PVC wall (pipe top Z 1.46) - nothing above it but the table edge",
                "+X (right edge)": "board edge at x=96; floor-level PVC wall (Z<=1.46) - nothing above it but the table edge",
            },
            "entrance": {
                "clear_height_under_beam_z": beam_under,
                "clear_height_under_elbows_z": elbow_under,
                "floor_level_gap_between_legs_y": [r3(v) for v in leg_gap],
                "floor_level_gap_between_floor_fittings_y": [r3(v) for v in clear_y_floor],
                "floor_level_width_in": r3(clear_y_floor[1] - clear_y_floor[0]),
                "narrow_gap_between_top_elbows_y": [r3(v) for v in clear_y_elbow],
                "narrow_width_in": r3(clear_y_elbow[1] - clear_y_elbow[0]),
                "limiting_width_note": (f"{r3(clear_y_floor[1] - clear_y_floor[0])} in wide below Z={elbow_under}; "
                                        f"{r3(clear_y_elbow[1] - clear_y_elbow[0])} in wide between the corner elbows for Z {elbow_under}-{beam_under}; "
                                        f"blocked above Z={beam_under} by the 9.5 in support beam"),
                "left_beam_box": left_beam["box"],
                "left_legs": [p["id"] for p in left_legs],
                "left_corner_elbows": [f["id"] for f in left_corner_elbows],
                "left_floor_fittings": [t3["id"], e7["id"]],
                "src": "cad",
            },
            "free_floor_rect": free_floor,
            "free_floor_note": ("board surface not covered by pipes/fittings: x 72.0 to right-wall inner edge, y between the "
                                "two floor-level fittings at the entrance; the 17.625 in floor pipes sit at y 0.162-1.462 and 11.039-12.336"),
            "floor_obstructions": [
                {"id": bottom_pipe["id"], "what": "17.625 in floor pipe along the bottom edge", "box": bottom_pipe["box"]},
                {"id": inner_pipe["id"], "what": "17.625 in floor pipe just inside the skirt (floor-level wall, 1.3 in wide)", "box": inner_pipe["box"]},
                {"id": right_wall["id"], "what": "right-wall floor pipe (9.5 in)", "box": right_wall["box"]},
            ] + [{"id": f["id"], "what": "floor-level fitting", "box": f["box"]}
                 for f in pvc["fittings"] if f["box"]["x"][0] >= 71 and f["box"]["y"][1] <= 13.4
                 and f["box"]["z"][0] < 0.1 and f["box"]["x"][1] >= 71.5],
            "no_tape_under_platform": True,
            "src": "cad",
        },
    }


# ---- game pieces ------------------------------------------------------------------------------------------
def build_pieces(meshes, profiles, zones, pvc) -> dict:
    prof = profiles["profiles"]

    # Botguy
    bg = [m for n, m in meshes.items() if n.startswith(("Cut-Extrude2", "Revolve2", "Extrude7", "Extrude8"))]
    bg_box = union_box(bg)
    base_parts = [m for n, m in meshes.items() if n == "Cut-Extrude2 - Part"]
    base_box = union_box(base_parts)
    botguy = {
        "id": "botguy", "parts": sorted(m["name"] for m in bg), "box": bg_box, "top_z": bg_box["z"][1],
        "center_xy": center_xy(base_box),
        "base_footprint": {"x": base_box["x"], "y": base_box["y"], "z": base_box["z"],
                           "note": "grey base/wheels part (Cut-Extrude2 Part 1)"},
        "torso_box": make_box(meshes["Cut-Extrude2 - Part 2"]),
        "head_box": make_box(meshes["Revolve2 - Part 2"]),
        "faces": "-Y (toward the table interior); visor/eyes at y 42.46-42.96, Z 5.4-6.1",
        "start_pocket_between_T_stubs_x": [44.0, 52.0],
        "scores": "15 pts on top of Raised Platform (rules p.5-6)",
        "src": "cad",
    }

    # Big duck
    bd = [m for n, m in meshes.items() if n.startswith(("Mirror3", "Split Line2"))]
    bd_box = union_box(bd)
    big_duck = {
        "id": "big_duck", "parts": sorted(m["name"] for m in bd), "box": bd_box, "top_z": bd_box["z"][1],
        "center_xy": center_xy(bd_box), "size_in": [r3(bd_box["x"][1] - bd_box["x"][0]), r3(bd_box["y"][1] - bd_box["y"][0]),
                                                  r3(bd_box["z"][1] - bd_box["z"][0])],
        "facing": "-X (beak toward the Starting Box side); beak tip x=72.13 is 0.13 in from the platform edge",
        "note": "two mirrored halves: Mirror3 (y 5.751-8.135) + Split Line2 (y 3.366-5.751)",
        "start_surface": "top of Raised Platform (Z 5.686)",
        "target": "Botguy's start footprint (see botguy.base_footprint) for 15 pts",
        "src": "cad",
    }

    # small ducks
    duck_colors = ["Red", "Green", "Lavender", "Blue", "Yellow"]
    ducks = []
    for c in duck_colors:
        parts = [m for n, m in meshes.items() if n.startswith(f"Rubber Duck {c} ")]
        ub = union_box(parts)
        body = next(m for m in parts if m["name"].startswith(f"Rubber Duck {c} 2.25in") and m["name"].endswith("- Part"))
        bb = make_box(body)
        ducks.append({
            "id": f"duck_{c.lower()}", "color": c.lower(), "box": ub, "body_box": bb, "center_xy": center_xy(bb),
            "size_in": [r3(ub["x"][1] - ub["x"][0]), r3(ub["y"][1] - ub["y"][0]), r3(ub["z"][1] - ub["z"][0])],
            "faces": "+X (beak toward the right edge)", "starts_on_tape": "tape_upper_horizontal",
            "src": "cad",
        })

    # cups
    cup_meshes = [meshes["Cup - Black-1 - Part"], meshes["Cup - Black-2 - Part"]]
    cups = []
    for i, m in enumerate(cup_meshes, 1):
        p = prof["cup"] if i == 1 else prof["cup2"]
        cups.append({
            "id": f"cup{i}", "cad_color": "black", "rules_color": "green or teal (assignment not stated)",
            "box": make_box(m), "center_xy": p["axis_xy"],
            "mouth_diameter_in": r3(2 * p["r_max_overall"]) if False else r3(2 * max(r[2] for r in p["slices_z_rmin_rmax"] if r[0] < 1)),
            "base_diameter_in_approx": r3(2 * max(r[2] for r in p["slices_z_rmin_rmax"] if r[0] > 5.5)),
            "height_in": r3(m["max_in"][2] - m["min_in"][2]),
            "start_orientation": "upside-down: open mouth on the board (mouth is the wide end, base at Z~5.7)",
            "starts_on_tape": ["tape_center_vertical", "tape_lower_horizontal" if i == 1 else "tape_upper_horizontal"],
            "src": "cad",
        })

    # poms
    cups_xy = [tuple(c["center_xy"]) for c in cups]
    color_map = {"gold": "yellow", "turquoise": "blue", "lavender": "purple", "green": "green", "red": "red"}
    poms = []
    for n, m in sorted(meshes.items()):
        mt = re.match(r"^pom-(\w+)-(\d+)( 2)? - Part$", n)
        if not mt:
            continue
        b = make_box(m)
        cx, cy = center_xy(b)
        under = next((f"cup{i + 1}" for i, (px, py) in enumerate(cups_xy) if math.hypot(cx - px, cy - py) < 1.9), None)
        poms.append({
            "mesh": n, "cad_color": mt.group(1), "color": color_map[mt.group(1)], "center": [cx, cy, r3(sum(b["z"]) / 2)],
            "box": b, "level": "top" if b["z"][0] > 0.9 else "floor", "under_cup": under,
        })
    stacks = []
    for cad_color in ["gold", "turquoise", "lavender", "green", "red"]:
        vis = [p for p in poms if p["cad_color"] == cad_color and p["under_cup"] is None]
        xs = [p["center"][0] for p in vis]
        stacks.append({
            "id": f"pom_stack_{cad_color}", "cad_color": cad_color, "color": color_map[cad_color],
            "center_xy": [r3(sum(xs) / len(xs)), 26.9], "poms": vis, "count": len(vis),
            "layout": "3 on the board in a triangle + 1 on top (top pom Z 1.22-2.72)",
            "starts_on_tape": "tape_upper_horizontal", "src": "cad",
        })
    hidden = [p for p in poms if p["under_cup"] is not None]
    hidden_by_cup = {c["id"]: [h["cad_color"] for h in hidden if h["under_cup"] == c["id"]] for c in cups}

    # bottles
    bp = prof["bottle"]
    bottles = []
    for i, nm in enumerate(["Blue Bottle-3 - Part", "Blue Bottle-2 - Part", "Blue Bottle-1 - Part"], 1):
        b = make_box(meshes[nm])
        bottles.append({"id": f"bottle{i}", "mesh": nm, "center_xy": center_xy(b), "box": b, "top_z": b["z"][1],
                        "order": "bottle1 is lowest (y~6.1), bottle3 highest (y~11.6)", "src": "cad"})
    bottle_spec = {
        "height_in": 4.948, "body_diameter_in": r3(2 * 1.263),
        "neck_outer_diameter_in": 1.06, "neck_inner_diameter_in": 1.0,
        "neck_flange_diameter_in": 1.3, "neck_flange_z": [4.0, 4.2],
        "neck_start_z": 3.8, "neck_height_in": r3(4.948 - 3.8), "shoulder_z": [2.7, 3.8],
        "ring_seat_z_estimate": 3.67,
        "note": ("estimated from radial slices of the mesh (data/glb_profiles.json): body OD 2.53 to Z~2.7, shoulder tapers to neck at "
                 "Z~3.8, neck OD ~1.06 up to Z 4.95 with a flange of OD ~1.30 at Z~4.1. A ring (ID 1.414) comes to rest on the shoulder at "
                 "Z~3.67; three rings stack to Z~4.75 (< 4.95 neck top)."),
        "src": "cad (estimated from mesh slices)",
    }

    # rings and posts
    ring_prof = prof["ring"]
    post_meshes = {"post_left": meshes["8 inch pvc-19 - Part"], "post_bottom": meshes["8 inch pvc-18 - Part"]}
    posts = []
    for pid, m in post_meshes.items():
        b = make_box(m)
        fit = next((f["id"] for f in pvc["fittings"] if f["top_z"] > 2.4 and inside_xy(f["box"], *center_xy(b))), None)
        posts.append({"id": pid, "mesh": m["name"], "center_xy": center_xy(b), "box": b, "top_z": b["z"][1],
                      "exposed_above_fitting_z": [2.5, b["z"][1]], "seated_in_fitting": fit,
                      "pipe_od_in": r3(b["x"][1] - b["x"][0]), "src": "cad"})
    rings = []
    for i in range(1, 7):
        m = meshes[f"Ring 1.75in-{i} - Part"]
        b = make_box(m)
        cxy = center_xy({"x": [m["centroid_in"][0], m["centroid_in"][0]], "y": [m["centroid_in"][1], m["centroid_in"][1]]})
        post = min(posts, key=lambda p: math.hypot(p["center_xy"][0] - cxy[0], p["center_xy"][1] - cxy[1]))
        rings.append({"id": f"ring{i}", "mesh": m["name"], "post": post["id"], "center_xy": cxy, "box": b,
                      "stack_level": ((i - 1) % 3) + 1, "z_range": b["z"], "src": "cad"})
    ring_spec = {
        "outer_diameter_in": r3(2 * ring_prof["r_max_overall"]), "inner_diameter_in": r3(2 * ring_prof["r_min_overall"]),
        "thickness_in": r3(ring_prof["z_range"][1] - ring_prof["z_range"][0]),
        "note": "from mesh radial profile; the raw bbox in glb_objects_raw.json (2.71 in) is inflated. ID 1.414 vs post OD 1.30 and neck flange OD ~1.30 leaves only ~0.06 in per side.",
        "src": "cad",
    }

    # pickleballs
    pb = []
    for i in range(1, 5):
        m = meshes[f"pickle ball 2-{i} - Part"]
        b = make_box(m)
        cxy = center_xy(b)
        fit = next((f for f in pvc["fittings"] if f["top_z"] > 2.4 and inside_xy(f["box"], *cxy)), None)
        pb.append({"id": f"pickleball{i}", "mesh": m["name"], "center": [cxy[0], cxy[1], r3(sum(b["z"]) / 2)], "box": b,
                   "diameter_in": r3(b["x"][1] - b["x"][0]), "top_z": b["z"][1],
                   "sits_on": fit["id"] if fit else None,
                   "overhangs_board_edge": bool(b["x"][1] > BOARD_W or b["y"][0] < 0),
                   "src": "cad"})
    pb_notes = {
        "pickleball1": "top wall, x~57.0", "pickleball2": "top wall, x~67.9",
        "pickleball3": "right wall at the pom/duck lane row (y~26.9), overhangs the board edge by ~0.64 in",
        "pickleball4": "bottom wall directly under the center tape, overhangs the board edge by ~0.64 in; 1 in left of the Starting Box corner",
    }
    for p in pb:
        p["position_note"] = pb_notes[p["id"]]

    return {
        "botguy": botguy, "big_duck": big_duck, "small_ducks": ducks,
        "small_duck_order_left_to_right": [d["color"] for d in ducks],
        "poms_visible_stacks": stacks, "poms_hidden": hidden, "poms_hidden_by_cup_cad": hidden_by_cup,
        "cups": cups, "bottles": bottles, "bottle_spec": bottle_spec,
        "ring_posts": posts, "rings": rings, "ring_spec": ring_spec, "pickleballs": pb,
        "pom_spec": {"diameter_in": 1.5, "src": "cad"},
        "pickleball_spec": {"diameter_in": r3(2 * prof["pickleball"]["r_max_overall"]), "src": "cad (vertex extents)"},
        "small_duck_spec": {"body_length_in": 2.06, "body_width_in": 1.456, "height_in": 1.455,
                            "with_beak_length_in": 2.27, "src": "cad"},
    }


def build_named_items(pieces: dict, zones: dict, platform: dict) -> dict:
    items: dict[str, dict] = {}

    def add(name, xy=None, rect_=None, z_top=None, kind="point"):
        items[name] = {"kind": kind, "xy": xy, "rect": rect_, "z_top": z_top}

    z = zones["zones"]
    for zid, zz in z.items():
        add(zid, xy=center_xy({"x": zz["bbox"]["x"], "y": zz["bbox"]["y"]}), rect_=zz["bbox"], kind="area")
    sb = zones["start_box_small"]
    add("start_box", xy=center_xy({"x": sb["bbox"]["x"], "y": sb["bbox"]["y"]}), rect_=sb["bbox"], z_top=START_CEILING_IN, kind="area")
    ur = zones["start_box_large"]["usable_rect"]
    add("start_box_large", xy=center_xy(ur), rect_=ur, z_top=START_CEILING_IN, kind="area")
    enc = zones["enclosure_outer"]["outer_footprint"]
    add("bottle_enclosure", xy=center_xy(enc), rect_=enc, kind="area")
    plat = platform["raised_platform"]
    add("platform", xy=center_xy(plat["footprint"]), rect_=plat["footprint"], z_top=plat["top_z"], kind="area")
    add("platform_opening", xy=[72.0, 6.25],
        rect_={"x": [72.0, 72.0], "y": platform["under_platform"]["entrance"]["floor_level_gap_between_floor_fittings_y"]},
        z_top=platform["under_platform"]["entrance"]["clear_height_under_beam_z"], kind="segment")
    add("under_platform", xy=center_xy(platform["under_platform"]["free_floor_rect"]),
        rect_=platform["under_platform"]["free_floor_rect"], kind="area")
    bg = pieces["botguy"]
    add("botguy", xy=bg["center_xy"], rect_={"x": bg["base_footprint"]["x"], "y": bg["base_footprint"]["y"]},
        z_top=bg["top_z"], kind="piece")
    bd = pieces["big_duck"]
    add("big_duck", xy=bd["center_xy"], rect_={"x": bd["box"]["x"], "y": bd["box"]["y"]}, z_top=bd["top_z"], kind="piece")
    for d in pieces["small_ducks"]:
        add(d["id"], xy=d["center_xy"], rect_={"x": d["box"]["x"], "y": d["box"]["y"]}, z_top=d["box"]["z"][1], kind="piece")
    for c in pieces["cups"]:
        add(c["id"], xy=c["center_xy"], rect_={"x": c["box"]["x"], "y": c["box"]["y"]}, z_top=c["box"]["z"][1], kind="piece")
    for s in pieces["poms_visible_stacks"]:
        xs = [p["box"]["x"] for p in s["poms"]]
        ys = [p["box"]["y"] for p in s["poms"]]
        add(s["id"], xy=s["center_xy"], rect_={"x": [min(a[0] for a in xs), max(a[1] for a in xs)],
                                              "y": [min(a[0] for a in ys), max(a[1] for a in ys)]}, z_top=2.723, kind="piece")
    for b in pieces["bottles"]:
        add(b["id"], xy=b["center_xy"], rect_={"x": b["box"]["x"], "y": b["box"]["y"]}, z_top=b["top_z"], kind="piece")
    for p in pieces["ring_posts"]:
        add(p["id"], xy=p["center_xy"], rect_={"x": p["box"]["x"], "y": p["box"]["y"]}, z_top=p["top_z"], kind="piece")
    for p in pieces["pickleballs"]:
        add(p["id"], xy=p["center"][:2], rect_={"x": p["box"]["x"], "y": p["box"]["y"]}, z_top=p["top_z"], kind="piece")
    return items


def carry_id(mesh_name: str) -> str:
    """Id of a piece that can sit in a fitting socket, matching the ids used elsewhere in the map."""
    mt = re.match(r"^([\d.]+) inch pvc-(\d+) - Part$", mesh_name)
    if mt:
        return f"pipe_{float(mt.group(1)):g}in_{mt.group(2)}"
    mt = re.match(r"^pickle ball 2-(\d+) - Part$", mesh_name)
    return f"pickleball{mt.group(1)}" if mt else mesh_name


def main() -> None:
    meshes = load_meshes()
    profiles = json.loads(PROFILES.read_text())

    # pieces that sit on fittings (needed to fill "carries" on fittings)
    carryable = []
    for n, m in meshes.items():
        if n.startswith(("pickle ball", "8 inch pvc-18", "8 inch pvc-19", "2.5 inch pvc-")):
            carryable.append((carry_id(n), make_box(m)))
    pvc = build_pvc(meshes, {"carryable": carryable})
    tapes = build_tape(meshes)
    zones = build_zones(pvc, tapes, meshes)
    platform = build_platform(meshes, pvc, tapes, profiles)
    pieces = build_pieces(meshes, profiles, zones, pvc)
    named = build_named_items(pieces, zones, platform)

    fm = {
        "meta": {
            "title": "2026 Botball Fall Game - field map",
            "units": "inch",
            "version": 1,
            "coordinate_convention": {
                "origin": "bottom-left corner of the board in docs/official/Fall_Game_Table_Overhead.png",
                "X": "along the 96 in length, left -> right: X = (1.2192 - y_blender) / 0.0254",
                "Y": "across the 48 in width, bottom -> top: Y = (x_blender + 1.2192) / 0.0254",
                "Z": "height above the FRP surface: Z = (z_blender - 0.0213) / 0.0254",
            },
            "sources": {
                "cad_tight_boxes": "data/glb_objects_tight.json (vertex-based, from Fall_Game_Table.glb via tools/extract_glb_profiles.py)",
                "cad_profiles": "data/glb_profiles.json",
                "rules": "docs/official/Botball_Fall_Game_Rule_Summary.txt (v1.0)",
                "build_drawings": "Fall_Game_Table.pdf (9 sheets)",
                "zone_image": "docs/official/Fall_Game_Zones.png",
                "not_used": "data/glb_objects_raw.json: Object.bound_box AABBs are inflated for meshes rotated by non-90 degree angles (30 of 146 meshes differ by >0.02 in, up to 0.7 in)",
            },
            "src_legend": {"cad": "measured from the GLB", "rules": "stated in the rules PDF", "pdf": "stated in the build PDF",
                           "derived": "computed from those", "inferred": "our reading, not stated"},
            "generated_by": "tools/build_field_map.py",
        },
        "board": {
            "outline": {"x": [0.0, BOARD_W], "y": [0.0, BOARD_H]},
            "polygon": rect_poly(0, BOARD_W, 0, BOARD_H),
            "surface_z": 0.0,
            "frp_thickness_in": r3(abs(meshes["FRP - 4x8-1 - Part"]["min_in"][2])),
            "particle_board_thickness_in": r3(meshes["Particle board - 4x8-1 - Part"]["max_in"][2] - meshes["Particle board - 4x8-1 - Part"]["min_in"][2]),
            "surface_note": "FRP 'bumpy side up' (PDF sheet 3): textured white surface",
            "playing_interior": zones["interior_bounds"],
            "src": "cad+pdf",
        },
        "pvc": pvc,
        "tape": tapes,
        "tape_note": ("Tape strips measure 1.875 in wide in the CAD (3M #3920 duct tape is 1-7/8 in), not 2 in; "
                      "lengths 93.5 / 89.5 / 41.5 / 12 match the mesh names and PDF sheets 7-8."),
        "zones": zones["zones"],
        "start_box_small": zones["start_box_small"],
        "start_box_large": zones["start_box_large"],
        "bottle_ring_enclosure": {
            **zones["enclosure_outer"],
            "interior": rect(1.462, 4.038, 4.837, 12.913),
            "interior_note": ("pocket between the left wall pipe (inner edge x=1.462), the 8 in pipe (inner edge x=4.038), the lower 2.5 in "
                              "pipe (top edge y=4.837) and the upper 2.5 in pipe (edge y=12.913): 2.58 x 8.08 in, walls are 1.46 in tall floor-level PVC on all 4 sides"),
            "open_side": "none: closed U of floor-level PVC; pieces enter over the 1.46 in walls (right side x~4.0-5.3 faces Zone 5)",
        },
        "raised_platform": platform["raised_platform"],
        "skirt": platform["skirt"],
        "under_platform": platform["under_platform"],
        "botguy_strip": zones["botguy_strip"],
        "pieces": pieces,
        "named_items": named,
        "derived_edges": zones["_edges"],
        "clearances": {
            "pvc_border_pipe_top_z": 1.46, "pvc_fitting_top_z_in_plane": 1.623, "pvc_fitting_top_z_with_socket": 2.498,
            "ring_stack_top_z": 3.543, "ring_post_top_z": 9.498, "pickleball_z_range": [2.29, 5.22],
            "bottle_top_z": 4.948, "cup_height_in": 5.698, "pom_stack_top_z": 2.723,
            "platform_entrance_clear_z": platform["under_platform"]["entrance"]["clear_height_under_beam_z"],
            "platform_underside_z": platform["raised_platform"]["underside_z"],
            "platform_top_z": platform["raised_platform"]["top_z"],
            "botguy_top_z": pieces["botguy"]["top_z"], "big_duck_top_z": pieces["big_duck"]["top_z"],
            "start_ceiling_z": START_CEILING_IN, "src": "cad+rules",
        },
    }
    OUT.write_text(json.dumps(fm, indent=1))
    print(f"wrote {OUT}  ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

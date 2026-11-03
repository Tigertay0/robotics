#!/usr/bin/env python3
"""Exact scorer for the 2026 Botball Fall Game ("Fall Game 2026" review v1.0).

Source of truth: docs/official/Botball_Fall_Game_Rule_Summary.txt (pages 5-7) and
Botball_Fall_Seeding_Scoresheet.xlsx.  Pure standard library.

Usage
-----
    python tools/score.py data/scenarios/d_strong.json
    python tools/score.py scenario.json --set zone5_counts_for_multiplier=false
    python tools/score.py scenario.json --sensitivity     # total under every ambiguity ruling
    python tools/score.py scenario.json --json            # machine-readable
    python tools/score.py --value-table                   # points per item + duck-zone math
    python tools/score.py --list-options                  # every interpretation switch

Scenario JSON (every key optional unless noted; omitted piece = not on the board / scores 0)
------------------------------------------------------------------------------------------
    {
      "name": "...", "description": "...",
      "interpretation": {"zone5_counts_for_multiplier": true},   # overrides, see --list-options
      "robot": {"left_start_box": true, "disqualified": false},
      "zones": {                                # numbered zones "1".."5"
        "3": {"poms": {"red": 4},               # poms touching the board, off tape, in that zone
                                                # (a dict = one group; a list of dicts = several piles)
              "ducks": 1,                       # small ducks off tape in that zone
              "ducks_on_tape": 0}               # small ducks in that zone but touching black tape
      },
      "poms_elsewhere": {"red": 1},             # poms on the board off tape outside numbered zones
      "platform": {"poms": {"red": 1}, "mystery_red_pom": true},
      "ducks": {"under_platform": 0, "elsewhere_off_tape": 0},
      "pickleballs": {"under_platform": 2, "board_off_tape": 0},
      "rings": {"on_neck": 2, "on_neck_per_bottle": [1, 1, 0],   # per-bottle list optional
                "touching_bottle": 0, "board_off_tape": 0},
      "cups": {"nested": false, "nest_orientation": "upright",
               "pieces": [{"upright": true, "on_tape": true, "touching_board": true}]},
      "botguy": "start" | "platform" | "board" | "none",          # default "start" (unmoved)
      "big_duck": "platform" | "botguy_start" | "board" | "none",  # default "platform" (unmoved)
      "big_duck_zone": 3,                       # optional: which numbered zone a "board" Big Duck sits in
      "base_eligible_count": 17                 # optional: judge's Base Score count, replaces the derived one
    }

Colors: red, yellow, green, blue, purple (aliases gold, turquoise, lavender, violet).

Nothing here mutates its inputs; every function returns new objects.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

# --------------------------------------------------------------------------------------
# Constants (rules text pages 4-7 and the scoresheet)
# --------------------------------------------------------------------------------------
ZONES = (1, 2, 3, 4, 5)
COLORS = ("red", "yellow", "green", "blue", "purple")
COLOR_ALIASES = {"gold": "yellow", "turquoise": "blue", "lavender": "purple", "violet": "purple"}
POMS_PER_COLOR = 5      # 4 visible + 1 hidden
N_DUCKS = 5             # small ducks
N_RINGS = 6
N_PICKLEBALLS = 4
N_CUPS = 2
N_BOTTLES = 3           # inferred from the GLB/overhead render; the rules text gives no count
MAX_MULTIPLIER = 5

PTS = {
    "base": 1,
    "pickleball_under_platform": 7,
    "ring_touching_bottle": 3,
    "ring_on_neck": 15,
    "duck_under_platform": 3,
    "cup_nested": 20,
    "cup_upright": 20,
    "botguy_on_platform": 15,
    "big_duck_at_botguy_start": 15,
    "mystery_red_pom": 50,
    "pom_complete_set": 25,
}

BOTGUY_STATES = ("start", "platform", "board", "none")
BIG_DUCK_STATES = ("platform", "botguy_start", "board", "none")

# option -> (default = official written rule, alternatives, one-line meaning)
OPTIONS: dict[str, tuple[Any, tuple[Any, ...], str]] = {
    "zone5_counts_for_multiplier": (
        True, (False,),
        "Zone 5 (also the large Starting Box) can be a Multiplier Zone. Default True: Overall "
        "Multiplier text, scoresheet row and 5x cap. False = Game Board Areas bullet."),
    "tape_duck_policy": (
        "ignore", ("count", "spoil"),
        "Ducks touching black tape inside a zone. ignore: not in the zone at all. count: still a duck "
        "in the zone (can qualify it or spoil it). spoil: can spoil a zone but never qualify it."),
    "pom_groups_per_zone": (
        "merge", ("separate",),
        "merge: all poms in a zone are one group (scoresheet has one row per zone). "
        "separate: each pile listed for a zone scores on its own."),
    "pom_base_additive": (
        True, (False,),
        "Written rule: Base 1/pom is additive with the pom group score. False: the group score "
        "replaces base for those poms (scoresheet-style single value)."),
    "special_base_additive": (
        True, (False,),
        "Written rule: Base 1 is additive with special scoring (duck/pickleball under platform, "
        "ring on bottle, cup bonuses, Botguy, Big Duck, red pom). False: special value replaces base."),
    "platform_counts_as_board_surface": (
        False, (True,),
        "Whether pieces on the Raised Platform touch 'the board surface' for Base Score."),
    "inverted_nest_counts_as_nested": (
        True, (False,),
        "A nest of two inverted (rim-down) cups earns the 20-pt Nested bonus."),
    "max_rings_per_neck": (
        None, (1,),
        "None: every ring on a neck scores 15. 1: only one ring per bottle neck scores; extras score 0."),
    "any_red_pom_is_mystery": (
        False, (True,),
        "True: any lone red pom on the platform earns the 50, not only the hidden Mystery Red Pom."),
    "big_duck_counts_for_multiplier": (
        False, (True,),
        "True: a Big Duck dropped in a numbered zone counts as 'a duck' for exactly-1. Default False "
        "(scoresheet says 'smaller duck')."),
    "unmoved_botguy_scores_base": (
        True, (False,),
        "Botguy untouched at his start position (on the board, off tape) earns Base 1."),
}

# The ruling we plan against: lowest-scoring for typical boards (used by --conservative and the a2 scenario).
# Note pom_groups_per_zone='merge' is the plan-safe choice, not always the lowest: two unique piles of 2 score
# 12 separately but 20 merged.
CONSERVATIVE_OPTIONS: dict[str, Any] = {
    "zone5_counts_for_multiplier": False,
    "tape_duck_policy": "spoil",
    "pom_groups_per_zone": "merge",
    "pom_base_additive": False,
    "special_base_additive": False,
    "platform_counts_as_board_surface": False,
    "inverted_nest_counts_as_nested": False,
    "max_rings_per_neck": 1,
    "any_red_pom_is_mystery": False,
    "big_duck_counts_for_multiplier": True,
    "unmoved_botguy_scores_base": False,
}


# --------------------------------------------------------------------------------------
# Interpretation handling
# --------------------------------------------------------------------------------------
def default_interpretation() -> dict[str, Any]:
    return {key: spec[0] for key, spec in OPTIONS.items()}


def resolve_interpretation(*layers: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge override layers (later wins) onto the defaults and validate every value."""
    merged = default_interpretation()
    for layer in layers:
        for key, value in (layer or {}).items():
            if key not in OPTIONS:
                raise ValueError(f"unknown interpretation option {key!r}; valid: {sorted(OPTIONS)}")
            allowed = (OPTIONS[key][0],) + OPTIONS[key][1]
            if value not in allowed or (isinstance(value, bool) != isinstance(allowed[0], bool)):
                raise ValueError(f"option {key!r}: {value!r} not allowed; choose one of {list(allowed)}")
            merged[key] = value
    return merged


# --------------------------------------------------------------------------------------
# Input normalisation / validation
# --------------------------------------------------------------------------------------
def _count(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{path}: expected a non-negative integer, got {value!r}")
    return value


def _color(name: str, path: str) -> str:
    key = COLOR_ALIASES.get(name.lower(), name.lower())
    if key not in COLORS:
        raise ValueError(f"{path}: unknown pom color {name!r}; use {COLORS}")
    return key


def _pom_counts(raw: Any, path: str) -> dict[str, int]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{path}: expected {{color: count}}")
    out: dict[str, int] = {}
    for name, n in raw.items():
        c = _color(name, path)
        out[c] = out.get(c, 0) + _count(n, f"{path}.{name}")
    return {c: n for c, n in out.items() if n}


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: expected an object, got {type(value).__name__}")
    return value


def _flag(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{path}: expected true/false, got {value!r}")
    return value


def _normalize_zone(raw: Any, z: int) -> dict[str, Any]:
    path = f"zones.{z}"
    raw = _mapping(raw, path)
    poms_raw = raw.get("poms", {})
    piles = poms_raw if isinstance(poms_raw, list) else [poms_raw]
    return {
        "poms": [p for p in (_pom_counts(pile, f"{path}.poms") for pile in piles) if p],
        "ducks": _count(raw.get("ducks", 0), f"{path}.ducks"),
        "ducks_on_tape": _count(raw.get("ducks_on_tape", 0), f"{path}.ducks_on_tape"),
    }


def _normalize_cups(raw: Any) -> dict[str, Any]:
    raw = _mapping(raw, "cups")
    if not isinstance(raw.get("pieces", []), list):
        raise ValueError("cups.pieces: expected a list")
    pieces = []
    for i, cup in enumerate(raw.get("pieces", [])):
        cup = _mapping(cup, f"cups.pieces[{i}]")
        pieces.append({
            "upright": _flag(cup.get("upright", False), f"cups.pieces[{i}].upright"),
            "on_tape": _flag(cup.get("on_tape", False), f"cups.pieces[{i}].on_tape"),
            "touching_board": _flag(cup.get("touching_board", True), f"cups.pieces[{i}].touching_board"),
        })
    nested = _flag(raw.get("nested", False), "cups.nested")
    orientation = raw.get("nest_orientation", "upright")
    if orientation not in ("upright", "inverted"):
        raise ValueError("cups.nest_orientation must be 'upright' or 'inverted'")
    if len(pieces) > N_CUPS:
        raise ValueError(f"cups.pieces: at most {N_CUPS} cups exist")
    if nested and len(pieces) != N_CUPS:
        raise ValueError("cups.nested needs both cups listed in cups.pieces")
    return {"nested": nested, "nest_orientation": orientation, "pieces": pieces}


def _normalize_rings(raw: Any) -> dict[str, Any]:
    raw = _mapping(raw, "rings")
    on_neck = _count(raw.get("on_neck", 0), "rings.on_neck")
    per_bottle = raw.get("on_neck_per_bottle")
    if per_bottle is not None:
        if not isinstance(per_bottle, list) or len(per_bottle) != N_BOTTLES:
            raise ValueError(f"rings.on_neck_per_bottle needs {N_BOTTLES} entries")
        per_bottle = [_count(v, "rings.on_neck_per_bottle") for v in per_bottle]
        if sum(per_bottle) != on_neck:
            raise ValueError("rings.on_neck_per_bottle must sum to rings.on_neck")
    return {
        "on_neck": on_neck,
        "on_neck_per_bottle": per_bottle,
        "touching_bottle": _count(raw.get("touching_bottle", 0), "rings.touching_bottle"),
        "board_off_tape": _count(raw.get("board_off_tape", 0), "rings.board_off_tape"),
    }


def _check_inventory(sc: Mapping[str, Any]) -> None:
    """Reject scenarios that use more pieces than exist."""
    by_color = dict.fromkeys(COLORS, 0)
    groups = [g for z in sc["zones"].values() for g in z["poms"]]
    groups += [sc["poms_elsewhere"], sc["platform"]["poms"]]
    for group in groups:
        for color, n in group.items():
            by_color[color] += n
    for color, n in by_color.items():
        if n > POMS_PER_COLOR:
            raise ValueError(f"{n} {color} poms used but only {POMS_PER_COLOR} exist")
    ducks = sum(z["ducks"] + z["ducks_on_tape"] for z in sc["zones"].values())
    ducks += sc["ducks"]["under_platform"] + sc["ducks"]["elsewhere_off_tape"]
    limits = (
        ("small ducks", ducks, N_DUCKS),
        ("pickleballs", sum(sc["pickleballs"].values()), N_PICKLEBALLS),
        ("rings", sc["rings"]["on_neck"] + sc["rings"]["touching_bottle"] + sc["rings"]["board_off_tape"], N_RINGS),
    )
    for label, used, cap in limits:
        if used > cap:
            raise ValueError(f"{used} {label} used but only {cap} exist")
    platform = sc["platform"]
    if platform["mystery_red_pom"] and not platform["poms"].get("red"):
        raise ValueError("platform.mystery_red_pom is true but no red pom is on the platform")


def normalize(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a raw scenario and return a fully-populated copy."""
    data = _mapping(data, "scenario")
    zones_raw = _mapping(data.get("zones", {}), "zones")
    by_zone: dict[int, Any] = {}
    for key, value in zones_raw.items():
        try:
            number = int(key)
        except (TypeError, ValueError):
            raise ValueError(f"zones.{key}: zones are 1..5") from None
        if number not in ZONES or number in by_zone:
            raise ValueError(f"zones.{key}: zones are 1..5, each listed once")
        by_zone[number] = value
    zones = {z: _normalize_zone(by_zone.get(z, {}), z) for z in ZONES}
    robot = _mapping(data.get("robot", {}), "robot")
    platform_raw = _mapping(data.get("platform", {}), "platform")
    ducks_raw = _mapping(data.get("ducks", {}), "ducks")
    pick_raw = _mapping(data.get("pickleballs", {}), "pickleballs")
    botguy = data.get("botguy", "start")
    big_duck = data.get("big_duck", "platform")
    if botguy not in BOTGUY_STATES:
        raise ValueError(f"botguy must be one of {BOTGUY_STATES}")
    if big_duck not in BIG_DUCK_STATES:
        raise ValueError(f"big_duck must be one of {BIG_DUCK_STATES}")
    big_duck_zone = data.get("big_duck_zone")
    if big_duck_zone is not None and (big_duck != "board" or big_duck_zone not in ZONES):
        raise ValueError("big_duck_zone (1..5) is only allowed with big_duck = 'board'")
    override = data.get("base_eligible_count")
    sc = {
        "name": str(data.get("name", "unnamed")),
        "description": str(data.get("description", "")),
        "robot": {"left_start_box": _flag(robot.get("left_start_box", True), "robot.left_start_box"),
                  "disqualified": _flag(robot.get("disqualified", False), "robot.disqualified")},
        "zones": zones,
        "poms_elsewhere": _pom_counts(data.get("poms_elsewhere", {}), "poms_elsewhere"),
        "platform": {"poms": _pom_counts(platform_raw.get("poms", {}), "platform.poms"),
                     "mystery_red_pom": _flag(platform_raw.get("mystery_red_pom", False), "platform.mystery_red_pom")},
        "ducks": {"under_platform": _count(ducks_raw.get("under_platform", 0), "ducks.under_platform"),
                  "elsewhere_off_tape": _count(ducks_raw.get("elsewhere_off_tape", 0), "ducks.elsewhere_off_tape")},
        "pickleballs": {"under_platform": _count(pick_raw.get("under_platform", 0), "pickleballs.under_platform"),
                        "board_off_tape": _count(pick_raw.get("board_off_tape", 0), "pickleballs.board_off_tape")},
        "rings": _normalize_rings(data.get("rings", {})),
        "cups": _normalize_cups(data.get("cups", {})),
        "botguy": botguy,
        "big_duck": big_duck,
        "big_duck_zone": big_duck_zone,
        "base_eligible_count": None if override is None else _count(override, "base_eligible_count"),
        "interpretation": dict(_mapping(data.get("interpretation", {}), "interpretation")),
    }
    _check_inventory(sc)
    return sc


# --------------------------------------------------------------------------------------
# Scoring primitives
# --------------------------------------------------------------------------------------
def item(category: str, label: str, count: int, pts_each: int, note: str = "") -> dict[str, Any]:
    return {"category": category, "item": label, "count": count, "pts_each": pts_each,
            "subtotal": count * pts_each, "note": note}


def classify_pom_group(counts: Mapping[str, int]) -> tuple[str, int, int]:
    """Return (kind, n_poms, group_score) per the Pom Scoring rules, ignoring base score.

    kinds: empty | same_color (1-4 linear) | complete_set (5 of one color, alone) |
           all_different (n colors, no duplicates, n>=2: n^2) | mixed (base only).
    Mirrors the scoresheet formula IF(B=5,25,IF(B>=1,B,IF(C>=2,C^2,0))) for correctly-entered B/C.
    """
    present = {c: n for c, n in counts.items() if n > 0}
    n = sum(present.values())
    if n == 0:
        return "empty", 0, 0
    if len(present) == 1:
        return ("complete_set", n, PTS["pom_complete_set"]) if n == POMS_PER_COLOR else ("same_color", n, n)
    if all(v == 1 for v in present.values()):
        return "all_different", n, n * n
    return "mixed", n, 0


def merge_piles(piles: list[dict[str, int]]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for pile in piles:
        for color, n in pile.items():
            merged[color] = merged.get(color, 0) + n
    return merged


def score_poms(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> tuple[list, list]:
    items: list[dict[str, Any]] = []
    base: list[tuple[str, int]] = []
    additive = interp["pom_base_additive"]
    for z in ZONES:
        piles = sc["zones"][z]["poms"]
        groups = [merge_piles(piles)] if interp["pom_groups_per_zone"] == "merge" and piles else piles
        for g, group in enumerate(groups, 1):
            kind, n, pts = classify_pom_group(group)
            tag = f"zone {z}" + (f" pile {g}" if len(groups) > 1 else "")
            if kind == "mixed" or additive:
                base.append((f"poms {tag}", n))
            if kind != "mixed":
                items.append(item("9. Poms", f"{tag}: {kind} x{n}", 1, pts,
                                  "additive with base" if additive else "replaces base for these poms"))
    base.append(("poms elsewhere off tape", sum(sc["poms_elsewhere"].values())))
    return items, base


def score_platform(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> tuple[list, list, list]:
    """Botguy, Big Duck, Mystery Red Pom (everything tied to the Raised Platform / Botguy start)."""
    items: list[dict[str, Any]] = []
    base: list[tuple[str, int]] = []
    notes: list[str] = []
    on_board = interp["platform_counts_as_board_surface"]
    extra_base = interp["special_base_additive"]

    botguy = sc["botguy"]
    if botguy == "platform":
        items.append(item("6. Botguy", "on top of platform", 1, PTS["botguy_on_platform"]))
        base.append(("botguy on platform", int(on_board and extra_base)))
    elif botguy == "board" or (botguy == "start" and interp["unmoved_botguy_scores_base"]):
        base.append((f"botguy ({botguy})", 1))

    big = sc["big_duck"]
    if big == "botguy_start":
        items.append(item("7. Big Duck", "at Botguy's starting position", 1, PTS["big_duck_at_botguy_start"]))
        base.append(("big duck at botguy start", int(extra_base)))
    elif big == "board":
        base.append(("big duck on board", 1))
    elif big == "platform":
        base.append(("big duck on platform", int(on_board)))

    plat_poms = sc["platform"]["poms"]
    n_plat = sum(plat_poms.values())
    scored_mystery = False
    if n_plat:
        is_mystery = sc["platform"]["mystery_red_pom"] or (interp["any_red_pom_is_mystery"] and plat_poms.get("red", 0) >= 1)
        if is_mystery and n_plat == 1:
            items.append(item("8. Mystery Red Pom", "alone on platform", 1, PTS["mystery_red_pom"], "multiplied"))
            scored_mystery = True
        elif is_mystery:
            notes.append("Mystery Red Pom bonus voided: other poms are on the platform with it.")
        base.append(("poms on platform", int(on_board) * (n_plat - (1 if scored_mystery and not extra_base else 0))))
    return items, base, notes


def score_ducks_and_toys(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> tuple[list, list]:
    items: list[dict[str, Any]] = []
    base: list[tuple[str, int]] = []
    extra_base = interp["special_base_additive"]
    under = sc["ducks"]["under_platform"]
    if under:
        items.append(item("4. Ducks", "under raised platform", under, PTS["duck_under_platform"]))
        base.append(("ducks under platform", under * int(extra_base)))
    base.append(("ducks in zones, off tape", sum(z["ducks"] for z in sc["zones"].values())))
    base.append(("ducks elsewhere off tape", sc["ducks"]["elsewhere_off_tape"]))

    balls = sc["pickleballs"]
    if balls["under_platform"]:
        items.append(item("2. Pickleballs", "under raised platform", balls["under_platform"], PTS["pickleball_under_platform"]))
        base.append(("pickleballs under platform", balls["under_platform"] * int(extra_base)))
    base.append(("pickleballs on board", balls["board_off_tape"]))
    return items, base


def _scoring_neck_rings(rings: Mapping[str, Any], cap: int | None) -> int:
    if cap is None or rings["on_neck"] == 0:
        return rings["on_neck"]
    if rings["on_neck_per_bottle"] is None:
        raise ValueError("max_rings_per_neck is set: rings.on_neck_per_bottle is required")
    return sum(min(n, cap) for n in rings["on_neck_per_bottle"])


def score_rings(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> tuple[list, list]:
    items: list[dict[str, Any]] = []
    base: list[tuple[str, int]] = []
    rings = sc["rings"]
    neck = _scoring_neck_rings(rings, interp["max_rings_per_neck"])
    if neck:
        note = "" if neck == rings["on_neck"] else f"{rings['on_neck'] - neck} extra ring(s) on a neck score 0"
        items.append(item("3. Rings", "on bottle neck", neck, PTS["ring_on_neck"], note))
    if rings["touching_bottle"]:
        items.append(item("3. Rings", "touching bottle, not on neck", rings["touching_bottle"], PTS["ring_touching_bottle"]))
        base.append(("rings touching bottle (also on board)", rings["touching_bottle"] * int(interp["special_base_additive"])))
    base.append(("rings on board off tape", rings["board_off_tape"]))
    return items, base


def score_cups(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> tuple[list, list]:
    items: list[dict[str, Any]] = []
    base: list[tuple[str, int]] = []
    cups = sc["cups"]
    nested_counts = cups["nested"] and (cups["nest_orientation"] == "upright" or interp["inverted_nest_counts_as_nested"])
    if nested_counts:
        items.append(item("5. Cups", "nested (one inside the other)", 1, PTS["cup_nested"], "regardless of tape"))
    flat = sum(1 for c in cups["pieces"] if c["upright"] and c["touching_board"])
    if flat:
        items.append(item("5. Cups", "flat/upright on the board", flat, PTS["cup_upright"], "regardless of nesting or tape"))
    for i, cup in enumerate(cups["pieces"], 1):
        has_special = bool(nested_counts or (cup["upright"] and cup["touching_board"]))
        eligible = cup["touching_board"] and not cup["on_tape"]
        base.append((f"cup {i}", int(eligible and (interp["special_base_additive"] or not has_special))))
    return items, base


def score_multiplier(sc: Mapping[str, Any], interp: Mapping[str, Any]) -> dict[str, Any]:
    policy = interp["tape_duck_policy"]
    detail: dict[int, dict[str, Any]] = {}
    for z in ZONES:
        zone = sc["zones"][z]
        in_zone = sc["big_duck"] == "board" and sc["big_duck_zone"] == z
        big = int(in_zone and interp["big_duck_counts_for_multiplier"])
        off, tape = zone["ducks"] + big, zone["ducks_on_tape"]
        total = off if policy == "ignore" else off + tape
        qualifies = total == 1 if policy != "spoil" else (total == 1 and tape == 0)
        reason = "exactly 1 duck" if qualifies else f"{total} duck(s) counted"
        if z == 5 and not interp["zone5_counts_for_multiplier"]:
            qualifies, reason = False, "zone 5 excluded by ruling"
        detail[z] = {"ducks_counted": total, "ducks_on_tape": tape, "qualifies": qualifies, "reason": reason}
    count = sum(1 for d in detail.values() if d["qualifies"])
    return {"qualifying_zones": [z for z in ZONES if detail[z]["qualifies"]],
            "count": count, "multiplier": max(1, min(MAX_MULTIPLIER, count)), "detail": detail}


# --------------------------------------------------------------------------------------
# Top-level scoring
# --------------------------------------------------------------------------------------
def score(data: Mapping[str, Any], interpretation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Score one scenario. `interpretation` overrides those embedded in the scenario."""
    sc = normalize(data)
    interp = resolve_interpretation(sc["interpretation"], interpretation)

    items: list[dict[str, Any]] = []
    base_entries: list[tuple[str, int]] = []
    notes: list[str] = []
    for part in (score_ducks_and_toys(sc, interp), score_rings(sc, interp), score_cups(sc, interp), score_poms(sc, interp)):
        items += part[0]
        base_entries += part[1]
    p_items, p_base, p_notes = score_platform(sc, interp)
    items += p_items
    base_entries += p_base
    notes += p_notes

    derived_base = sum(n for _, n in base_entries)
    base_count = derived_base if sc["base_eligible_count"] is None else sc["base_eligible_count"]
    base_note = "derived: " + ", ".join(f"{label} {n}" for label, n in base_entries if n)
    if sc["base_eligible_count"] is not None:
        base_note = f"judge-entered count overrides derived {derived_base} ({base_note})"
    items.insert(0, item("1. Base Score", "pieces touching board, off tape", base_count, PTS["base"], base_note))
    items.sort(key=lambda it: it["category"])

    subtotal = sum(it["subtotal"] for it in items)
    mult = score_multiplier(sc, interp)
    gate = None
    if sc["robot"]["disqualified"]:
        gate = "disqualified for the round (robot still driving/servoing at end)"
    elif not sc["robot"]["left_start_box"]:
        gate = "robot never left the Starting Box: score 0"
    ungated = subtotal * mult["multiplier"]
    return {
        "name": sc["name"], "description": sc["description"], "interpretation": interp,
        "items": items, "subtotal": subtotal, "multiplier": mult["multiplier"],
        "qualifying_zones": mult["qualifying_zones"], "multiplier_detail": mult["detail"],
        "gate": gate, "total": 0 if gate else ungated, "ungated_total": ungated, "notes": notes,
    }


def sensitivity(data: Mapping[str, Any]) -> list[tuple[str, Any]]:
    """Total under the default ruling, each single alternative ruling, and the all-conservative set."""
    label = "scenario's embedded rulings" if data.get("interpretation") else "default (official written rule)"
    rows: list[tuple[str, Any]] = [(label, score(data)["total"])]
    for key, (default, alternatives, _doc) in OPTIONS.items():
        for alt in alternatives:
            try:
                total = score(data, {key: alt})["total"]
            except ValueError as err:  # e.g. cap needs a per-bottle ring list
                rows.append((f"{key}={alt}", f"n/a ({err})"))
                continue
            rows.append((f"{key}={alt}", total))
    try:
        rows.append(("ALL conservative rulings", score(data, CONSERVATIVE_OPTIONS)["total"]))
    except ValueError as err:
        rows.append(("ALL conservative rulings", f"n/a ({err})"))
    return rows


# --------------------------------------------------------------------------------------
# Duck / multiplier maths
# --------------------------------------------------------------------------------------
def duck_zone_totals(subtotal_without_ducks: int, max_zones: int = MAX_MULTIPLIER) -> list[int]:
    """total(k) = (S + k) * max(1, k) for k = 0..max_zones qualifying duck zones (each duck also earns Base 1)."""
    return [(subtotal_without_ducks + k) * max(1, min(MAX_MULTIPLIER, k)) for k in range(max_zones + 1)]


def duck_zone_marginals(subtotal_without_ducks: int, max_zones: int = MAX_MULTIPLIER) -> list[int]:
    """Marginal value of the k-th qualifying duck zone, k = 1..max_zones. k=1 is only the duck's Base 1;
    k>=2 is S + 2k - 1 (so roughly one full subtotal per extra zone)."""
    totals = duck_zone_totals(subtotal_without_ducks, max_zones)
    return [totals[k] - totals[k - 1] for k in range(1, max_zones + 1)]


def best_duck_allocation(subtotal_without_ducks: int, interp: Mapping[str, Any] | None = None) -> dict[str, int]:
    """Best split of the 5 small ducks: k qualifying zones, u under the platform, rest off tape elsewhere.
    Ties go to the split with fewer qualifying zones."""
    cfg = resolve_interpretation(interp)
    max_zones = N_DUCKS if cfg["zone5_counts_for_multiplier"] else N_DUCKS - 1
    under_pts = PTS["duck_under_platform"] + (PTS["base"] if cfg["special_base_additive"] else 0)
    candidates = (
        {"zones": k, "under_platform": u, "elsewhere": N_DUCKS - k - u,
         "total": (subtotal_without_ducks + k * PTS["base"] + u * under_pts + (N_DUCKS - k - u) * PTS["base"]) * max(1, k)}
        for k in range(max_zones + 1)
        for u in range(N_DUCKS - k + 1)
    )
    return max(candidates, key=lambda c: c["total"])


# --------------------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------------------
def format_report(result: Mapping[str, Any]) -> str:
    lines = [f"Scenario: {result['name']}"]
    if result["description"]:
        lines.append(result["description"])
    lines.append("")
    lines.append(f"{'Item':<52}{'Count':>6}{'Pts':>6}{'Subtotal':>10}")
    for it in result["items"]:
        lines.append(f"{it['category'] + ' | ' + it['item']:<52.52}{it['count']:>6}{it['pts_each']:>6}{it['subtotal']:>10}")
        if it["note"]:
            lines.append(f"    note: {it['note']}")
    lines.append("-" * 74)
    lines.append(f"Round subtotal: {result['subtotal']}")
    zones = result["qualifying_zones"]
    lines.append(f"Multiplier: {result['multiplier']}x  (qualifying zones: {zones if zones else 'none'})")
    for z, d in result["multiplier_detail"].items():
        lines.append(f"    zone {z}: {'YES' if d['qualifies'] else 'no '} - {d['reason']}")
    for note in result["notes"]:
        lines.append(f"NOTE: {note}")
    if result["gate"]:
        lines.append(f"GATE: {result['gate']} (would have been {result['ungated_total']})")
    lines.append(f"TOTAL: {result['total']}")
    return "\n".join(lines)


def format_sensitivity(rows: list[tuple[str, Any]]) -> str:
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"{label:<{width}}  {total}" for label, total in rows)


def value_table_markdown() -> str:
    """Markdown tables: per-item values and the duck-zone maths. Used verbatim in docs/rules-digest.md."""
    rows = [
        ("Base, any piece on board off tape", 1, 1),
        ("Duck under platform", 3, 4),
        ("Pickleball under platform", 7, 8),
        ("Ring touching bottle (not neck)", 3, 4),
        ("Ring on neck (not touching board)", 15, 15),
        ("Cup flat/upright, on tape", 20, 20),
        ("Cup flat/upright, off tape", 20, 21),
        ("Cups nested (once)", 20, 20),
        ("Botguy on platform", 15, 15),
        ("Big Duck at Botguy's start", 15, 16),
        ("Mystery Red Pom alone on platform", 50, 50),
        ("Pom group of 5 (set or rainbow)", 25, 30),
    ]
    out = ["| Item | Written points | With Base | x2 | x3 | x4 | x5 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label, written, with_base in rows:
        out.append(f"| {label} | {written} | {with_base} | " + " | ".join(str(with_base * m) for m in (2, 3, 4, 5)) + " |")
    out += ["", "| Pom group (additive base) | Group score | + Base | Total |", "|---|---:|---:|---:|"]
    for label, n, pts in (("same color x1", 1, 1), ("same color x2", 2, 2), ("same color x3", 3, 3), ("same color x4", 4, 4),
                          ("complete set x5", 5, 25), ("all different x2", 2, 4), ("all different x3", 3, 9),
                          ("all different x4", 4, 16), ("all different x5", 5, 25), ("mixed, n poms (n=5 shown)", 5, 0)):
        out.append(f"| {label} | {pts} | {n} | {pts + n} |")
    sample = (0, 20, 40, 60, 100, 150, 200, 300)
    out += ["", "Marginal value of the k-th qualifying duck zone for a subtotal S (excluding the ducks' own Base):", "",
            "| S | k=1 | k=2 | k=3 | k=4 | k=5 | total at k=5 |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for s in sample:
        m = duck_zone_marginals(s)
        out.append(f"| {s} | " + " | ".join(f"+{v}" for v in m) + f" | {duck_zone_totals(s)[5]} |")
    out += ["", "Best use of the 5 small ducks for a subtotal S (before the ducks), default ruling:", "",
            "| S | qualifying zones | under platform | total |", "|---:|---:|---:|---:|"]
    for s in (0, 5, 10, 15, 20, 30, 50, 100):
        b = best_duck_allocation(s)
        out.append(f"| {s} | {b['zones']} | {b['under_platform']} | {b['total']} |")
    return "\n".join(out)


def list_options_text() -> str:
    lines = []
    for key, (default, alts, doc) in OPTIONS.items():
        lines.append(f"{key}  (default {default!r}; alternatives {list(alts)})\n    {doc}")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _parse_value(text: str) -> Any:
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("none", "null"):
        return None
    return int(text) if text.lstrip("-").isdigit() else text


def parse_set_args(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--set expects key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        out[key.strip()] = _parse_value(value.strip())
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score a 2026 Botball Fall Game scenario.")
    parser.add_argument("scenarios", nargs="*", help="scenario JSON file(s)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="interpretation override, e.g. zone5_counts_for_multiplier=false")
    parser.add_argument("--conservative", action="store_true", help="apply every lowest-scoring ruling")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--sensitivity", action="store_true", help="total under each single ambiguity ruling")
    parser.add_argument("--value-table", action="store_true", help="print the value tables and exit")
    parser.add_argument("--list-options", action="store_true", help="list interpretation switches and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_options:
        print(list_options_text())
        return 0
    if args.value_table:
        print(value_table_markdown())
        return 0
    if not args.scenarios:
        build_parser().error("give at least one scenario file (or --value-table / --list-options)")
    try:
        overrides = {**(CONSERVATIVE_OPTIONS if args.conservative else {}), **parse_set_args(args.set)}
        outputs = []
        for path in args.scenarios:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            result = score(data, overrides)
            if args.json:
                outputs.append(result)
            else:
                print(format_report(result))
                if args.sensitivity:
                    print("\nSensitivity (total under each ruling):")
                    print(format_sensitivity(sensitivity(data)))
                print()
        if args.json:
            print(json.dumps(outputs if len(outputs) != 1 else outputs[0], indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

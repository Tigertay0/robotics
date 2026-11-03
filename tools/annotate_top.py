#!/usr/bin/env python
"""Draw the field-map zones, start boxes, platform, entrance and key pieces over docs/renders/top_ortho.png.

Output: docs/renders/top_annotated.png  (same 2500 x 1300 px, 25 px per inch; px = (X+2)*25, py = 1300-(Y+2)*25).
All geometry comes from data/field_map.json, so rerun after tools/build_field_map.py.

Usage: python tools/annotate_top.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "renders" / "top_ortho.png"
OUT = ROOT / "docs" / "renders" / "top_annotated.png"
FM = ROOT / "data" / "field_map.json"

PX_PER_IN = 25
IMG_H = 1300
MARGIN_IN = 2


def P(x: float, y: float) -> tuple[float, float]:
    return (x + MARGIN_IN) * PX_PER_IN, IMG_H - (y + MARGIN_IN) * PX_PER_IN


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


COLORS = {
    "zone1": (239, 83, 80), "zone2": (255, 167, 38), "zone3": (205, 220, 57), "zone4": (38, 198, 164),
    "zone5": (66, 165, 245), "start_box": (171, 71, 188), "platform": (76, 175, 80), "enclosure": (63, 81, 181),
}


def main() -> None:
    fm = json.loads(FM.read_text())
    base = Image.open(SRC).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    def fill_poly(poly, color, alpha=105, outline_alpha=230, width=3):
        pts = [P(x, y) for x, y in poly]
        d.polygon(pts, fill=color + (alpha,))
        d.line(pts + [pts[0]], fill=color + (outline_alpha,), width=width)

    for zid, z in fm["zones"].items():
        fill_poly(z["polygon"], COLORS[zid])
    fill_poly(fm["start_box_small"]["polygon"], COLORS["start_box"], 120)
    fill_poly(fm["raised_platform"]["polygon"], COLORS["platform"], 90)
    fill_poly(fm["bottle_ring_enclosure"]["outer_polygon"], COLORS["enclosure"], 110)
    # Botguy strip outline
    sb = fm["botguy_strip"]["bbox"]
    fill_poly([[sb["x"][0], sb["y"][0]], [sb["x"][1], sb["y"][0]], [sb["x"][1], sb["y"][1]], [sb["x"][0], sb["y"][1]]],
              (120, 120, 120), 25, 160, 2)

    # entrance of the area under the platform
    ent = fm["under_platform"]["entrance"]
    y0, y1 = ent["floor_level_gap_between_floor_fittings_y"]
    xo = fm["under_platform"]["open_side"]["plane_x"]
    d.line([P(xo, y0), P(xo, y1)], fill=(255, 235, 59, 255), width=9)
    ny0, ny1 = ent["narrow_gap_between_top_elbows_y"]
    d.line([P(xo - 0.5, ny0), P(xo - 0.5, ny1)], fill=(255, 109, 0, 255), width=5)

    # tape rectangle outlines (thin white) so the exact strips are visible under the colour wash
    for t in fm["tape"]:
        r = t["rect"]
        d.rectangle([P(r["x"][0], r["y"][1]), P(r["x"][1], r["y"][0])], outline=(255, 255, 255, 200), width=2)

    # piece markers
    pieces = fm["pieces"]
    for c in pieces["cups"]:
        cx, cy = c["center_xy"]
        rad = c["mouth_diameter_in"] / 2 * PX_PER_IN
        px, py = P(cx, cy)
        d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=(255, 255, 0, 255), width=4)
    for p in pieces["pickleballs"]:
        px, py = P(p["center"][0], p["center"][1])
        rad = p["diameter_in"] / 2 * PX_PER_IN
        d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=(255, 255, 255, 255), width=3)
    bg = pieces["botguy"]["base_footprint"]
    d.rectangle([P(bg["x"][0], bg["y"][1]), P(bg["x"][1], bg["y"][0])], outline=(255, 255, 0, 255), width=3)
    bd = pieces["big_duck"]["box"]
    d.rectangle([P(bd["x"][0], bd["y"][1]), P(bd["x"][1], bd["y"][0])], outline=(255, 255, 0, 255), width=3)

    img = Image.alpha_composite(base, overlay)
    d = ImageDraw.Draw(img)

    def label(text, x, y, size=26, bold=False, anchor="mm", fg=(255, 255, 255), bg=(20, 20, 20, 205), pad=5):
        f = font(size, bold)
        px, py = P(x, y)
        l, t, r, b = d.textbbox((px, py), text, font=f, anchor=anchor)
        d.rounded_rectangle([l - pad, t - pad, r + pad, b + pad], radius=5, fill=bg)
        d.text((px, py), text, font=f, fill=fg, anchor=anchor)

    zl = {"zone1": "Zone 1", "zone2": "Zone 2", "zone3": "Zone 3", "zone4": "Zone 4"}
    for zid, name in zl.items():
        b = fm["zones"][zid]["bbox"]
        label(name, (b["x"][0] + b["x"][1]) / 2, (b["y"][0] + b["y"][1]) / 2 + (2.0 if zid in ("zone1", "zone2") else -3.0),
              44, True)
    label("Zone 5 / large Starting Box", 28.0, 9.9, 38, True)
    label("usable x 5.5-47.1, y 1.46-12.7 (41.6 x 11.25)", 28.0, 7.5, 24)
    label("Starting Box (small)", 59.56, 9.6, 36, True)
    label("21.125 x 11.25, ceiling 12 in", 59.56, 6.9, 26)
    label("centre (59.56, 7.09)", 59.56, 4.4, 24)
    label("Raised platform top Z 5.69", 87.0, 10.3, 28, True)
    label("area under it: 4.04 in clear", 87.0, 2.2, 26)
    label("Big Duck (start)", 76.0, 1.3, 24, anchor="mm")
    label("entrance x=72", 71.3, 3.0, 26, True, anchor="rm", fg=(255, 235, 59))
    label("9.25 in wide (y 1.63-10.88)", 71.3, 1.7, 22, anchor="rm", fg=(255, 235, 59))

    # enclosure and pieces
    label("Bottle/Ring enclosure", 6.5, 11.4, 26, True, anchor="lm")
    label("3 bottles (neck Z 3.8-4.95)", 6.5, 9.4, 22, anchor="lm")
    label("ring post L (3 rings)", 9.0, 30.0, 24)
    label("ring post B (3 rings)", 23.3, 3.4, 24)
    for p in pieces["pickleballs"]:
        cx, cy = p["center"][0], p["center"][1]
        if p["id"] == "pickleball4":
            label("PB4", cx - 4.0, cy + 2.6, 24, True, fg=(255, 170, 220))
            continue
        dy = 2.7
        dx = -2.6 if cx > 90 else 0.0
        label(p["id"].replace("pickleball", "PB"), cx + dx, cy + dy, 24, True, fg=(255, 170, 220))
    label("Cup 1 (CAD: red pom under)", 50.6, 16.7, 24, True, anchor="lm", fg=(255, 255, 0))
    label("Cup 2 (CAD: gold, green, purple, blue under)", 50.6, 30.3, 24, True, anchor="lm", fg=(255, 255, 0))
    names = {"red": "red", "green": "green", "lavender": "purple", "blue": "blue", "yellow": "yellow"}
    for dk in pieces["small_ducks"]:
        label(names[dk["color"]], dk["center_xy"][0], 24.2, 22)
    label("5 small ducks (start ON tape)", 70.7, 22.2, 26, True)
    for s in pieces["poms_visible_stacks"]:
        label({"gold": "gold", "turquoise": "blue", "lavender": "purple", "green": "green", "red": "red"}[s["cad_color"]],
              s["center_xy"][0], 24.2, 22)
    label("5 pom stacks (3+1, start ON tape)", 25.5, 22.2, 26, True)
    label("Botguy start", 43.4, 46.5, 28, True, anchor="rm", fg=(255, 255, 0))
    label("base 6.83 x 2.5, top Z 8.52", 43.4, 44.8, 22, anchor="rm")
    label("top PVC wall (y 41.66-42.96)", 14.0, 44.8, 22)

    # axes: tick every 10 in along bottom and left margin
    f = font(22)
    for x in range(0, 100, 10):
        px, py = P(x, 0)
        d.line([(px, py), (px, py + 14)], fill=(255, 255, 255, 255), width=2)
        d.text((px, py + 16), f"{x}", font=f, fill=(255, 255, 255), anchor="mt")
    for y in range(0, 50, 10):
        px, py = P(0, y)
        d.line([(px - 14, py), (px, py)], fill=(255, 255, 255, 255), width=2)
        d.text((px - 16, py), f"{y}", font=f, fill=(255, 255, 255), anchor="rm")
    label("inches: origin = bottom-left of board; X ->, Y up (Fall_Game_Table_Overhead.png orientation)", 1.0, 49.0, 22,
          anchor="lm", fg=(255, 255, 255), bg=(0, 0, 0, 160))
    label("yellow bar = under-platform entrance (floor level), orange = narrow part (Z 3.0-4.04)", 95.0, 49.0, 22,
          anchor="rm", fg=(255, 235, 59), bg=(0, 0, 0, 160))

    img.convert("RGB").save(OUT)
    print("wrote", OUT, img.size)


if __name__ == "__main__":
    main()

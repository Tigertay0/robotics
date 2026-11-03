"""Top-down debug plot of a match plan: python tools/match_plot.py [t0 t1] -> docs/animation/plan_debug.png"""
import math, os, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_plan
from match_sim import pose, rect_pts, interp_track

S = 14  # px per inch
W, H = int(96 * S), int(44 * S)


def P(x, y):
    return (x * S + 20, H - (y * S + 20))


def main():
    plan = match_plan.build()
    t0 = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    t1 = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    im = Image.new("RGB", (W + 40, H + 40), (245, 245, 240))
    d = ImageDraw.Draw(im, "RGBA")
    f = plan["meta"]["field"]
    for name, (x0, y0, x1, y1) in f["zones"].items():
        d.rectangle([P(x0, y1), P(x1, y0)], fill=(200, 220, 240, 70), outline=(150, 170, 190))
        d.text(P(x0 + 1, y1 - 1), name, fill=(80, 90, 110))
    for (x0, y0, x1, y1) in f["tape"].values():
        d.rectangle([P(x0, y1), P(x1, y0)], fill=(30, 30, 30, 200))
    d.rectangle([P(*f["raised_platform"][:2])[0], P(0, f["raised_platform"][3])[1], P(f["raised_platform"][2], 0)[0], P(0, f["raised_platform"][1])[1]], outline=(120, 80, 40), width=2)
    d.rectangle([P(0, 40.2), P(93.08, 0)], outline=(0, 0, 0), width=2)
    for s in plan["statics"]:
        if "r" in s:
            x, y, r = s["x"], s["y"], s["r"]
            d.ellipse([P(x - r, y + r), P(x + r, y - r)], outline=(120, 0, 120), width=2)
        else:
            x0, y0, x1, y1 = s["box"]
            d.rectangle([P(x0, y1), P(x1, y0)], outline=(120, 0, 120), width=2)
    cols = {"A": (0, 170, 200), "B": (230, 140, 0)}
    for name, r in plan["robots"].items():
        n = int((t1 - t0) / 1.0) + 1
        for i in range(n):
            t = t0 + i * 1.0
            x, y, h = pose(r["keys"], t)
            pts = [P(*p) for p in rect_pts(x, y, math.radians(h), *r["full"])]
            d.polygon(pts, outline=cols[name] + (120,))
            if i % 5 == 0:
                d.text(P(x, y), f"{name}{t:.0f}", fill=cols[name] + (255,))
    for pc in plan["pieces"]:
        for tt, c in ((t0, (0, 120, 0)), (t1, (200, 0, 0))):
            x, y = interp_track(pc["track"], tt)
            rr = pc["r"]
            d.ellipse([P(x - rr, y + rr), P(x + rr, y - rr)], outline=c, width=2)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "animation", "plan_debug.png")
    im.save(out)
    print(out)


if __name__ == "__main__":
    main()

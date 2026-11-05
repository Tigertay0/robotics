"""Check the build manual's fastener positions: python tools/check_fasteners.py [docs/manual/steps.json]

For every sub-step that lists both screws and nuts (8-32 and M3), each nut must sit on its
screw's axis, just past the screw tip, facing back along it. Reports the ones that do not.
The nut-less screws (servo horn screw, brass, caster, wheel, 2-56 mount screws) are skipped.
Exit code 1 if anything is reported.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "manual", "steps.json")
PAIRED = ("8-32", "Servo Horn Machine Screw")        # screw kinds that are fastened with a nut
AXIS_TOL = 1.6        # mm: nut centre off the screw axis
REACH_AFTER = 3.0     # ... or this far past it


def sub3(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    with open(PATH, encoding="utf-8") as f:
        steps = json.load(f)
    bad = []
    for rk in ("robot_a", "robot_b"):
        for st in steps[rk]["steps"]:
            targets = [(u["tag"], t) for u in st["subs"] for t in u["targets"]]
            screws = [(g, t) for g, t in targets if t["kind"] == "screw" and any(k in t["name"] for k in PAIRED)]
            nuts = [(g, t) for g, t in targets if t["kind"] == "nut" and any(k in t["name"] for k in ("8-32", "M3"))]
            if not nuts:                      # screws into standoffs / horns need no nut
                continue
            free = list(nuts)
            for g, sc in screws:
                best = None
                for item in free:
                    n = item[1]
                    rel = sub3(n["at"], sc["at"])
                    along = dot(rel, sc["dir"])
                    perp = math.sqrt(max(0.0, dot(rel, rel) - along * along))
                    if (perp <= AXIS_TOL and 0.5 <= along <= sc["len_mm"] + REACH_AFTER
                            and dot(n["dir"], sc["dir"]) < -0.9):
                        best = item
                        break
                if best is not None:
                    free.remove(best)
                    continue
                near = min((i[1] for i in free), key=lambda n: math.dist(n["at"], sc["at"]), default=None)
                extra = ""
                if near is not None:
                    rel = sub3(near["at"], sc["at"])
                    along = dot(rel, sc["dir"])
                    perp = math.sqrt(max(0.0, dot(rel, rel) - along * along))
                    extra = f" | nearest nut {perp:.1f} mm off axis, {along:.1f} mm along (screw {sc['len_mm']} mm)"
                bad.append(f"{rk} {g} {sc['name']} at {sc['at']}: no nut on its axis{extra}")
            bad += [f"{rk} {g} nut at {n['at']}: no screw" for g, n in free]
    for b in bad:
        print(b)
    print(f"{len(bad)} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

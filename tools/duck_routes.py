"""Straight-line distance each small duck must travel to rest fully inside each numbered zone.

Target point = the nearest point of the zone rectangle shrunk by MARGIN on every side (duck half-length 1.14 in plus
0.06 in slack), so the duck is clear of tape and PVC. Zone 5 uses the usable robot-start rectangle (X 5.5 to 47.125),
i.e. the L-shape minus the enclosure. Geometry: docs/field-map.md sections 2-3. Derived numbers, not measurements.

    python tools/duck_routes.py
"""
import math

MARGIN = 1.2
ZONES = {
    "Z1": (1.462, 27.838, 47.125, 41.662),
    "Z2": (49.000, 27.838, 94.538, 41.662),
    "Z3": (1.462, 14.588, 47.125, 25.963),
    "Z4": (49.000, 14.588, 94.538, 25.963),
    "Z5": (5.500, 1.462, 47.125, 12.713),
}
DUCKS = {"red": 54.68, "green": 62.68, "lavender": 70.68, "blue": 78.68, "yellow": 86.68}
DUCK_Y = 26.90


def travel(x: float, y: float, rect: tuple) -> float:
    x0, y0, x1, y1 = rect
    tx = min(max(x, x0 + MARGIN), x1 - MARGIN)
    ty = min(max(y, y0 + MARGIN), y1 - MARGIN)
    return math.hypot(tx - x, ty - y)


def main() -> None:
    print("| duck | " + " | ".join(ZONES) + " |")
    print("|---|" + "---:|" * len(ZONES))
    for name, x in DUCKS.items():
        cells = [f"{travel(x, DUCK_Y, r):.1f}" for r in ZONES.values()]
        print(f"| {name} (X {x}) | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()

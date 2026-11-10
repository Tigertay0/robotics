# Team hardware — confirmed by the team (2026-10-20)

Source: team member, from memory ("I think") — verify by physical count.

| Robot | Controller | DC motors | Notes |
|---|---|---|---|
| Robot A (mecanum) | 1 Wombat | 4 drive (one per mecanum wheel) + 1 arm motor = **5** | Wombat has only 4 motor ports (0-3) — see conflict below |
| Robot B | 1 Wombat | **2** (drive) | Differential drive |

Total: 7 DC motors, 2 Wombats, 5 standard servos + 2 micro (9 g) servos.

## Conflict to resolve
A Wombat drives at most 4 DC motors. Robot A cannot run 4 mecanum motors + 1 arm motor on one controller.
Options (rules allow 2 controllers on one robot, but we only have 2 Wombats and Robot B needs one):
1. Robot A: mecanum drive on motor ports 0-3, arm on a **servo** (arm motor goes to Robot B as a 3rd motor for its lift).
2. Robot A: 2-motor drive (diagonal or front pair) + arm motor — loses mecanum strafing.
Recommended: option 1.

## Measured game pieces

| Piece | Measured (Nov 10, 2026) | Was assumed |
|---|---|---|
| Small duck | **60 × 60 mm, 53 mm tall** | 58 × 37 × 37 mm (game documents) |

Used by `tools/blender/parts/p1_chassis_a.py` (`DUCK_W`, `DUCK_H`) and `tools/match_plan.py` (`R_DUCK`, `H_DUCK`, lane pitch).

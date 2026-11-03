# Parts — Blender CLI part generator

> **The team's print plan is [3D_PRINTS.md](../3D_PRINTS.md).** This file documents `tools/blender/build_parts.py`: parametric part scripts plus an automatic check against KIPR's size classes (watertight, one piece, ≥ 1 mm margin, 1/2/6 budget). The parts below go with the alternative plan in [strategy-alt.md](strategy-alt.md); the same library (`tools/blender/partlib.py`) can generate the parts listed in 3D_PRINTS.md.

Every printed part is a parametric Blender Python script. One command rebuilds all of them, checks each STL is watertight, checks the KIPR print-size classes, and writes previews:

```bash
python tools/blender/build_parts.py
```

Output: `parts/out/<part>.stl` (mm, ready for the slicer), `<part>.png` / `_top.png` / `_under.png` previews, `<part>.json` reports and `budget.md`. The build fails if a part is not watertight, is in more than one piece, has under 1 mm margin, or breaks the 1/2/6 budget. A single part: `blender -b --factory-startup --python tools/blender/parts/duck_cage.py -- --out parts/out`.

**Before printing anything:** the sizes in the scripts come from KIPR's CAD model of the table, not from real pieces (the team does not have the 2026 pieces yet). Measure the real duck, pom, servo, horn, top-hat, light sensor, tee socket and ring, edit the `MEASURE` constants at the top of each script, and re-run.

## Print budget (rules p.12) — all 9 slots used, all pass

Each part is sized to fit the class box **as written in millimetres** (small 60×60×20, mid 220×220×80, large 220×220×250), so it passes under every reading of the whole-inch rounding rule (see rules-digest §3D Print Rules). PLA or PETG, **grayscale only**, STL of each part submitted before the event.

| Slot | Part | Robot | Size (mm) | Job |
|---|---|---|---|---|
| L1 | `claw_palm` | B | 91 × 192 × 44 | Palm plate + fixed jaw (grip ribs, pom notch) + inverted claw-servo pocket + wrist-servo horn hub |
| M1 | `duck_cage` | A | 127 × 197 × 54 | Floorless 3-slot duck cage: 120 mm funnel → 66 mm channel, three gate axle holes, LEGO-pitch rails and rear mounting grid |
| M2 | `claw_jaw` | B | 34 × 145 × 28 | Moving jaw screwed to the stock round horn (no printed splines), grip ribs, pom notch |
| S1 | `camera_mount` | B | 58 × 31 × 19 | L-bracket for the Logitech camera clip + rubber-band hooks |
| S2, S3 | `tophat_bracket` ×2 | A, B | 58 × 24 × 6 | Two top-hat bores 30 mm apart (both over the 47.6 mm tape when centred) |
| S4, S5 | `light_shroud` ×2 | A, B | 38 × 26 × 18 | Start-light sensor hood (must stay inside the Starting Box) |
| S6 | `ring_fork` | B | 58 × 58 × 4 | **Stretch (Tier 3)**: tines slide beside the post's tee socket under the 3 rings |

If S6 is never used, that slot can go to a spare tophat bracket or a duck-cage gate flap.

### How the key parts work

**Duck cage (M1, Robot A).** Mounted on the mecanum robot's front, wall bottoms ~2 mm above the floor. Gate flaps are LEGO beams on cross axles through the three axle holes, each turned by a servo bolted to the top rails (micro servos fit; use kit servo brackets). Capture: open the gates → drive onto a duck → it slides back until the first closed gate → close the gate behind it. Release: open the front-most closed gate and back away; the duck stays on the floor because the cage has no floor. The closed front flap doubles as a pusher (yellow duck → Zone 2). Print upside down (rails on the bed); no supports.

**Claw (L1 + M2, Robot B).** Standard servo upside-down on the palm plate, horn below, moving jaw screwed to the horn. Jaws grip in one horizontal plane 2–30 mm above the floor, so the claw can sit on the FRP to pick a pom. Range of the moving jaw: pom 38 mm (~10° inward), Botguy 63.5 mm (~0°), cup ≈ 79 mm (~−8°), Big Duck ≈ 121 mm (~−33°). The rear hub bolts to the **wrist servo** (roll axis = claw axis): that 180° roll flips Cup 1 upright. The wrist servo rides on the end of the lift.

## Kit-built mechanisms (no print slot)

| Mechanism | Robot | Build from | Notes |
|---|---|---|---|
| Mecanum chassis | A | KIPR metal chassis + 4 mecanum wheels/motors | Keep ≤ 10" wide (gap between the cups is 9.7"). Gyro heading hold while strafing. |
| Differential chassis | B | KIPR metal + 2 Solarbotics wheels + caster | 2 drive motors + the arm motor (moved from Robot A). |
| Parallel 4-bar lift | B | KIPR metal straps (bending straps/plates is allowed; brackets are not) | Arm motor with back-EMF position control (`mrp`). Claw height 0.5"–11", reach ≥ 3" past the front bumper: clears the 1.46" top pipe for Botguy and the 5.69" platform. |
| PB4 plow | B | One letter sheet of corrugated plastic (black/white) | V-shape at Z ≈ 3" to knock the pickleball off its socket, then herd it into the 9.25"-wide platform entrance. |
| Rear push bumper | A | KIPR metal plate | Pushes the blue duck south into Zone 4. |
| Gate flaps | A | LEGO beams on cross axles | 40 mm long so they swing clear above a 37 mm duck. |
| Top-hat / camera / light wiring | both | kit cables only | No wire extensions beyond the kit (rules). |

Kit limits to respect: 5 structural zip ties (unlimited for wiring), 10 rubber bands, 10 paper clips, 100 cm string, one letter sheet each of paper / foam board / corrugated plastic, no hot glue, LEGO unmodified.

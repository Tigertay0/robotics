# 2026 Botball Fall Game: Strategy v2

Team Rochambotics. Written against **Botball_Fall_Game_Rule_Summary.pdf (v1.0)**, the
scoresheet, the 2026 kit part lists and the official **Fall_Game_Table.glb**. Replaces the
earlier `strategy` file and `STRATEGY_REVISED.md`; what changed is listed at the end.

Coordinates: inches, origin at the inside corner of the bottom-left PVC, x along the long
side, y toward Botguy. The 3D model and animation in `blender/` use the same frame.

## 1. What the rules actually say (the parts that decide the plan)

| Topic | Rule | Consequence |
|---|---|---|
| Multiplier | Each of the **5 numbered zones** with **exactly one small duck** adds +1; total score = subtotal × (1 to 5). Zone 5 (bottom-left) is the large start box and **does count**; the small start box, platform, under-platform and bottle enclosure don't. | Ducks first, everything else second. Zones: 1 TL, 2 TR, 3 ML ("pom side"), 4 MR ("duck side"), 5 BL. |
| Ducks | 5 small ducks start on the centre lane (right half). 1 pt base; 3 pts under the platform (bait, ignore). | A single line-follow east collects all 5. |
| Poms | **20 visible** = 5 colours × 4, as stacks of 3+1 on the centre lane (left half). **5 hidden** under the cups: 2 under the upper cup, 3 under the lower cup (one is the **red mystery pom**). | 25 poms total. |
| Pom scoring, per *group* in a numbered zone | same colour 1-4 poms: 1-4 pts; **complete set** (all 5 of a colour, alone): 25; all different colours, n poms: n²; any mix with a duplicate: base only. Base 1 pt per pom off tape is additive. | A stack of 4 pushed into a zone as its own group = 4 + 4 = **8**. Fifteen poms swept into one mixed pile = 15. So push stacks **individually**, don't sweep. |
| Red pom | Only pom on the platform → **50**, multiplied. Big duck/Botguy on the platform don't void it. It starts under the **lower** cup (the one nearest the start box) with 2 other poms. | 50 × 5 = 250 pts for one object: worth a dedicated mechanism. |
| Cups | Upright on its base: **20 each** (even on tape). Nested: **20**. Both nested and upright: 60. Off tape: +1 base. | Flip both = 40. Nesting is a +20 stretch. |
| Pickleballs | 4, on posts on the PVC; **7 each** under the platform. | +8 each with base. |
| Rings | 6 (3 per post); on a bottle neck **15**, touching 3. | Richest stretch (6 × 16 = 96 base) and **tiebreaker #1**, but needs a lift. |
| Botguy / big duck | 15 each (Botguy on platform; big duck at Botguy's start). | Low priority. |
| Robots | A robot = Wombat + ≥2 motors, must leave the start box. Each robot must fit **11.25 × 21.125 × 12 in**; both start in the small box, or one in the small box and one in zone 5. Max 4 independent structures. Robot-to-robot IR allowed. | Robot A in zone 5, Robot B in the small box (plan v3, section 4). |
| Match | 120 s, start on light, lights off at 5 s, **motors and servos must stop by 120 s** or DQ. Seeding = best 2 of 3 runs averaged; DE is scored on your own board (no opponent on the table). | No defence needed. Hard stop at 118 s in code. |
| Kit | 8 gear motors, 5 servos, 2 micro servos, 2 Wombats, 4 mecanum + 4 Solarbotics wheels, 2 casters, 2 chassis, 1 camera, 2 ET, 4+2 tophat, 3 light, 2 lever, 4+6 touch. Metal can't be cut (straps/plates may bend). 3D prints allowed (PLA/PETG, grayscale, STL submitted in advance). | Everything below uses kit parts only. |

## 2. Robot roles

**Robot A, "Duck Runner"** (mecanum, 4 motors, 1 Wombat). A raised chassis with an open-bottom
duck lane running under the robot (12" long, 68 mm wide: ducks measure 60 × 60 × 53 mm). Three servo flaps: intake (front),
pin (one duck from the rear), exit (rear). It line-follows the centre lane, swallows all 5 ducks,
then visits the 5 zones and releases exactly one duck in each. It never touches anything else.

**Robot B, "Point Scorer"** (servo demobot + paralleling arm, 2 motors, 1 Wombat, camera).
Front V-plow (two bent 4×12 plates), a side hook for flipping cups, and the arm/claw for the red
pom. Does cups, pom stacks, the red pom and the near pickleball.

## 3. Score

| Item | Base pts | Who | When |
|---|---|---|---|
Plan v3 (section 4) times:

| Item | Base pts | Who | When |
|---|---|---|---|
| 5 ducks in 5 zones (base 1 each) | 5 | A | 25-71 s |
| Lower cup upright, off tape | 21 | B | 6 s |
| 5 pom stacks pushed into zone 1 as 5 same-colour groups (A pushes the red one) | 40 | A + B | 17-50 s |
| Red pom alone on the platform | 51 | B | 62 s |
| Pickleball 1 (bottom wall) under the platform | 8 | B | 60 s |
| **Core subtotal** | **125** | | |

| Outcome | Subtotal | × | Score |
|---|---|---|---|
| Everything lands | 125 | 5 | **625** |
| Red pom missed | 74 | 5 | 370 |
| Red pom missed, 4 ducks | 74 | 4 | 296 |
| 3 ducks, no red pom | 74 | 3 | 222 |
| Old strategy's best case for comparison | 78 | 5 | 390 |

The earlier timeline also flipped the **upper cup** (+21, so 730 total), but its route had B
crossing the red duck and the two robots meeting at the lower cup. In plan v3, A pushes the
upper cup out of the lane upside down; it ends on the centre tape and scores nothing.

Stretch goals, in order of value per second (all ×5): **flip the upper cup with B after 62 s**
(+21 = +105, B and A are both done by 72 s), rings on bottle necks (+16 base each), nesting the
cups (+20), pickleball 2 on the right wall (+8), complete pom sets by adding the freed hidden pom
of the same colour (+22 per colour), Botguy on platform (+15), big duck at Botguy's start (+15).

## 4. Timeline: plan v3 (both robots, collision-checked by `tools/match_sim.py`)

The routes live in `tools/match_plan.py` and the code in `code/robot_*/main.c` follows them
move for move. Frame: inches from the inside corner of the bottom-left PVC. Robot A starts in
**zone 5** (large box) at (28.5, 5.7) facing east; Robot B starts in the **small box** at
(63.8, 7.15) facing west. The robots don't talk to each other: the 4 hand-offs are fixed times
(`wait_until_s`), each padded past the moment the simulator says it is safe.

| Time | Robot A, Duck Runner | Robot B, Point Scorer |
|---|---|---|
| 0-3 | North out of zone 5, then west to (14.3, 17.9): out of B's way | Hook down; drags the upside-down lower cup west along the lower tape |
| 3-12 | Waits (**hand-off 12 s**) | 6 s: pivots 20°, the cup rolls upright off the tape at (27, 8.9) in zone 5, its 3 poms spill; 7-10 s: grabs the red pom with the camera + claw |
| 12-17 | East under the red stack, side-pushes the red stack + upper cup north into zone 1 | Waits holding the red pom (**hand-off 26 s**) |
| 17-24 | Line-follows east, swallowing red, green, lavender, blue, yellow | same |
| 24-36 | Drops: zone 2 (70.6, 33), zone 4 (72.1, 17.6), zone 1 (44, 28.2). The lane is first in, first out | 27-50: pushes the green, lavender, turquoise and gold stacks north into zone 1 |
| 36-60 | Waits at (52.6, 21) (**hand-off 60 s**) | 51-57: east along zone 3, arcs down to the bottom wall east of the cup |
| 57-62 | same | Hook knocks pickleball 1 off its post, the plow pushes it under the platform; red pom on the platform, stops at 62 s |
| 60-72 | West through zone 3; waits (**hand-off 66 s**); drops in zone 5 (33.2, 6.8) and zone 3 (35.7, 21), stops at 72 s | Stopped |

Checks the simulator runs every 0.05 s (`python tools/match_sim.py` must print NO CONTACTS):
- both robots' true footprints never come within 0.25" of each other;
- no robot touches a wall, the platform, a post, or any piece outside a declared push/grab window;
- B touches no duck at any time;
- every duck lands alone in its own zone, off tape.

`docs/animation/match_data.json` (`--export`) feeds the "How our robots think" video.

## 5. Failure plans

- **A fails:** B finishes its list, then pushes the red duck (x ≈ 54) south into zone 4 and the
  yellow duck (x ≈ 86) north into zone 2: 2 zones → ×2. 95 → 190.
- **B fails:** A finishes the ducks (×5 on 5 pts = 25) and, with its remaining 6 s, nothing
  else. Robot A's 13 s idle start is the place to add a cheap task later.
- **Red pom grab fails:** B skips the platform and does pickleball 2 instead (+8).
- **A duck double-drops in a zone:** that zone counts 0; the escapement timing is the single
  most valuable thing to test. Target: 50 drops in a row without a double.

## 6. Build notes (kit parts only)

> Superseded for the actual build by [docs/BUILD.md](docs/BUILD.md) and the step-by-step manual
> (`docs/manual/`): Robot A now uses printed chassis p1, Robot B the claw jaw, pocket plow and
> cup hook prints (4 prints total, see [3D_PRINTS.md](3D_PRINTS.md)). The notes below are the
> original all-metal design.

Robot A: chassis, 4 gear motors in 4 servo brackets dropped on 2" standoffs so the chassis
floor sits 3" up, 4 mecanum wheels, 4 × Plate 4×12 on edge as lane walls (two per side,
joined with Strap 1×10), 2 × Channel 3×8 cross-members, 2 servos + 1 micro servo with 1×5 servo
horns as the flaps, 1 tophat (tape edge), 1 light sensor (start), 1 touch (lane full), ET
rangefinder (wall distance before drops), Wombat + battery on the chassis.
Size 12.5 × 10 × 7 in.

Robot B: base demobot (chassis, 2 motors, 2 Solarbotics wheels, caster) + servo demobot arm
with the paralleling-arm extension and the claw, 2 × Plate 4×12 bent into a V plow on the
front, 1 servo with a bent Strap 1×19 as the cup hook on the right side, camera on a Channel
3×12 mast, 2 tophats, 1 light sensor, 1 lever switch bumper, Wombat + battery.
Size 10 × 8 × 11 in (mast folded for the start-box height limit).

Servos used: A 2 + B 2 = 4 of 5; micro servos A 1 + B 1 = 2 of 2; motors 4 + 2 = 6 of 8.

## 7. What changed since the first strategy

1. Zone 5 (bottom-left) is a scoring zone and the large start box; the small box next to the
   platform is not a zone. Robot B now starts in zone 5.
2. There are 20 visible poms (stacks of 4), not 15, and pom groups score per group, so the
   stacks are pushed one by one into zone 1 (40 pts) instead of being swept into one pile (15).
3. The red pom is under the lower cup; freeing it and placing it alone on the platform is worth
   250 pts and is now in the core plan, done last so a failure costs nothing else.
4. Cups: nesting is worth +20 after all (rules allow nested + upright = 60). Kept as a stretch.
5. The platform top is ~6.5" high (from the GLB), cups are 5.1" wide and 5.9" tall, ducks 2.25"
   long: the lane, hook and arm were resized.
6. Pickleball 2 dropped from the core plan: B runs out of time. First stretch item.
7. The old "53 pts/s" and "singles pom zone" ideas are gone (they were based on misread
   drawings).
8. Plan v3 (Nov 3, 2026): the start boxes are swapped (A in zone 5, B in the small box). B's
   first run is the lower cup + red pom, entirely south of the duck lane, so it can never hit a
   duck; A pushes the red stack and the upper cup out of the lane itself. The upper cup stays
   upside down in zone 1 (no flip bonus) — its flip is a stretch item. The old timeline had B
   crossing the red duck and the robots meeting at the lower cup; the simulator now proves
   0 contacts. Everything ends by 72 s, leaving ~45 s of margin for slower real robots.

## 8. Code

`code/robot_a/main.c` and `code/robot_b/main.c` follow the plan v3 timeline move for move, with
the calibration numbers from last season. If you change a route, change `tools/match_plan.py`
first, run `python tools/match_sim.py`, then copy the distances and the `T_*` hand-off times into
the code. See `code/README.md`.

## 9. Open items

- Rules v1.0 says 2 + 3 hidden poms; the GLB shows 4 under the upper cup and 1 under the lower.
  Ask on the Discord FAQ which is right (it only changes how many loose poms B leaves behind).
- Last season's notes (`Botball robotics 2025_26 .pdf`) give the encoder constant (1870 ticks per
  wheel turn), 3" wheels on last year's robot, the servo positions of the arm and claw, the
  starting-light threshold (analog < 770) and the camera's red channel. They are used in `code/`.
  Still to measure: the mecanum and Solarbotics wheel diameters and the actual speed at 80% power,
  then update the per-segment times above.
- Submit the STL of any 3D-printed part before the tournament (none used so far).

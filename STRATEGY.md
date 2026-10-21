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
| Robots | A robot = Wombat + ≥2 motors, must leave the start box. Each robot must fit **11.25 × 21.125 × 12 in**; both start in the small box, or one in the small box and one in zone 5. Max 4 independent structures. Robot-to-robot IR allowed. | Robot A in the small box, Robot B in zone 5. |
| Match | 120 s, start on light, lights off at 5 s, **motors and servos must stop by 120 s** or DQ. Seeding = best 2 of 3 runs averaged; DE is scored on your own board (no opponent on the table). | No defence needed. Hard stop at 118 s in code. |
| Kit | 8 gear motors, 5 servos, 2 micro servos, 2 Wombats, 4 mecanum + 4 Solarbotics wheels, 2 casters, 2 chassis, 1 camera, 2 ET, 4+2 tophat, 3 light, 2 lever, 4+6 touch. Metal can't be cut (straps/plates may bend). 3D prints allowed (PLA/PETG, grayscale, STL submitted in advance). | Everything below uses kit parts only. |

## 2. Robot roles

**Robot A, "Duck Runner"** (mecanum, 4 motors, 1 Wombat). A raised chassis with an open-bottom
duck lane running under the robot (12.5" long, 1.8" wide). Three servo flaps: intake (front),
pin (one duck from the rear), exit (rear). It line-follows the centre lane, swallows all 5 ducks,
then visits the 5 zones and releases exactly one duck in each. It never touches anything else.

**Robot B, "Point Scorer"** (servo demobot + paralleling arm, 2 motors, 1 Wombat, camera).
Front V-plow (two bent 4×12 plates), a side hook for flipping cups, and the arm/claw for the red
pom. Does cups, pom stacks, the red pom and the near pickleball.

## 3. Score

| Item | Base pts | Who | When |
|---|---|---|---|
| 5 ducks in 5 zones (base 1 each) | 5 | A | 46-112 s |
| Upper cup upright, off tape | 21 | B | 11 s |
| Lower cup upright, off tape | 21 | B | 52 s |
| 5 pom stacks pushed into zone 1 as 5 same-colour groups | 40 | B | 58-82 s |
| Red pom alone on the platform | 51 | B | 110 s |
| Pickleball 1 (bottom wall) under the platform | 8 | B | 104 s |
| **Core subtotal** | **146** | | |

| Outcome | Subtotal | × | Score |
|---|---|---|---|
| Everything lands | 146 | 5 | **730** |
| Red pom missed | 95 | 5 | 475 |
| Red pom missed, 4 ducks | 95 | 4 | 380 |
| 3 ducks, no red pom | 95 | 3 | 285 |
| Old strategy's best case for comparison | 78 | 5 | 390 |

Stretch goals, in order of value per second (all ×5): rings on bottle necks (+16 base each),
nesting the cups (+20), pickleball 2 on the right wall (+8), complete pom sets by adding the
freed hidden pom of the same colour (+22 per colour), Botguy on platform (+15), big duck at
Botguy's start (+15). The animation leaves B parked at 110 s; ball 2 is the first thing to add.

## 4. Timeline (both robots, collision-checked in `blender/animate_strategy.py`)

Robot A starts in the small start box at (54.3, 5.6) facing east. Robot B starts in zone 5 at
(33, 5.6) facing east. Times are what the animation uses; measured speeds will shift them.

| Time | Robot A, Duck Runner | Robot B, Point Scorer |
|---|---|---|
| 0-16 | Waits: B must clear the upper cup from A's line-up spot first | Arcs north-east out of zone 5; the left plow wing flips the upper cup and pushes it to (59.5, 34) in zone 2 |
| 16-24 | North out of the box, lines up on the centre lane at x = 44 facing east | Loops down the east side to (68, 16), faces west, waits |
| 24-41 | Line-follows east, intake open; red, green, lavender, blue, yellow enter the lane | waits (A passes in front of it) |
| 41-51 | Zone 2: drop at (72, 34.5), creeps 1.5" forward | waits |
| 51-59 | Zone 4: drop at (73.6, 23.5), creeps forward | pushes the lower cup west with the right wing and hook (50-58): cup ends upright at (18.5, 7.3) in zone 5, the hidden poms spill |
| 59-74 | West along y = 17, holds at (56, 17) while B works | grabs the red pom with the claw (camera, 58-63) |
| 74-84 | West along y = 19.5; zone 3: drop at (26.5, 19.5), creeps forward | pushes the pom stacks north off the tape into zone 1, one at a time, east to west (66-86): x = 40, 32, 24, 16, 8 |
| 84-100 | East to x = 48, north up the centre column to y = 34.6, west; zone 1: drop at (26.5, 34.6), creeps forward | same |
| 100-117 | East to x = 48, south down the centre column to y = 5.6, west; zone 5: drop at (26.7, 5.6), creeps forward, stops | 86-97: back east along y = 14, down to the bottom wall; the hook knocks pickleball 1 off its post (96) |
| 117-120 | Stopped | 97-104: pushes the ball under the platform; 105-112: lifts the red pom onto the platform edge, stops |

Rules the routes obey: a robot never crosses a zone's duck drop point after that duck is down;
A always creeps **forward** after a drop (the lane opens at the rear); every pom group ends more
than 1" from tape; Robot B only turns in place where its 14" length has room (never within 11"
of a wall or the platform); both robots keep clear of each other at every frame (the script checks
footprints every 1/12 s and reports violations).

## 5. Failure plans

- **A fails:** B finishes its list, then pushes the red duck (x ≈ 54) south into zone 4 and the
  yellow duck (x ≈ 86) north into zone 2: 2 zones → ×2. 95 → 190.
- **B fails:** A finishes the ducks (×5 on 5 pts = 25) and, with its remaining 6 s, nothing
  else. Robot A's 13 s idle start is the place to add a cheap task later.
- **Red pom grab fails:** B skips the platform and does pickleball 2 instead (+8).
- **A duck double-drops in a zone:** that zone counts 0; the escapement timing is the single
  most valuable thing to test. Target: 50 drops in a row without a double.

## 6. Build notes (kit parts only)

Robot A: chassis raised to a 2.9" floor on four servo brackets hung from 1" standoffs, 4 gear
motors, 4 mecanum wheels, lane of 4 × Plate 4×12 on edge (two per side spliced with Strap 1×10)
held by the 2 angle brackets, 2 × Strap 1×10 flared as the funnel, 2 servos + 1 micro servo with
1×5 servo horns as the flaps, 2 tophats (tape edges), ET rangefinder, touch switch (lane full),
light sensor (start), Wombat + battery on the floor. Size 17.9 × 9.1 × 6.5 in. The printed lane
in `prints/` replaces the plates, straps and brackets.

Robot B: base demobot (chassis, 2 motors, 2 Solarbotics wheels, caster) + servo demobot shoulder
with the paralleling-arm extension and the liftarm claw (micro servo), 2 × Plate 4×12 bent into a
V plow on the front, 1 servo with a bent Strap 1×10 as the cup hook on the right side, camera on
a Channel 3×8 mast, 2 tophats, ET rangefinder, lever switch on the plow, light sensor, Wombat +
battery. Size 14.4 × 9.2 × 8.7 in.

Servos used: A 2 + B 2 = 4 of 5; micro servos A 1 + B 1 = 2 of 2; motors 4 + 2 = 6 of 8.
Step-by-step assembly with the 3D model: `guide/index.html`.

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

## 8. Code

`code/robot_a/main.c` and `code/robot_b/main.c` are first versions of both Wombat programs following
this timeline, with the calibration numbers from last season. See `code/README.md`.

## 9. Open items

- Rules v1.0 says 2 + 3 hidden poms; the GLB shows 4 under the upper cup and 1 under the lower.
  Ask on the Discord FAQ which is right (it only changes how many loose poms B leaves behind).
- Last season's notes (`Botball robotics 2025_26 .pdf`) give the encoder constant (1870 ticks per
  wheel turn), 3" wheels on last year's robot, the servo positions of the arm and claw, the
  starting-light threshold (analog < 770) and the camera's red channel. They are used in `code/`.
  Still to measure: the mecanum and Solarbotics wheel diameters and the actual speed at 80% power,
  then update the per-segment times above.
- Submit the STLs of the printed lane (`prints/out/`) before the tournament deadline.

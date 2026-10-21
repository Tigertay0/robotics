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

Robot A starts in the small start box at (53.3, 5.6) facing east. Robot B starts in zone 5 at
(40, 6) facing north.

| Time | Robot A, Duck Runner | Robot B, Point Scorer |
|---|---|---|
| 0-13 | Waits (B must clear the upper cup from A's line-up spot) | Drives north, then east to (48.5, 17.5) |
| 8-13 | | Flips the upper cup and pushes it north-east to (60, 34) in zone 2 |
| 13-21 | North out of the box, lines up on the centre lane at x = 44 facing east | Backs off to (66, 35) and waits for A to pass |
| 21-38 | Line-follows east, intake open; red, green, purple, blue, yellow enter the lane | |
| 38-48 | Zone 2 (TR): drop at (76, 34.5), then 4" forward | Drives south along x = 66 to the lower tape |
| 48-56 | Zone 4 (MR): drop at (76.7, 23.5), 4" forward | Heads west on the lower tape, flips the lower cup, pushes it to (20, 7) in zone 5; the 3 hidden poms spill with it |
| 56-71 | West along y = 17, holds at (56, 17) | Picks the red pom with the claw (camera) |
| 71-81 | West along y = 19.5; zone 3 (ML): drop at (28, 19.5), 4" forward | Pushes the pom stacks north off the tape into zone 1, one at a time, east to west: x = 41, 33, 25, 17, 9 |
| 81-97 | East to x = 48, north to y = 34.6, west; zone 1 (TL): drop at (28, 34.6), 4" forward | same |
| 97-112 | East to x = 48, south to y = 5.6, west; zone 5 (BL): drop at (28.2, 5.6), 4" forward, stop | 83-96: south at x = 30, east along the bottom wall; knocks pickleball 1 off its post |
| 112-120 | Stopped | 96-104: pushes the ball under the platform; 104-110: places the red pom on the platform, stops |

Rules the routes obey: a robot never crosses a zone's duck drop point after that duck is down;
A always moves **forward** after a drop (the lane opens at the rear); every pom group ends more
than 1" from tape; both robots keep ≥0.3" clearance from each other at every frame (the script
checks footprints every 1/12 s and reports violations).

## 5. Failure plans

- **A fails:** B finishes its list, then pushes the red duck (x ≈ 54) south into zone 4 and the
  yellow duck (x ≈ 86) north into zone 2: 2 zones → ×2. 95 → 190.
- **B fails:** A finishes the ducks (×5 on 5 pts = 25) and, with its remaining 6 s, nothing
  else. Robot A's 13 s idle start is the place to add a cheap task later.
- **Red pom grab fails:** B skips the platform and does pickleball 2 instead (+8).
- **A duck double-drops in a zone:** that zone counts 0; the escapement timing is the single
  most valuable thing to test. Target: 50 drops in a row without a double.

## 6. Build notes (kit parts only)

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

## 8. Open items

- Rules v1.0 says 2 + 3 hidden poms; the GLB shows 4 under the upper cup and 1 under the lower.
  Ask on the Discord FAQ which is right (it only changes how many loose poms B leaves behind).
- Exact mecanum wheel diameter and motor speed: measure, then update `WHEEL_D`/speeds in the
  scripts and the per-segment times above.
- Submit the STL of any 3D-printed part before the tournament (none used so far).

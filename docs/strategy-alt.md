# 2026 Botball Fall Game — Alternative strategy (analysis)

> **The team plan is [STRATEGY.md](../STRATEGY.md).** This is a second, independently derived plan kept for comparison and for its supporting analysis: the exact scorer (`tools/score.py`), the field map, the rules digest and the KIPR questions. Same robot split as STRATEGY.md; the main difference is Robot B's job list (this plan swaps Botguy and the Big Duck instead of pushing the pom stacks). Score any variant with `python tools/score.py <scenario.json>`.

Sources: [rules digest](rules-digest.md), [field map](field-map.md) (all coordinates below are inches in its frame: X 0–96 left→right, Y 0–48 bottom→top, see `docs/renders/top_annotated.png`), [hardware](hardware.md), [prior art](prior-art.md), [team hardware](team-hardware-confirmed.md). Scores computed with `tools/score.py` (default = written rules; "conservative" = every ambiguity ruled against us).

## 1. The one idea that wins this game

**Total = subtotal × (number of zones 1–5 holding exactly one small duck).** The multiplier goes up to ×5 and multiplies *everything*, including the 50-point Mystery Red Pom. Once the subtotal is more than ~8 points, every extra duck zone is worth about one whole subtotal. So:

1. **Five ducks, one per zone, placed well clear of tape, is the backbone of every run.** Nothing else comes close in points per second.
2. Then stack the **biggest subtotal items that sit next to our starting boxes**: Mystery Red Pom (50), Cup 1 flipped (20), pickleball PB4 (7+1), then the Botguy ↔ Big Duck swap (15 + 15+1).
3. Rings (15 each) are high value but the tolerance is brutal (ring ID 1.41" over a 1.30" bottle flange = 0.06"/side). They are **stretch only**.
4. Pom sorting is low value per second (a 4-stack in a zone = 4 + 4 base). Only do the one cheap push that falls on the Duck bot's route.

Seeding = average of the **best 2 of 3** runs, and seed rank is 75% of the seeding formula, so **consistency beats peak score**. Every step below is independent: if one fails, the robot moves on.

## 2. Score targets

| Tier | What | Subtotal | Total (written rules) | Total (all ambiguities against us) | Total if Zone 5 doesn't count |
|---|---|---:|---:|---:|---:|
| T0 floor | Ducks nudged into Z2 + Z4, PB4 under platform, Cup 1 flipped | 32 | **64** | 58 | 64 |
| T1 core | 5 ducks in 5 zones + PB4 + Cup 1 + Mystery Red Pom on platform | 85 | **425** | 328 | 340 |
| T2 full | T1 + Botguy→platform + Big Duck→Botguy start + red stack→Z1, green stack→Z3 | 131 | **655** | 480 | 524 |
| T3 stretch | T2 + Cup 2 flipped + 3 rings from post B on one bottle neck | 197 | **985** | 620 | 788 |

For comparison the scorer's hypothetical "strong team" scenario (no multiplier focus) is 456. T1 alone beats it. Scenario files: `data/scenarios/plan_t0_floor.json` … `plan_t3_stretch.json`.

## 3. Robots and roles

We have 2 Wombats and (per the team, to verify) 7 DC motors: 4 mecanum + 1 arm motor + 2 drive.

| | **Robot A — "Duck bot"** | **Robot B — "Lifter"** |
|---|---|---|
| Drive | Mecanum, 4 motors (all 4 motor ports) | 2-wheel differential + caster |
| Mechanism motors | none (port budget) | **arm motor moved here**: lift (4-bar) — 3 motors total |
| Servos | 3 gate servos on the duck cage (+1 spare) | claw, wrist (cup flip), +1 spare |
| Sensors | light (start), 2 top-hats (front), ET distance (side, for X), gyro | light, 2 top-hats, camera (red pom), ET, gyro |
| Starts in | **Small Starting Box** (X 49–70, Y 1.5–12.7), facing north | **Zone 5** right end (X ~35–47), facing east |
| Jobs | all 5 ducks; red pom stack → Z1 at the end | PB4, Cup 1, Mystery Red Pom, Botguy↔Big Duck swap |

Why this split: the ducks are straight north of the small box (red duck 14" above it); everything Robot B touches (PB4, Cup 1, the red pom, the platform, the Big Duck) is clustered around the box's west and east edges, which a robot in Zone 5's right end reaches without crossing the duck lane early. Robot A leaves the small box at t = 0, which frees it for Robot B's pickleball push. Both robots must fit 11.25" × 21.125" × 12" at the start; keep each robot ≤ 10" wide so it can pass the 9.7" gap between the cups.

## 4. Robot A — Duck bot run (≈ 75 s, 45 s margin)

Mechanism: a **floorless 3-slot duck cage** on the front (printed part M1, §7). Ducks enter broadside through a funnel; three servo gates (G0 front, G1, G2) split the channel into slots 1 (front) → 3 (back). Captured ducks slide on the floor inside the cage; opening a gate and backing away leaves that duck behind. The closed front gate is also a pusher; a flat rear bumper is the second pusher.

| # | t (s) | Action | End state |
|---|---|---|---|
| A1 | 0–4 | Wait for light, drive north out of the box at X 54.7 to Y ≈ 22; front top-hats stop on the lane tape edge (Y 25.96). | Robot in Z4 under the red duck |
| A2 | 4–9 | All three gates open. Drive north 2.5": **red** slides back to the cage's rear wall (slot 3). Close G2. Back 3". | red in slot 3 |
| A3 | 9–15 | Strafe east 8.0" (gyro heading hold, ET to right wall for X). Drive in: **green** stops against G2 (slot 2). Close G1. Back 3". | green in slot 2 |
| A4 | 15–21 | Strafe east 8.0" to X 70.7. Drive in: **lavender** stops against G1 (slot 1). Close G0. Back 3". | 3 ducks carried |
| A5 | 21–27 | Strafe east to X 86.7. Drive north 3.5" with the closed front: **yellow** pushed into **Z2** (ends ≈ Y 30.5). Back off. | Z2 ✓ |
| A6 | 27–37 | Strafe west to X 64, drive north through the now-empty lane into Z2 (Y ≈ 34), strafe east to X 78.7, **back up** 3.5" with the rear bumper: **blue** pushed into **Z4** (ends ≈ Y 23.4). | Z4 ✓ |
| A7 | 37–47 | North to Y 35, strafe west across the centre tape (clear of Cup 2, whose top edge is Y 29.4) to X 25. Open G0, back away south 3": lavender left in **Z1** at ≈ (25, 36). | Z1 ✓ |
| A8 | 47–62 | Back east to X 70 (Y 35), south through the empty lane to Y 20, strafe west across the centre tape at Y 20 (gap between the cups is Y 15.4–24.4; Cup 1 is normally gone by now) to X 25. Open G1, back away 3": green left in **Z3** at ≈ (25, 22). | Z3 ✓ |
| A9 | 62–72 | South across the lower tape to Y 7, open G2, back away: red left in **Z5** at ≈ (25, 9.5). | Z5 ✓ (if Zone 5 counts; else go to A9′) |
| A10 | 72–85 | Stretch: drive to (41.5, 19) and push the **red pom stack** north 3.5" into Z1 (+4 +4 base). Stop. | |
| — | 118 | `shut_down_in(118)` safety stop. | |

A9′ (if KIPR rules Zone 5 does **not** count): instead of Z5, carry the third duck to the under-platform opening (X 72, Y 6) — +3 +1 base, no multiplier change.

Placement rules for every duck: rest it **≥ 1.5" from any tape edge and PVC**, never in the small Starting Box, never two in one zone. Drop points above keep every duck ≥ 4" from tape.

## 5. Robot B — Lifter run (≈ 105 s)

Mechanism: motor-driven parallel 4-bar lift (KIPR metal, keeps the claw level; claw height 0.5"–11"), wrist servo (180° roll for the cup flip), wide-range claw: printed palm with a fixed jaw (L1) + servo-driven moving jaw (M2) with a pom notch near the tip, opening 0–5.2". Camera on a printed tilt mount (S1). Front plow for the pickleball = one sheet of corrugated plastic (allowed by the kit rules).

| # | t (s) | Action | Points |
|---|---|---|---|
| B1 | 0–12 | Wait 3 s (Robot A clears the box). Drive east 3": the plow at Z ≈ 3" knocks **PB4** off its socket at (48.1, 0.8) into the small box; keep driving east along Y ≈ 5 so the plow herds it 20" into the under-platform entrance (X 72, Y 1.6–10.9). Stop on the 12" tape (X 70.1). | 7 + 1 |
| B2 | 12–27 | Reverse to X ≈ 55, turn to face Cup 1 (48.0, 13.6). Claw at mid-height (Z ≈ 2.5", cup Ø ≈ 3.1" there), close, lift 3.5" (reveals the 3 hidden poms), wrist 180°, lower **upright** at (56, 4) (off tape), release. | 20 + 1 |
| B3 | 27–47 | Camera finds the **red** blob among the 3 poms at Cup 1's spot. Align, pick it with the jaw tips (pom notch), lift to Z 7", drive east, stop on the 12" tape, reach 3" over the platform, drop at ≈ (73.5, 11) — clear of the Big Duck. | **50** |
| B4 | 47–55 | Grab the **Big Duck** (X 72.6–77.5, Y 3.4–8.1) from the box side, back off, set it on the floor at (62, 5) inside the small box (not a zone, not the platform). | — |
| B5 | 55–75 | Drive north along X ≈ 58 (the duck lane there is empty after A2/A3) to the top wall, turn west, line up on the centre tape at X 48, face north. Lift to Z 2.5", reach 3" over the 1.46" top pipe, grip **Botguy** across his 2.5" thickness, lift to Z 7". | — |
| B6 | 75–92 | Back to the small box, face east on the 12" tape, place Botguy on the platform at ≈ (74, 3–9.8) (where the Big Duck was). | 15 |
| B7 | 92–112 | Pick the Big Duck from (62, 5), drive north again, place it over the top wall on **Botguy's start** (48, 44.25). | 15 + 1 |
| — | 118 | `shut_down_in(118)`. | |

Order is by risk: the cheap, near points (B1–B3 = 79 subtotal) are banked before the long trips. If B5 is not finished by t = 85, skip the swap and park.

## 6. Collision plan (no robot-to-robot comms needed)

- t 0–4: A leaves the small box northward; B waits 3 s before entering it.
- t 4–47: A works the duck lane and Z1/Z2 (north half); B stays in Y < 13 (south strip).
- t 47–62: A crosses the lane southbound at **X 70** and the centre tape at **Y 20**; B travels north at **X 58** around t 55–60 — 12" apart in X; B must be past Y 27 before A reaches Y 20 at X 70 (A reaches it ≈ t 52). Tune by adding waits; never by speeding up.
- t 62+: A is in Z3/Z5 (west of X 47); B uses X ≥ 48.

## 7. Parts to build and print

Print budget (rules p.12): 1 large (≤ 9×9×10 in), 2 mid (≤ 9×9×4 in), 6 small (≤ 3×3×1 in), PLA/PETG, grayscale, STL submitted before the event. Every printed part below is generated by a **Blender CLI** script in `tools/blender/parts/` (see [parts.md](parts.md)); each run writes the STL, a preview render and a print-class check.

> **Superseded (2026-11-03):** the team prints only 4 parts (see [3D_PRINTS.md](../3D_PRINTS.md)): Robot A's chassis with the duck lane built in, a print-in-place geared claw, a pocket plow and a cup hook. The 9-part list that used to be here (claw palm/jaw, duck cage, camera mount, sensor brackets, light shrouds, ring fork) was deleted from the repo.

Built from the kit (no print slot): mecanum chassis (KIPR metal), Robot B differential chassis, Robot B 4-bar lift (metal straps — bending straps/plates is allowed, brackets are not), rear push bumper (metal plate), PB4 plow (corrugated plastic, one letter sheet allowed), gate flaps (LEGO beams on servo horns).

## 8. Build and test schedule (event ≈ Dec 5, 2026 → ~6 weeks)

| Week | Goal | Exit test |
|---|---|---|
| 1 (Oct 20) | Count motors/sensors, buy 2026 practice pieces, build the practice table, send FAQ questions (§9), both chassis driving, light start + `shut_down_in` | Both robots start on light and stop by 118 s, 10/10 |
| 2 | Drive calibration (ticks/in, gyro scale), print M1 + tophat brackets, **T0** | T0 ≥ 8/10 runs |
| 3 | Duck cage gates + full duck route; print L1/M2 claw; B1–B3 | **T1** ≥ 6/10 |
| 4 | Lift + camera red-pom pick; B4–B7 swap | T2 attempted |
| 5 | Reliability only: run full matches, log every failure, fix the top one each day | T1 ≥ 9/10, T2 ≥ 5/10 |
| 6 | Freeze code, submit STLs, rehearse setup in 90 s, decide T3 go/no-go | 3 clean dress rehearsals |

## 9. Rule questions to send KIPR now (they change the plan)

Full list with wording: [rules-digest.md](rules-digest.md) §Ambiguities. The ones that matter most to this plan:

1. **Does Zone 5 (the larger Starting Box) count for the Overall Multiplier?** (p.3 vs p.6 conflict; −20% of our score if not → A9′ fallback.)
2. Does a duck touching tape count as "in" a zone (spoiling it)? — we avoid tape anyway.
3. Is the Big Duck a "duck" for the exactly-one test? — we never put it in a numbered zone (B4 parks it in the small box).
4. Exact footprint of "Botguy's starting position" for the Big Duck's 15.
5. 3D-print classes: whole-inch box per dimension (our reading) vs volume only; is the 6/2/1 budget per team?
6. Which two poms are under Cup 1 with the Mystery Red Pom (rules: 3 + 2; CAD model: 1 + 4) and which cup is green/teal.

## 10. Before anything else — verify physically

- **Motors**: the inventory lists none; team recalls 7. A Wombat drives only 4 → Robot A's arm motor goes to Robot B (§3).
- **Light sensors** (one per Wombat for the start light): not in the inventory; the 2026 kit ships 3.
- **2026 game pieces**: the "Parcour" bag is last year's game (pallets, foam, cones). We need small rubber ducks (~2.25"), a big duck (~5.3"), 4 pickleballs, 2 cups (mouth ≈ 3.6", 5.7" tall), 6 rings (ID ≈ 1.41"), 3 bottles, 25 poms (1.5", 5 colours), Botguy. Every printed part is parametric — re-run the Blender scripts with measured sizes before printing.
- Wombat case size + mass, wheel diameters, real servo torque (see hardware.md checklist).

# 2026 Botball Fall Game: rules digest, ambiguities, scoring maths

Everything a strategy or robot-design decision needs from the official documents, plus an exact scorer
([`tools/score.py`](../tools/score.py), tests in [`tools/test_score.py`](../tools/test_score.py), scenarios in
[`data/scenarios/`](../data/scenarios/)).

**Sources and tags**

| Cite | File |
|---|---|
| RS p.N | `docs/official/Botball_Fall_Game_Rule_Summary.txt` (the 14-page "2026 Botball Fall Game Review", v1.0; same content as the `.pdf`) |
| SS | `Botball_Fall_Seeding_Scoresheet.xlsx`, cell refs |
| TD sheet N | `Fall_Game_Table.pdf` (9 build sheets) |
| GLB | `Fall_Game_Table.glb`, read through `data/glb_objects_raw.json` |
| IMG | `docs/official/Fall_Game_Zones.png`, `Fall_Game_Table_Overhead.png` |
| LY | `docs/official/last-year/2025_Pallet_Pushers_Fall_Game_Review_v1.0.txt` (different game; precedent only) |
| INV | `Botball Inventory.xlsx` (team parts list, French labels) |

Tags: **[S]** stated in the official documents; **[I]** our inference or arithmetic; **[G]** measured from the GLB
(about 0.1 in; verify on the real table). Rule text is paraphrased, not copied.

Coordinates: team convention. Origin = bottom-left of the board in the overhead image, **X** along the 96 in length
(left to right), **Y** across the 48 in width (bottom to top), **Z** above the FRP surface. Inches.

---

## 0. One-screen summary

1. A run is **120 s**, single-sided. Three seeding runs; the **seed score is the average of the best two** [S, RS p.11].
2. Everything is multiplied: **total = round subtotal x multiplier**, where multiplier = number of numbered zones that
   hold **exactly one small duck**, clamped to 1..5 [S, RS p.6]. Zero or one qualifying zone = 1x.
3. The first qualifying duck zone adds nothing by itself; the k-th (k >= 2) adds about one full subtotal
   (`S + 2k - 1`) [I, section 5]. Once the rest of the subtotal is 8 or more, **all five ducks belong one per zone**
   (a duck under the platform is worth only 3, or 4 with Base) [I].
4. Biggest items: **Mystery Red Pom alone on the platform = 50 (multiplied)**; cups **flat/upright = 20 each even
   while touching tape** (flip them in place); Botguy on platform 15 and Big Duck at Botguy's start 15 (a swap);
   rings on a bottle neck 15 each (6 rings = 90); pickleballs under the platform 7 each (4 = 28); pom groups up to 25
   (+5 Base) in each of 5 zones.
5. **Black tape voids scoring** (cups' bonuses excepted). At the start every duck and every visible pom sits on the
   tape lane and both cups sit on tape crossings, so **almost nothing scores until it is moved clear of the tape**; the
   exceptions are the cup flips and Botguy's Base point [S + G].
6. Scoring is by **final position**, judged after everything stops moving [S, RS p.5, p.10].
7. Robot: Wombat only; each robot must fit **11.25 x 21.125 x 12 in** at the start; one robot can start in the small box
   and one in the large box (Zone 5); max **4 independent structures** on the table; a robot that never leaves its box
   scores 0; motors and servos must stop by 120 s or the round is disqualified [S, RS p.8-13].
8. 3D prints: PLA or PETG, grayscale, **6 small / 2 mid / 1 large**, size measured as a whole-inch bounding box
   (every dimension rounded **up** to the next inch), STL submitted in advance [S, RS p.12].
9. Largest unresolved questions (section 12): does **Zone 5** count for the multiplier; is Base **additive** with pom
   and special scores; are **several pom piles in one zone** separate groups; does a **duck touching tape** count in a zone.
10. Computed totals (default ruling = written rule): theoretical max **2050**; max if every ambiguity goes against us
    **1300**; ducks only (one per zone) **30**; hypothetical novice **86**; hypothetical strong **456** (section 5.4).
11. Inventory gap to check now: INV lists **no light sensor** and the "Parcour" items are last year's pieces (section 7.3).

---

## 1. Field and zones

### 1.1 Areas [S, RS p.3, p.7]

| Area | What the rules say |
|---|---|
| Zone 1 | top-left |
| Zone 2 | top-right |
| Zone 3 | middle-left ("pom side") |
| Zone 4 | middle-right ("duck side") |
| Zone 5 | lower-left; **doubles as the larger Starting Box** |
| Small Starting Box | 11.25 x 21.125 in, virtual height limit 12 in |
| Raised Platform | elevated scoring area for Botguy and the Mystery Red Pom; bounded by the corrugated-plastic edges |
| Area under the platform | separate scoring zone; pickleballs (7) and ducks (3) score here |
| Bottle/Ring enclosure | holds blue bottles; borders but is **not part of** Zone 5 |

Zones are bounded by the **inner edge of the black tape** and the vertical projection of any PVC border [S, RS p.7].
Excluded from the multiplier count by the list on RS p.3: the Starting Box, the platform, the area under it, the
enclosure. See ambiguity A1 for the Zone 5 conflict.

### 1.2 Measured layout [G]

Dimensioned geometry lives in [`docs/field-map.md`](field-map.md) (`data/field_map.json`, `tools/field_geom.py`); the numbers
below are the ones scoring depends on and agree with it. Source: `data/glb_objects_raw.json` and TD sheets 3-9.

| Feature | Position / size |
|---|---|
| Playing surface | FRP 4 x 8 ft, white, **bumpy side up**, on 3/8 in particle board; 1 in ID Sch-40 PVC border (1.3 in OD); 3M black duct tape, **1.875 in wide** (TD sheets 2-3) |
| Upper tape lane ("center lane") | Y 25.96-27.84, X 1.04-94.54; carries every duck and pom stack and the center crossing |
| Lower tape lane | Y 12.71-14.59, X 5.04-94.54 |
| Center vertical tape | X 47.13-49.0, Y 0.16-41.66 |
| Platform-side tape (12 in strip) | X 70.13-72.0, Y 0.71-12.71 |
| Zone 1 | X 1.46-47.13, Y 27.84-41.66 (45.7 x 13.8) |
| Zone 2 | X 49.0-94.54, Y 27.84-41.66 (45.5 x 13.8) |
| Zone 3 | X 1.46-47.13, Y 14.59-25.96 (45.7 x 11.4) |
| Zone 4 | X 49.0-94.54, Y 14.59-25.96 (45.5 x 11.4) |
| Zone 5 / large Starting Box | X 1.46-47.13, Y 1.46-12.71 minus the enclosure at its left end; usable start area about X 5.5-47.1 (41.6 x 11.25). The rules give no size for the large box |
| Small Starting Box | X 49.0-70.13, Y 1.46-12.71 = **21.13 x 11.25**, exactly the stated size |
| Bottle/Ring enclosure | PVC footprint X 0-5.5, Y 3.4-14.4; 3 bottles at X 2.9, Y 6.13 / 8.88 / 11.63 |
| Raised platform plate | X 72-96, Y 0-12.5; underside **5.50 in**, top 5.69 in; a 5.5 in skirt closes the field-facing (+Y) edge |
| Under-platform entrance | only the Start-Box side (X = 72), 1.875 in of tape beyond the box edge: **4.04 in clear height**; **9.25 in wide** below Z 3.0, **7.5 in wide** between Z 3.0 and 4.04 (corner elbows) |
| Under-platform floor | free board surface X 72.0-94.5, Y 1.6-10.9 (22.5 x 9.25), 1.46 in-high floor pipes along both long sides and the far end; no tape inside |
| Top PVC rail | Y 41.66-42.96; Botguy stands beyond it (outside zones 1 and 2) |

Game-piece spacing on the table drawing: pom stacks and ducks are each spaced **8.00 in** apart (TD sheet 9).

### 1.3 Start layout [G]

| Piece | Start position (X, Y) | Touching tape at start? |
|---|---|---|
| 5 small ducks | center lane Y 26.9; X = 54.68 red, 62.68 green, 70.68 purple, 78.68 blue, 86.68 yellow | **yes** (on the upper lane) |
| 5 visible pom stacks (3 + 1 on top) | center lane Y 26.9; X = 9.46 yellow, 17.46 blue, 25.46 purple, 33.46 green, 41.46 red | yes |
| Cup A (nearest the Start Box) | (48.02, 13.62), upside-down on the lower tape crossing | yes |
| Cup B | (48.05, 26.91), upside-down on the center crossing | yes |
| Botguy | base centre (48.0, 44.25) on the strip beyond the top rail; 6.8 x 2.5 in base, 8.5 in tall | no |
| Big Duck | (74.8, 5.75) on the platform; 5.3 x 4.8 x 4.5 in | n/a |
| Pickleballs (Ø 2.91 in) | on tee sockets: (57.06, 42.31), (67.94, 42.31), (95.19, 26.94), (48.06, 0.81) | on posts |
| Rings | 3 on post L (0.81, 26.94), 3 on post B (23.31, 0.81); OD 2.13, ID 1.41, 0.36 in thick, Z 2.46-3.54 | on posts |

Other sizes [G]: small duck 2.27 x 1.46 x 1.46 in; pom Ø 1.5 in; cup mouth Ø 3.63 in, base Ø about 2.5 in, height 5.70 in;
bottle body Ø 2.53 in, 4.95 in tall, neck about Ø 1.06 in from Z 3.8 to 4.95 (estimate from mesh slices).

**Model/text conflict (risk):** the GLB puts only the red pom under Cup A and four poms (yellow, green, purple, blue) under
Cup B; the rules say 3 under the cup nearest the Start Box (including the Mystery Red Pom) and 2 under the other
(RS p.4). The GLB cups are also black, while the rules call them green and teal. `docs/field-map.md` section 9 lists
the other model-versus-rules differences. Treat the GLB as an approximation.

---

## 2. Pieces [S, RS p.4-5, p.8]

| Piece | Count | Start | Scores |
|---|---:|---|---|
| Botguy | 1 | top center, far edge | on top of platform: 15 |
| Big Duck (larger than the small ducks) | 1 | on top of the platform | at Botguy's starting position: 15 |
| Rubber ducks (small) | 5 (5 colors) | center lane | Base 1; under platform 3; drive the multiplier |
| Poms, visible | 20 (5 colors x 4) | center lane, stacks of 3 + 1 on top | Base 1; pom group score |
| Poms, hidden | 5 (1 per color) | under the two upside-down cups | must be freed to join the sorts |
| Mystery Red Pom | 1 (one of the 5 hidden) | with two other poms under the cup closest to the Start Box | alone on platform: 50 (multiplied) |
| Cups | 2 (green, teal) | upside-down, hiding poms | nested 20; flat/upright 20 each; up to 60 |
| Blue bottles | not stated (3 in the GLB and IMG [I]) | enclosure | rings score onto them |
| Rings | 6 (3 per post, 2 posts) | posts | touching bottle 3; on neck 15 |
| Pickleballs | 4 | mounted on posts | under platform 7 each |

Every color has exactly 5 poms (4 visible + 1 hidden), so a "complete set" is unambiguous (RS p.5).
The five colors are not named in the rules; IMG and GLB show yellow, blue, purple, green, red (GLB names: gold,
turquoise, lavender). The scorer accepts either set of names.

---

## 3. Scoring rules

### 3.1 Foundational rules [S, RS p.5]

- **Black Tape Rule**: a piece touching black tape does not score. Cups are exempt **only** for their Nesting and
  Flat/Upright bonuses; a cup on tape still earns no Base.
- **General Scoring Rule**: a piece must touch the surface of the scoring area, except pieces scored under the Volume Rule.
- **Volume Rule** (rings on bottles only): for the 15-point level the bottle neck must break the ring's interior volume.
- **Highest Scoring Rule**: a piece scores in one scoring area only, as if in the highest-scoring area by base score
  without multipliers.
- **Robot Rule**: a robot = a KIPR controller with at least two motors connected, **that leaves the Starting Box**.
  Two controllers on one robot count as one robot.
- **Final Scoring Rule**: final location counts, not how it got there; judges wait until moving pieces stop.

### 3.2 Base Score [S, RS p.5; SS row 9]

Every scoring piece touching the board surface and not touching black tape scores 1. The text says this is **in addition
to** special scoring (additive, not exclusive). Whether that holds for poms and special items is ambiguity A4.

### 3.3 Poms [S, RS p.5-6; SS rows 22-26]

Applied per group of poms found together in one numbered zone:

| Group | Score (before Base) |
|---|---|
| Same color, 1-4 poms | 1, 2, 3 or 4 (linear) |
| All 5 of one color alone in the zone (Complete Set) | flat **25** |
| All different colors, no duplicates, n poms (n >= 2) | **n squared**: 2 poms = 4, 3 = 9, 4 = 16, 5 = 25 |
| Mixed (duplicates and uniques, neither sorted nor unique) | Base only, no bonus |

Ducks do not break a sort. The scoresheet formula per zone is `=IF(B=5,25,IF(B>=1,B,IF(C>=2,C^2,0)))` with B = "same-color
count" and C = "unique-color count" (see A8 for how it differs from the text).

**Mystery Red Pom** [S, RS p.6; SS row 18]: if the hidden red pom, and only that pom, ends up alone on top of the platform
it scores a flat **50, multiplied**. Any other pom on the platform voids it (so dumping all poms there does not work).

### 3.4 Ducks and the Overall Multiplier [S, RS p.6; SS rows 30-38]

- Small duck: Base 1 off tape; **3 under the platform**.
- Overall Multiplier: each numbered zone holding **exactly 1 duck** (no more, no fewer) adds +1 to one game-wide
  multiplier, max 5x, applied to the **whole subtotal including the Mystery Red Pom**. 0 or 1 qualifying zones = 1x.
- The small Starting Box, platform, area under the platform and the enclosure do not count (ambiguity A1 for Zone 5).
- The scoresheet says "exactly 1 **smaller** duck" (SS A30), i.e. the Big Duck does not count (A13).

### 3.5 Cups [S, RS p.6; SS rows 14-15]

| State | Points |
|---|---:|
| Touching tape, nothing special | 0 |
| Off tape on the board, nothing special | 1 (Base) |
| Nested (one inside the other's volume), regardless of tape | 20 |
| Flat/upright on the board (per cup), regardless of nesting or tape | 20 each |
| Nested and both flat/upright | 20 + 20 + 20 = 60 |

"Flat/upright" = resting with its bottom flat on the board. Both cups start upside-down, so each flip is worth 20.
The 60-point state looks physically impossible (A5).

### 3.6 Rings, pickleballs, Botguy, Big Duck [S, RS p.6; SS rows 10-17]

| Item | Points |
|---|---:|
| Ring touching a bottle, not on the neck | 3 |
| Ring on the bottle neck (neck breaks the ring's interior volume) | 15 |
| Pickleball under the Raised Platform | 7 each |
| Botguy on top of the Raised Platform | 15 |
| Big Duck at Botguy's starting position | 15 |

The two 15s need a swap: Botguy goes up onto the platform, the Big Duck comes off it to Botguy's old spot [I].

### 3.7 Worked examples (all produced by `tools/score.py`; default ruling, Botguy/Big Duck out of play unless stated)

| Situation | Calculation | Total |
|---|---|---:|
| 3 red poms alone in a zone, off tape | linear 3 + Base 3 | 6 (3 if Base is not additive) |
| 5 different colors in a zone | 25 + Base 5 | 30 |
| 5 yellow poms alone in a zone | 25 + Base 5 | 30 |
| 2 red + 1 blue in a zone | mixed: Base only | 3 |
| Mystery Red Pom alone on platform; 3 ducks in zones 1-3 | (50 + 3) x 3 | 159 |
| Both cups flipped upright, still on tape | 20 + 20, no Base | 40 (42 if off tape) |
| 4 duck zones + 1 pickleball under platform + 1 ring on a neck | (4 + 8 + 15) x 4 | 108 |
| 5 ducks, one per zone, Botguy untouched | (5 + 1 Botguy Base) x 5 | 30 |

### 3.8 Practical consequences [I]

- A pom resting **on** another pom (the 3 + 1 start stacks) does not touch the board, so the top pom earns nothing (A11).
- Ducks and poms start on tape: moving one fully clear of the 1.875 in tape is worth +1 (Base) before any bonus.
- Under the default reading (A3) a group of poms must be **alone in the zone** to be a sort; mixed leftovers dilute it. Ducks are harmless to it.
- The rainbow (5 different colors, 25) is as good as a color set (25) and needs one pom from each of the five stacks
  instead of emptying one color (the stacks are in a row on the lane) [I].

---

## 4. Scoresheet mapping (SS)

`E28 = SUM(E9:E18) + SUM(E22:E26)`; `B38 = MAX(1, MIN(5, SUM(B32:B36)))`; `E40 = E28 * B38`.

| Row | Item | Pts | Count rule |
|---|---|---:|---|
| 9 | Base: objects touching board, off black tape | 1 | judge's count |
| 10 | Pickleballs under platform | 7 | count |
| 11 | Rings touching bottle, not on neck | 3 | count |
| 12 | Rings on bottle neck | 15 | count |
| 13 | Ducks under platform | 3 | count |
| 14 | Cups nested | 20 | 1 or 0 |
| 15 | Cups flat/upright | 20 | 0-2 |
| 16 | Botguy on platform | 15 | 1 or 0 |
| 17 | Big Duck at Botguy's start | 15 | 1 or 0 |
| 18 | Mystery Red Pom alone on platform | 50 | 1 or 0 |
| 22-26 | Pom bonus per zone 1-5 | formula above | B in 0-5, C in 0-5 |
| 32-36 | Zone has exactly 1 duck? | +1 each | 1 or 0 |

`tools/test_score.py` re-reads these formulas from the xlsx and fails if they change.

---

## 5. Value table

### 5.1 Points per item, before and after the multiplier

Tables 5.1 and 5.2 are the output of `python tools/score.py --value-table` (default ruling: Base additive, platform not
board surface); 5.3 lists the thresholds found with `best_duck_allocation`. "With Base" adds the 1-point Base where the
item touches the board off tape; the multiplier columns multiply the with-Base value. `test_score.py` checks the rows
against the scorer.

| Item | Written points | With Base | x2 | x3 | x4 | x5 |
|---|---:|---:|---:|---:|---:|---:|
| Base, any piece on board off tape | 1 | 1 | 2 | 3 | 4 | 5 |
| Duck under platform | 3 | 4 | 8 | 12 | 16 | 20 |
| Pickleball under platform | 7 | 8 | 16 | 24 | 32 | 40 |
| Ring touching bottle (not neck) | 3 | 4 | 8 | 12 | 16 | 20 |
| Ring on neck (not touching board) | 15 | 15 | 30 | 45 | 60 | 75 |
| Cup flat/upright, on tape | 20 | 20 | 40 | 60 | 80 | 100 |
| Cup flat/upright, off tape | 20 | 21 | 42 | 63 | 84 | 105 |
| Cups nested (once) | 20 | 20 | 40 | 60 | 80 | 100 |
| Botguy on platform | 15 | 15 | 30 | 45 | 60 | 75 |
| Big Duck at Botguy's start | 15 | 16 | 32 | 48 | 64 | 80 |
| Mystery Red Pom alone on platform | 50 | 50 | 100 | 150 | 200 | 250 |
| Pom group of 5 (set or rainbow) | 25 | 30 | 60 | 90 | 120 | 150 |

| Pom group (Base additive) | Group score | + Base | Total |
|---|---:|---:|---:|
| same color x1 | 1 | 1 | 2 |
| same color x2 | 2 | 2 | 4 |
| same color x3 | 3 | 3 | 6 |
| same color x4 | 4 | 4 | 8 |
| complete set x5 | 25 | 5 | 30 |
| all different x2 | 4 | 2 | 6 |
| all different x3 | 9 | 3 | 12 |
| all different x4 | 16 | 4 | 20 |
| all different x5 | 25 | 5 | 30 |
| mixed, n poms (n=5 shown) | 0 | 5 | 5 |

Ceiling by category before the multiplier (default ruling) [I]: poms 140, rings 90, cups 62 (41 if the 60 state is
impossible: outer cup flat + nested + outer Base), pickleballs 32, Mystery Red Pom 50, Big Duck 16, Botguy 15, ducks 5 (Base) = **410**.
The 140 pom figure is the exhaustive optimum for splitting the 24 non-mystery poms over 5 zones (four rainbows of 5 and
one rainbow of 4); putting all 25 in zones is worth only 150 against 140 + 50 with the Mystery Red Pom on the platform
(checked by exhaustive search in `test_score.py`).

### 5.2 Marginal value of the k-th qualifying duck zone

With `S` = subtotal excluding the ducks' own Base and `k` qualifying zones, `total(k) = (S + k) x max(1, k)`.
The marginal value of zone k is therefore `+1` for k = 1 and `S + 2k - 1` for k >= 2.

| S | k=1 | k=2 | k=3 | k=4 | k=5 | total at k=5 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | +1 | +3 | +5 | +7 | +9 | 25 |
| 20 | +1 | +23 | +25 | +27 | +29 | 125 |
| 40 | +1 | +43 | +45 | +47 | +49 | 225 |
| 60 | +1 | +63 | +65 | +67 | +69 | 325 |
| 100 | +1 | +103 | +105 | +107 | +109 | 525 |
| 150 | +1 | +153 | +155 | +157 | +159 | 775 |
| 200 | +1 | +203 | +205 | +207 | +209 | 1025 |
| 300 | +1 | +303 | +305 | +307 | +309 | 1525 |

Reading it: when the rest of the board is worth S, each extra duck zone is worth about S. The first duck in a zone pays
only its Base unless a second zone follows.

### 5.3 Best use of the five ducks

Best split of the 5 small ducks into k qualifying zones and u under the platform, for subtotal S before the ducks:

| S | best split | total |
|---:|---|---:|
| 0-1 | 3 zones + 2 under platform (4 + 1 ties at S = 1) | 33 at S = 0 |
| 2-7 | 4 zones + 1 under platform (5 + 0 ties at S = 7) | 40 at S = 2 |
| 8 and up | 5 zones, none under the platform | 65 at S = 8 |

If Zone 5 does not count (A1) the cap is 4 zones and the fifth duck goes under the platform from S = 2 up.

### 5.4 Scenario totals (`data/scenarios/`, default ruling)

| Scenario | Subtotal | Mult | Total | What it is |
|---|---:|---:|---:|---|
| `a_theoretical_max` | 410 | 5x | **2050** | every piece scores; the scoresheet's cup 60 state assumed |
| `a2_theoretical_max_conservative` | 325 | 4x | **1300** | all ambiguities ruled against us, physically plausible states only |
| `b_ducks_only` | 6 | 5x | **30** | one duck per zone; Botguy's unmoved Base included (25 without it, 24 if Zone 5 is excluded, 20 with both) |
| `c_novice` | 43 | 2x | **86** | hypothetical: flip both cups in place, 2 ducks into zones 2 and 4 |
| `d_strong` | 152 | 3x | **456** | hypothetical two-robot run: Botguy and Big Duck swap, Mystery Red Pom, cups, 2 pickleballs, 4 reds sorted, 3 duck zones + 1 duck under platform |
| `e_ducks_under_platform` | 21 | 1x | **21** | all 5 ducks under the platform (compare b: 30) |

`c_novice` and `d_strong` are targets we defined, not measurements. The scenario descriptions state each assumption.

---

## 6. Gameplay, timing, start light, shutdown

### 6.1 Virtual tournament requirements [S, RS p.3, p.11]

- A competition board built to the table document (TD), internet access, **two cameras**: a static one showing the whole
  board and a movable one for robot inspection and point verification.
- An adult present for the whole tournament who **attests** to the board, robots and pieces. Minor board differences may
  be accepted by the Head Judge.
- The Head Judge's rulings on rules or wording apply for the rest of the tournament; the Head Judge may overrule loopholes
  that violate the Spirit of Botball (RS p.10-11).

### 6.2 Before the round [S, RS p.9-10]

- Up to **two students** bring the robots to the table and set up. **90 s** for setup and calibration; robots go in the
  Starting Box(es). A slow team gets a warning and a 60 s timer and may be disqualified (A16 on how 60 and 90 combine).
- Starting lights sit on the outside edge of the table; teams adapt the sensor mounts. Lights must be aimed at the team's
  sensors or the floor and may not break the vertical projection of the board inside the PVC. **Two connected starting
  lights per team, one per controller.** Nobody touches the lights or the table after "Hands-Off".
- Report any table problem before "Hands-Off" ends. After it, nobody blocks the cameras, and no robot part may leave the
  Starting Box(es) before the round starts (movement inside is fine; a violation is a **fault**, consequence unstated).
  No signaling the robots to start. A shirt with large solid colors like the game pieces may get the student asked to crouch.
- Teams control outside light so the sensors are not triggered early.
- Timeout: **one 3-minute timeout for the whole tournament**, requested at the table before Hands-Off; adjust the robot, no
  practice runs (practicing the start-light sequence is allowed). Teams are told to save it for double elimination. In
  seeding, an illegal part can be removed using the timeout; in double elimination it is a disqualification.

### 6.3 The round [S, RS p.10]

| Time | Event |
|---|---|
| 0 s | lights on; robots may leave the box |
| 5 s | lights off |
| 120 s | game over: motors off, servos frozen or powered down |

- The 120 s limit is enforced even if the home light setup gives no end-of-round blink; the team tracks time itself.
- Failing to stop driving motors and servo motion = **automatic disqualification for that round**; a servo holding
  position under load is fine.
- A team that never breaks the Starting Box boundary (including the 12 in ceiling) scores **0** (RS p.8, p.10).
- Shutdown guidance (RS p.11): threading can leave the robot running past the `shut down in` function; limit threads and
  stop the robot yourself.
- If everything has stopped before 120 s, the judge may ask whether the robot is done and end the round early.

### 6.4 Scoring and disputes [S, RS p.10]

Scoring happens after the round and after pieces come to rest. Object to a score **before leaving the table and before
anything is moved**; the Head Judge decides in at most 5 minutes; the team initials the sheet. No instant replays and no
outside video. Only the two students at the table may discuss a ruling.

---

## 7. Tournament structure and seeding

### 7.1 Structure [S, RS p.8, p.11]

- **Seeding: 3 single-sided runs**; seed score = **average of the best two**; seed scores below 0 count as 0 (the rules
  contain no negative scoring [I]). Not head-to-head.
- **Double elimination**: out after two losses; teams play simultaneously on their own boards and scores are compared.
  Non-final tie: replay once; then tiebreakers in this order: most rings on bottle necks, most complete pom sets, most
  ducks counted toward the multiplier, most cups flipped, most pickleballs under the platform, Mystery Red Pom scored,
  closest to Botguy (nearest corner of the Wombat to Botguy). Finals: replay until one team has strictly more.
- Not part of this game: documentation scoring, double seeding, alliance matches, tiered double elimination.

### 7.2 Overall score [S, RS p.14]

Overall = Seeding score + Double Elimination score; **maximum 2.000**.

```
Seed Score = 3/4 x (n - SeedRank + 1) / n  +  1/4 x (Team Average Seed Score / Max Tournament Seed Score)
DE Score   = (n - DE Rank + 1) / n
n = number of teams at the tournament or in the bracket
```

Reading it [I]: three quarters of the seeding component is rank (each rank place is worth `0.75 / n`), one quarter is your
average relative to the best team's average. For n = 20: rank 1 with ratio 1.0 gives 1.000; rank 2 at 90% of the top gives
0.9375; rank 5 at 60% gives 0.750; rank 10 at 40% gives 0.5125. Because the ratio term is relative to the tournament
maximum, one runaway team shrinks everyone else's ratio term. Best-two-of-three means one failed run costs nothing, but
two failures drag the average down; a disqualified or zero run counts as a run. How seed ranks are tied is not stated (A20).

### 7.3 Team inventory cross-check (INV vs the rules) [I]

| INV line | Note |
|---|---|
| 2 controllers, 2 batteries, 2 chargers | two Wombats allow two robots and two start lights (RS p.9, p.12) |
| 4 Mecanum + 4 multi-directional + 4 simple wheels, 2 Pololu balls | no restriction in the rules |
| 2 small (9 g) + 5 regular servos | fine |
| IR sensors, switches, buttons, limit switches, IR emitter/receiver, 1 Logitech camera | rules allow two cameras (A18); INV has one |
| **7 DC motors (team memory, unverified)** | `docs/team-hardware-confirmed.md`: Robot A mecanum 4 + 1 arm and Robot B 2. INV lists no motors at all. The mecanum robot's fifth motor cannot share one Wombat (4 motor ports) |
| **no light sensor listed** | the start light needs one; RS p.12 says the kit's light sensors need no light guide, so check you have them |
| 1 wrench | wrenches, screwdrivers, chargers, cables, boxes, bags, packing and color stickers may not be built into the robot (RS p.11) |
| "Parcour": cotton fuzz, foam block bags, traffic cones, wood pallets, plushie | these look like last year's pieces; this year's ducks, pickleballs, rings, cups, bottles, Botguy and Big Duck are not listed. You need practice pieces of the 2026 sizes (section 1.3) |

---

## 8. Construction and kit rules [S, RS p.11-13]

The construction rules are this document plus any updated rules on the FAQ (the 2026 document does not say where the FAQ
is; LY p.19 pointed to a Discord FAQ).

**Parts**
- Sensors from the 2017, 2018, 2019 and 2020-2026 kits are allowed if they do not exceed the type or number in the **2026
  kit** (that list is not in the repo). Two cameras may be used; the included camera is the only USB device allowed on a robot.
- Any or all of this year's kit parts except boxes, bags, wrapping, packing material, chargers, download cables, wrenches,
  screwdriver and color stickers. The old aluminum KIPR chassis is not allowed.
- Only Wombat controllers; multiple controllers may be on one robot; no need to use every part; a robot name must be G-rated
  and approved by an adult team leader.
- No electrical modification of controllers, sensors or motors (approved battery substitution only); **no wire extensions
  except those in the kit**.
- Metal parts may not be cut or broken; only straps and plates may be bent, brackets may not. Lego may not be modified
  except threading axle holes with screws.
- Only **4 ft** of the ABS plastic rod; it must be permanently attached to the robot by at least one end and may not be a
  projectile or independent structure.

**Allowed extras (limits)**

| Material | Limit |
|---|---|
| Removable mounting dots/strips (Glue Dots, UGlu, Scotch Restickable, blue tack) | allowed; hot melt glue and other adhesives are not |
| Zip ties | unlimited for wire management; **5 total** for any other use; standard 4 in white ties only (black or white replacements of equal size) |
| Thread, string, fishing line | 100 cm total, max 1 mm diameter, non-metallic; not for entanglement |
| Paper (max 20#), foam board, corrugated plastic | up to one letter/A4 sheet of each; **black or white/grayscale only** |
| Rubber bands | 10, max size #19, not glued or melted |
| Metal paper clips | 10, 1-1.5 in, not cut, broken or plugged into wiring |
| Coins | up to 250 g, counterweight only |
| Light sensors | no light guide needed unless there is strong direct sunlight |

---

## 9. 3D print rules [S, RS p.12]

- Filament **PLA or PETG**; every printed part **grayscale**, any material.
- A single part cannot exceed an Ender 3 V3 SE print volume: **220 x 220 x 250 mm**.
- Allowed parts: **6 small, 2 mid-size, 1 large** (nominal 60 x 60 x 20 mm, 220 x 220 x 80 mm, 220 x 220 x 250 mm);
  the text does not say whether that is per team or per robot (A17).
- Size is the **total exterior bounding-box volume in whole-inch units**: each of the three dimensions is rounded **up**
  to the next whole inch, then multiplied.
- Anti-circumvention: splitting or segmenting parts, or assemblies of smaller prints that tether, sit adjacent or assemble
  into a functionally or physically monolithic part, are judged as one combined part; the Head Judge may disqualify or
  require changes.
- An **STL for every part in use** must be submitted before the tournament on the schedule posted on Team Homebase.

### 9.1 What the rounding does [I]

1 in = 25.4 mm. Whole-inch bins: 1 = 25.4, 2 = 50.8, 3 = 76.2, 4 = 101.6, 5 = 127.0, 6 = 152.4, 7 = 177.8, 8 = 203.2,
9 = 228.6, 10 = 254.0 mm. A dimension of 25.5 mm already counts as 2 in, so a part at exactly 25.4 mm is one tolerance
error away from the next bin: design to **0.5 mm under** each bin edge.

Applying the rounding to the class names (the only reading in which each class can hold its own nominal part):

| Class (count) | Nominal mm | Whole-inch box | Rounded volume | Largest actual part under a per-dimension reading |
|---|---|---|---:|---|
| Small (6) | 60 x 60 x 20 | 3 x 3 x 1 in | **9 in^3** | 76.2 x 76.2 x 25.4 mm (design to 75.7 x 75.7 x 24.9) |
| Mid (2) | 220 x 220 x 80 | 9 x 9 x 4 in | **324 in^3** | 220 x 220 x 101.6 mm (printer limits X and Y to 220) |
| Large (1) | 220 x 220 x 250 | 9 x 9 x 10 in | **810 in^3** | 220 x 220 x 250 mm, i.e. any single part that fits the printer |

Two readings of "volume class" disagree (A17):
- **Per-dimension**: the rounded box must fit inside the class box (any orientation). Small = at most 3 x 3 x 1 in.
- **Volume only**: the rounded volume must be at most the class volume. Small then also admits, for example, 9 x 1 x 1 in
  (228.6 x 25.4 x 25.4 mm), 1 x 2 x 4, 1 x 3 x 3 or 2 x 2 x 2 in (50.8 mm cube); mid admits 6 x 6 x 9 in
  (152.4 x 152.4 x 228.6 mm), 7 x 7 x 6, 8 x 8 x 5 besides 9 x 9 x 4.
- Reading the class volume from the **unrounded** nominal sizes (small 4.39, mid 236.3, large 738.4 in^3) makes a part of
  exactly the nominal size exceed its own class, so it cannot be the intended meaning.

**Safe design rule**: make every small part fit 3 x 3 x 1 in, every mid part 9 x 9 x 4 in (X and Y at most 220 mm), and
treat a part over 101.6 mm tall as a large part. A part that is thin (up to 25.4 mm) is free to be 76 mm wide. Do not
count on printing a spare part for a bigger slot.

---

## 10. Robot logistics [S, RS p.7-8, p.12-13]

- **Robot** = Wombat + at least two motors, and it must leave the box (3.1). A team with two Wombats has two robots (two
  start lights, one per controller).
- **Start boxes**: small box 11.25 x 21.125 x 12 in; larger box = Zone 5. Robots start inside a Starting Box; each robot
  must individually fit the small-box footprint (interim rule), though one may start in the larger box.
- **Everything at game start inside a Starting Box volume**; after the start robots may expand.
- **Independent structures** (anything on the table not under computer control): **at most 4 at a time**, each marked with
  the team number.
- Starting-light sensors may be shielded, but neither sensor nor shield may extend outside the Starting Box.
- Ceiling: breaking the 12 in height of the box also counts as leaving it (RS p.8).
- Design numbers [I, G]: footprint 286 x 537 x 305 mm; platform plate underside 5.5 in (140 mm); entrance for ducks and
  pickleballs 4.04 in tall x 7.5-9.25 in wide (103 x 190-235 mm); cups 5.70 in tall with a 3.63 in mouth; rings ID 1.41 in
  on 1.30 in posts, 2.5-3.5 in off the board.

---

## 11. Safety and communication [S, RS p.13]

**Safety**
- No untethered robot-launched projectiles except game pieces; no tethered projectiles containing metal.
- No metal pieces or wires in fast-moving or rotating effectors; no metal protrusions likely to cause electrical or safety
  risks to other robots (arms and projectiles included).
- Judges decide what is safe. Black or white electrical tape may cover metal deemed a risk, but never for structure.
  An unsafe robot does not run until modified, or is removed from the table.
- Entanglement strategies are not in the spirit of Botball and may be disqualified.

**Communication**
- No external communication (IR, Bluetooth, wireless, semaphores) during play, **except robot-to-robot for a team's own
  robots**. The controller's WiFi may be on or off at the tournament, so a team's own robots may talk over it [I].
- Programming a robot at the table or on deck during rounds (timeout excepted) = DQ for the round.
- USB cables and chargers may not be used during game-table play.

---

## 12. AMBIGUITIES

KIPR says the Head Judge can rule on wording and that updates are posted to the FAQ (RS p.11). The 2026 document does not
say where the FAQ lives; last year it was a Discord FAQ (LY p.19). Send each question there; until answered, plan with
the **safest** reading. "Scorer switch" names the option in `tools/score.py` (default = the written rule; `--list-options`,
`--sensitivity`, `--conservative`).

Impact is shown where it can be computed. Let S = subtotal excluding the ducks.

### A1. Does Zone 5 (the large Starting Box) count for the Overall Multiplier?
- **Text.** RS p.3 lists "the Starting Box" among areas excluded from the multiplier count and says Zone 5 doubles as the
  larger Starting Box. RS p.6 says each of the **5 numbered zones** counts and excludes only "the **smaller** Starting Box"; max
  5x. RS p.7 defines Starting Box as both boxes. SS has a Zone 5 row (A36) and a 5x cap (B38).
- **Readings.** (a) Zone 5 counts: 5x is reachable. (b) Zone 5 is excluded: the cap is 4x and the 5th row and 5x cap are dead text.
- **Safest.** Plan on 4x; do the duck in Zone 5 last and treat it as an option.
- **Switch.** `zone5_counts_for_multiplier` (default true). **Impact:** with all five ducks in zones, 5(S+5) vs 4(S+5), one
  full subtotal (20% of the total).
- **FAQ question.** "Zone 5 is also the larger Starting Box. Does a Zone 5 that holds exactly one small duck count as a qualifying zone for the Overall
  Multiplier (so 5x is possible)? Game Board Areas excludes 'the Starting Box', the Overall Multiplier text excludes only 'the smaller Starting Box', and the
  scoresheet has a Zone 5 row."

### A2. Does a duck touching black tape count toward a zone?
- **Text.** Black Tape Rule: a piece touching tape does not score (RS p.5). Zones end at the inner tape edge (RS p.7). The multiplier says a zone with exactly one duck, no more no fewer (RS p.6). Not stated whether a tape-touching duck is "in" the zone.
- **Readings.** `ignore`: it is not in the zone. `count`: it is a duck in the zone (can qualify it or spoil it). `spoil`: it can spoil a zone but never qualify one.
- **Safest.** `spoil`: keep every duck clear of tape, and do not leave a stray duck on the tape beside a qualifying zone.
- **Switch.** `tape_duck_policy`. **Impact:** a stray duck on tape in a qualifying zone costs that zone, about one subtotal (S).
- **FAQ.** "A small duck whose body touches black tape but is partly inside a numbered zone: (1) is it counted as being in that zone for the 'exactly 1 duck' test, so that a
  second duck in the zone voids it? (2) can a tape-touching duck by itself make a zone qualify?"

### A3. Can several pom groups coexist in one zone?
- **Text.** Pom scoring is applied "for each group of poms found together in a single zone" (RS p.5). A Complete Set must be alone in its zone (RS p.8). The scoresheet has one pom row per zone (SS rows 22-26).
- **Readings.** (a) All poms in a zone are one group (a second color makes it mixed). (b) Physically separate piles are separate groups, each scored.
- **Safest.** (a): one clean group per zone, at most 5 groups total.
- **Switch.** `pom_groups_per_zone` (merge|separate). **Impact:** e.g. a pile of 4 yellow and a pile of 4 blue in one zone scores 16 separately vs 8 merged; five complete sets in one zone would be 150 scored separately vs 25 (Base only) merged.
- **FAQ.** "Pom scoring applies to 'each group of poms found together in a single zone'. If one zone has two separate, non-touching piles (e.g. 5 red in one pile and 5 blue in another), are they two groups
  each scored separately, or one mixed group for the zone?"

### A4. Is Base (1 per piece) additive with pom bonuses and with special scores?
- **Text.** RS p.5 says Base and special scoring are additive. But same-color poms score "1, 2, 3, or 4" (equal to Base), the mixed group "falls back to Base Score only - 1 point per pom, no additional bonus" (RS p.5-6), the cup list gives Base only for "no special condition" (RS p.6), the Highest Scoring Rule says a piece scores in **one** area, and the scoresheet pom formula returns B for same color (SS E22:E26) with a separate Base row (SS row 9) the judge fills.
- **Readings.** Additive: 3 red poms = 3 + 3 = 6; set of 5 = 30; duck under platform 4; pickleball 8; ring on bottle 4; cup flat 21. Non-additive: 3; 25; 3; 7; 3; 20.
- **Safest.** Non-additive for planning.
- **Switches.** `pom_base_additive` (poms), `special_base_additive` (everything else). **Impact:** at most 5 per pom group (up to 25 before the multiplier for five groups); about 1 per special piece; under 4% of a strong run (d_strong: 456 vs 444).
- **FAQ.** "Is the 1-point Base Score added on top of special scores? Examples: three red poms alone in a zone (3 or 6?); five different colors in a zone (25 or 30?); a duck under the Raised
  Platform (3 or 4?); a pickleball under the platform (7 or 8?); an upright cup off tape (20 or 21?)."

### A5. Do stacked inverted cups count as nested? Is nested + both flat possible?
- **Text.** Nested = one cup inside the other's volume (RS p.6, p.8); flat/upright = bottom flat on the board; the table row says "up to 60", "both nested and both flat" = 60.
- **Readings.** Inverted nest (rim-down) counts, or only upright nests count. If one cup sits inside the other, the inner one is not touching the board, so 60 appears unreachable and the practical ceiling is 40 (outer flat + nested).
- **Safest.** Bank 40 (two separate flips, or outer flat + nested), never 60. If nesting, nest upright.
- **Switch.** `inverted_nest_counts_as_nested`. **Impact:** 20.
- **FAQ.** "Do two cups stacked with both inverted (rim down) count as 'nested'? When one upright cup sits inside the other, is the inner cup 'flat/upright' (it does not touch the board)? How can the 60-point state occur?"

### A6. Several rings on one bottle neck? Where does the neck start?
- **Text.** 15 points for a ring when the neck breaks its interior volume (RS p.6). No limit per neck; the neck is not defined. The mesh suggests three rings can stack on one neck (`docs/field-map.md` section 6), so this is a practical question.
- **Readings.** Every ring on a neck scores 15, or only one ring per neck (extras 0 or 3).
- **Safest.** Spread rings over the three bottles (at most 2 each), and seat each ring well down the neck.
- **Switch.** `max_rings_per_neck` (None|1). **Impact:** up to 45 of the 90 available.
- **FAQ.** "May more than one ring score the 15-point 'on bottle neck' level on the same bottle? Where does the neck start (how far down must the ring sit)? Does a ring on a neck that also touches the board earn Base?"

### A7. Pieces resting on a robot
- **Text.** Pieces must touch the surface of the scoring area (RS p.5) and scoring is by final location. Nothing is said about robots at the end of the round, robots parked in a zone (Zone 5 is also a start box) or pieces under a robot.
- **Readings.** Pieces on or inside a robot score 0 and do not count in a zone; or they count as in the zone below.
- **Safest.** End with every scoring piece off the robot and the robot not sitting on pieces.
- **Switch.** not modeled (pieces on robots are simply left out of the scenario).
- **FAQ.** "At the end of a round, do pieces resting on, held by, or under a robot score or count for a zone (for example a duck sitting on a robot parked in Zone 5)?"

### A8. Scoresheet pom formula vs the written rule
- **Text.** Formula `IF(B=5,25,IF(B>=1,B,IF(C>=2,C^2,0)))` (SS E22:E26). Written rule: Complete Set needs "no other colors present"; all-different is n^2; mixed is Base only.
- **Problems.** (1) If the judge enters B = 1 ("each color once") for a rainbow of 3, the sheet pays 1, not 9; the judge must enter B = 0, C = 3. (2) With 5 red + 1 blue, B = 5 pays 25 although the written rule makes it a mixed group. (3) "Same-Color Count" is not defined for mixed groups (2 red + 1 blue: B = 2 pays 2). Our tests show these cases (`TestScoresheetParity`).
- **Safest.** Assume the written rule, and show the judge the intended entries for B and C before the round.
- **Switch.** the scorer follows the written rule; the sheet behaviour is reproduced only in tests.
- **FAQ.** "How should the judge fill 'Same-Color Count' and 'Unique-Color Count' for: (a) 3 poms, all different colors; (b) 5 red poms and 1 blue pom in the same zone; (c) 2 red and 1 blue? The formula pays B before C, so B = 1 for the rainbow would give 1 instead of 9."

### A9. Do Botguy, the red pom and the Big Duck also earn Base on the platform / at their positions?
- **Text.** Base is additive with special scoring (RS p.5); platform items are "scored as" 15 / 50 (RS p.6).
- **Readings.** +1 each, or the special value replaces Base.
- **Safest.** No Base.
- **Switch.** `special_base_additive`; for platform items also `platform_counts_as_board_surface` (A10). **Impact:** 1-2 points.
- **FAQ.** "Does Botguy on the Raised Platform (15) or the Mystery Red Pom alone on it (50) also earn the 1-point Base? Does the Big Duck at Botguy's starting position (15) also earn Base?"

### A10. Is the Raised Platform "board surface"?
- **Text.** Base is for touching "the board surface" (RS p.5); the platform is a corrugated-plastic deck above the FRP, called a scoring area (RS p.7). Last year's rules said "game table or platform" separately (LY p.13, rule 6).
- **Readings.** The deck is not the board (no Base for platform pieces), or it is board surface.
- **Safest.** Not board surface.
- **Switch.** `platform_counts_as_board_surface` (default false). **Impact:** +1 per piece, at most about 2-3.
- **FAQ.** "Is the top of the Raised Platform 'the board surface' for Base Score, and does the area under the platform (FRP floor) count as board surface?"

### A11. Pieces resting on other pieces
- **Text.** The General Scoring Rule requires touching the surface of the scoring area; the start stacks have the 4th pom on top of 3. Last year's Electricity Rule counted stacked cubes as touching the surface below (LY p.13, rule 5); nothing similar is in the 2026 text.
- **Readings.** A stacked piece scores nothing (and may not count in the sort), or it counts as touching the board.
- **Safest.** Spread poms flat; stacked pieces score 0.
- **Switch.** not modeled (list only pieces touching the board).
- **FAQ.** "Does a piece resting on another piece (a pom on a pom, a pom inside an upright cup, a duck on a cup) count as touching the board? Is there an equivalent to last year's 'Electricity Rule'?"

### A12. Identity of the Mystery Red Pom, and the hidden-pom split
- **Text.** Only "that" hidden red pom earns 50 (RS p.6). There are 5 red poms. RS p.4: 3 poms under the cup nearest the Start Box (including the red) and 2 under the other; the GLB shows 1 and 4.
- **Readings.** Only the original hidden pom scores, or any red pom alone on the platform.
- **Safest.** Keep the freed red pom separate from the four visible reds and deliver only that pom.
- **Switch.** `any_red_pom_is_mystery`. **Impact:** 50 x multiplier if you pick wrongly.
- **FAQ.** "The five red poms look identical. If a different red pom (not the one that started under the cup) is alone on the platform, does it earn the 50? How will judges identify it? Which is correct for the start: 3 + 2 poms under the cups (rules) or 1 + 4 (the 3D model)?"

### A13. Is the Big Duck a "duck"?
- **Text.** Multiplier text: "exactly 1 duck" (RS p.6); scoresheet: "smaller duck" (SS A30); the Piece Summary lists small ducks for under-platform 3 and multiplier. "At Botguy's starting position" is not defined (footprint, tolerance); Botguy starts outside zones 1 and 2.
- **Readings.** Big Duck does or does not count for exactly-1 and for the under-platform 3.
- **Safest.** Keep the Big Duck out of numbered zones; place it clearly on Botguy's old spot.
- **Switch.** `big_duck_counts_for_multiplier`. **Impact:** one zone (about S) if the Big Duck lands in a duck zone.
- **FAQ.** "Is the Big Duck a 'duck' for (a) the exactly-1-duck zone test, (b) the 3-point under-platform score? How exactly is 'at Botguy's starting position' judged?"

### A14. Do unmoved pieces earn Base (Botguy at his start, the blue bottles)?
- **Text.** "Every scoring piece touching the board surface, off tape" (RS p.5). Botguy is a listed piece; the bottles are called scoring pieces in the definitions (RS p.8) but have no count or points (RS p.5).
- **Readings.** Botguy untouched = +1, bottles +3, or neither; fixtures do not count.
- **Safest.** Count none.
- **Switch.** `unmoved_botguy_scores_base` (default true: Botguy +1). **Impact:** 1-4 points x multiplier (ducks only: 30 vs 25).
- **FAQ.** "Do Botguy standing untouched at his starting position and the three fixed blue bottles earn the 1-point Base Score?"

### A15. Two robots, the Starting Boxes, faults
- **Text.** The robot must leave "the Starting Box" (RS p.8, p.10); the Robot Rule counts a robot that leaves; the boxes are one small, one large; every robot fits the small footprint; all elements within a Starting Box volume at the start. A moving violation draws a fault with no stated effect.
- **Open points.** Must both robots leave? Must a robot starting in Zone 5 leave Zone 5? May both robots start in the large box? Must independent structures start inside a box? What is the consequence of a fault?
- **Safest.** Make every robot leave its box and clear its start area; start passive structures inside a box; never move before the lights.
- **Switch.** `robot.left_start_box`, `robot.disqualified` (gate the total to 0).
- **FAQ.** "With two robots, must each robot leave its Starting Box or only one? Does a robot that starts in the large box (Zone 5) have to leave Zone 5? May both robots start in the larger box? Must independent structures start inside a Starting Box? What is the penalty for a start-box 'fault'?"

### A16. Setup time: 90 s or 90 s + 60 s?
- **Text.** 90 s for setup; maximum 90 s (extendable); a slow team gets a warning and a 60 s timer and "may be disqualified" (RS p.9).
- **FAQ.** "Is the 60-second timer part of the 90-second setup or additional to it?" **Safest.** finish in 90 s.

### A17. 3D print class definitions
- **Text.** RS p.12 (section 9).
- **Open points.** Volume-only vs per-dimension fit (section 9.1); whether the rounded volume is compared to class volumes of 9 / 324 / 810 in^3; the 0-tolerance at exact inch boundaries; whether the 6/2/1 limits are per team or per robot; whether a smaller part may use a larger slot; whether supports, brims and rafts count in the bounding box; whether the box may be oriented any way; whether positioning jigs not used on the robot count (LY p.22 exempted them).
- **Safest.** Per-dimension fit with 0.5 mm margin, per class, in the printed orientation, nothing spare.
- **FAQ.** "Is a part's class decided by (a) its whole-inch bounding box fitting inside the class box (3x3x1, 9x9x4, 9x9x10 in) or (b) its rounded volume being at most the class volume (9, 324, 810 in^3)? Are the limits 6/2/1 per team or per robot? May a smaller part use a larger slot? Do brims and supports count, and may the part be rotated to measure it? Do jigs that never go on the robot count?"

### A18. Cameras and the 2026 kit list
- **Text.** "Teams may use two cameras" and "the included camera is the only USB device" (RS p.11); sensor rule refers to the 2026 kit's type and number.
- **Safest.** Plan with one camera until answered.
- **FAQ.** "Does 'two cameras' mean one per controller (is a second camera in the kit)? Please publish the 2026 kit parts list so older sensors can be checked against it."

### A19. Tape-touching poms, PVC, and what breaks a sort
- **Text.** Ducks do not break sorts (RS p.6); nothing is said about cups, rings, Botguy or other pieces in a zone, a pom of the group touching tape, or a piece leaning on the PVC border.
- **Safest.** Keep sorted zones free of other pieces; keep every pom of a group off tape and off PVC.
- **Switch.** not modeled (the scorer ignores poms on tape).
- **FAQ.** "If one pom of a five-pom group touches black tape (so it does not score), is the group judged without it (4 of a color = 4, not a Complete Set)? Do non-pom pieces in the zone (cups, rings, the Big Duck) break a pom sort? Do pieces leaning on the PVC border score?"

### A20. Minor points
- `Seed Rank` ties and `n` for the seeding formula are not defined (RS p.14); "Seed scores of less than 0 are counted as 0" has no matching negative scoring (RS p.11).
- The DE tiebreaker "closest to Botguy" is measured from the Wombat corner to Botguy (RS p.8), but Botguy may have moved; not stated whether Botguy's start or final position is meant.
- How a failure to stop (DQ for the round) is scored in seeding (we assume 0).

### A21. Out of bounds and the PVC border (added by the completeness review)
- **Text.** Nothing in RS defines out-of-bounds, whether a robot may cross or climb the 1.46 in PVC border, or what happens to a piece that leaves the board. Zones are bounded by the vertical projection of the PVC (RS p.7). Botguy and the Big Duck's 15-point spot lie on the 5.1 in board strip beyond the top wall (`docs/field-map.md` sections 3 and 6); PB3 and PB4 hang over the board edge.
- **Readings.** (a) Robots may go anywhere on or over the table as long as nothing is damaged; (b) the PVC ring is a boundary a robot may not cross.
- **Safest.** Plan to reach Botguy and his spot with an arm over the wall, not with the chassis.
- **FAQ.** "May a robot drive over, or have a wheel on, the PVC border? May it stand on the board strip behind the top wall? Does a piece that falls off the table score or return?"

### 12.1 Impact summary (from `--sensitivity`, default vs one switch changed)

| Switch flipped | b_ducks_only (30) | c_novice (86) | d_strong (456) | a_theoretical_max (2050) |
|---|---:|---:|---:|---:|
| `zone5_counts_for_multiplier` = false | 24 | 86 | 456 | 1640 |
| `pom_base_additive` = false | 30 | 86 | 444 | 1930 |
| `special_base_additive` = false | 30 | 86 | 444 | 2015 |
| `platform_counts_as_board_surface` = true | 35 | 88 | 462 | 2060 |
| `max_rings_per_neck` = 1 | 30 | 86 | 456 | 1825 |
| `unmoved_botguy_scores_base` = false | 25 | 84 | 456 | 2050 |
| **all rulings adverse** | 20 | 84 | 432 | 1336 |

Scenarios with no zone-5 duck, no tape duck and one pile per zone barely move; the tape, zone-5 and pile switches
matter only for boards that use those cases (formulas in A1-A3).

---

## 13. Using the scorer

```
python tools/score.py data/scenarios/d_strong.json
python tools/score.py scenario.json --sensitivity
python tools/score.py scenario.json --set zone5_counts_for_multiplier=false --set pom_base_additive=false
python tools/score.py scenario.json --conservative --json
python tools/score.py --value-table
python tools/test_score.py          # unit tests
```

Scenario schema, defaults and every switch are documented at the top of `tools/score.py` and by `--list-options`.
Omitted pieces are not on the board and score 0, except that Botguy defaults to "start" (unmoved, +1 Base under the
written rule) and the Big Duck to "platform" (unmoved, 0).

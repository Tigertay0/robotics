# 3D-printed parts: are they worth it?

Rules (rule summary, "3D Print Rules"): PLA or PETG, grayscale only, STL for every part submitted
before the tournament. Allowance per robot entry: **6 small** parts (60 × 60 × 20 mm), **2
mid-size** (220 × 220 × 80 mm), **1 large** (220 × 220 × 250 mm). Bounding boxes are measured in
whole inches rounded up, and parts that only make sense assembled together count as one part.

Short answer: prints don't add points by themselves, but they make the items worth the most
points reliable, and one print opens a 480-point item nobody on the team has a mechanism for.

## Ranked

| # | Print | Size class | What it replaces | Why it matters | Points at stake (×5) |
|---|---|---|---|---|---|
| 1 | **Duck lane** for Robot A, two halves of 160 mm, each 46 mm wide × 70 mm tall | both mid-size parts | 4 bent plates + 2 straps + 2 angle brackets + funnel straps | A printed channel has an exact 1.8" width, smooth inner walls with no bolt heads, the funnel built in, and the three servo flap mounts in the right places. Every double-drop or jam in the metal lane costs a whole multiplier step. | the multiplier itself: 5 ducks = the difference between 146 and 730 |
| 2 | **Claw pads** for the red pom, two cups shaped for a 1.6" pom | 2 small | bare LEGO liftarm fingers | A pom is soft and slips out of flat fingers. The red pom is one object worth 250 points and is grabbed once, at the end of the match. | 255 |
| 3 | **Cup hook** profiled to the 5.1" cup rim | 1 small | bent 1×10 strap | The hook has to catch the rim at one height while the robot moves. A printed hook with a lip does this at any approach angle. | 210 (two cups upright + off tape) |
| 4 | **Plow end caps** that round the plate tips | 2 small | bare plate edges | Keeps a pushed pom stack together as one group (4 + 4 pts each) instead of splitting it. | 200 |
| 5 | **Flap pad** for the intake gate | 1 small | bare 1×5 servo horn | A wider, flat flap face stops ducks squeezing past. | part of #1 |
| 6 | **Ring fork** (large part, 200 mm long) | the large part | nothing exists today | Slides under a stack of 3 rings on a post and lifts them; dropped over a bottle neck they score 15 each. This is the only untouched item worth more than the red pom and it is tiebreaker #1. But the rings sit at the bottom of an 8" post, so the fork must rise ~9" before it can clear the post top: that needs a lift the servo arm can't give. | up to 480, only with a new lift |

Total if all printed: 6 small (2 claw pads, 1 hook, 2 end caps, 1 flap pad), 2 mid (lane halves),
1 large (ring fork). Exactly the allowance.

## Recommendation

1. Print the **lane** first, before any other change. It is the only print that touches the multiplier.
2. Then the **claw pads** and the **cup hook**: cheap, small, and they protect 465 points.
3. Leave the **ring fork** until the core plan scores 500+ in practice three times in a row.
   Design the lift first (a second servo on the paralleling arm, or a rack from the LEGO gear rack
   parts); the fork is the easy part.

## Submission

Every STL must be submitted before the tournament, on the schedule posted on the Team Home Base.
Export each part from the Blender model (select the part, File → Export → STL, "Selection Only",
scale 25.4 to get millimetres) once the real dimensions are measured on the kit. Print in grey
PLA, 0.2 mm layers, 3 walls; the lane halves need supports under the flap mounts only.

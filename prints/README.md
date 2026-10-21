# Printed duck lane for Robot A

Two parts, both within the **mid-size** print allowance (220 × 220 × 80 mm). They replace the four
bent 4×12 plates, the two splice straps, the two angle brackets and the two funnel straps of the
metal lane, and they carry the three gate servos.

| File | Part | Size (mm) | Whole inches | Volume |
|---|---|---|---|---|
| `out/lane_front.stl` | front half with the funnel and the intake gate (C) | 202 × 121 × 71 | 8 × 5 × 3 | 119 cm³ |
| `out/lane_rear.stl` | rear half with the pin gate (B), the exit gate (A), the touch-switch window and the joint tabs | 180 × 120 × 71 | 8 × 5 × 3 | 108 cm³ |

Inside width 45.7 mm (1.8 in; a duck is 30 mm wide), walls 3 mm, height 70 mm. Assembled length
320 mm (12.6 in) plus the funnel. Robot A stays 17.9 in long.

## How it mounts
- The top flanges have 12 mm slots every 25.4 mm: bolt them to the chassis floor from above with
  8-32 × 1/2 in screws and keps nuts. The slots take up the difference between the printed pitch and
  the chassis hole pitch.
- The rear half's two tabs overlap the outside of the front half's walls; two 8-32 bolts per side
  through the matching holes join the halves.
- Gate servos push into their pockets from the outside, shaft first, through the 12 mm hole in
  the wall; the tab screws go along the wall into the pocket ends. The 1×5 servo horn goes on inside
  the lane and hangs down; closed = vertical, open = swung up through the slot (90°).
- The window on the right wall near the rear takes the small touch switch that reports "lane full".

## Printing
Grey PLA (grayscale is a rule), 0.2 mm layers, 3 perimeters, 20 % infill. Print each half on its
flange side (top face down) so the walls grow straight up with no supports; the funnel of the
front half then needs a small support wedge under its outer end, or print the front half standing
on its rear end instead. Check the first layer: the inside faces must stay smooth, so no brim on
the inside.

## Before printing
Measure on the real parts and change the constants at the top of `build_lane.py`, then re-run it:
`SERVO` and `MICRO` (body length, width, height of your servos), `HOLE` (8-32 clearance), the
chassis hole pitch (the flange slots). The script also writes `out/dims.json` with the rule check.

Submit both STLs on the Team Home Base before the deadline (3D Print Rules).

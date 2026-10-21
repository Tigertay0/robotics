# Blender model: 2026 Fall Game table and the two proposed robots

Units: 1 Blender unit = 1 inch. Origin = inside corner of the bottom-left PVC, x along the long
side toward the platform, y toward Botguy.

| File | What it is |
|---|---|
| `out/fall_game_2026.blend` | The **official table** (`Fall_Game_Table.glb` from KIPR, every game piece at its start position) plus Robot A "Duck Runner" in the small start box and Robot B "Point Scorer" in zone 5. Showcase copies of both robots sit off the table at y = -16. |
| `out/fall_game_2026_animated.blend` | Same scene with the 120 s plan from `../STRATEGY.md` keyframed, with a timer and score HUD. Press Space to play. |
| `out/strategy_animation.mp4` | The plan rendered from above (12 fps). |
| `out/*.png` | Stills: field, each robot, the start box, frames of the animation. |
| `out/pieces.json`, `out/envelopes.json` | Measured piece positions and robot envelopes, written by the build script and read by the animation script. |
| `build_fall_game.py` | Rebuilds `out/fall_game_2026.blend`. Needs `../Fall_Game_Table.glb` and the extracted `../STL Parts/` folder. |
| `animate_strategy.py` | Rebuilds the animation. Both robots' routes are the `A_WPS` / `B_WPS` waypoint lists at the top: `(time_s, x, y)`, add `'rev'` for a reversing move. It checks every frame that the robots never overlap each other, a placed duck or a pushed pom group, and prints `COLLISIONS:`. |

Rebuild:
```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/build_fall_game.py -- "$PWD/blender/out"
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/animate_strategy.py -- "$PWD/blender/out"
```
Set `NO_RENDER=1` on the second command to only bake and check collisions (seconds instead of minutes).

## What is real and what is estimated

Every object has a `source` custom property (N panel → Object → Custom Properties):
- `kit-stl`: geometry is the official KIPR/LEGO STL from the Team Home Base (chassis, servo
  brackets, plates, straps, channels, servo horns, liftarms, micro servo mount).
- `estimate`: a kit part without an STL (gear motor, servo, micro servo, Wombat, battery,
  mecanum and Solarbotics wheels, caster, sensors, camera). Sizes are from photos; measure yours.
- `design`: a layout decision (where a part sits, the lane width, the plow angle). Change freely.

Robot parts also carry a `kit` property naming the 2026 kit line they come from. Anything not in
the kit would be bright red and named `NOT_IN_KIT_*`; there are none at the moment.

## The robots

**Robot A, Duck Runner** (17.9 × 9.1 × 6.5 in): KIPR chassis raised to a 2.9" floor on four
servo brackets + 1" standoffs, four gear motors with mecanum wheels. Under the floor an open-bottom
lane 12.5" long and 1.8" wide made of four 4×12 plates on edge (two per side, spliced with 1×10
straps) and two angle brackets; two 1×10 straps flare out as the intake funnel. Three flaps (1×5
servo horns on two servos and one micro servo) act as intake, pin and exit gates so the robot
releases exactly one duck per zone. Sensors: two tophats at the lane mouth (tape edges), ET
rangefinder (wall distance), touch switch at the lane rear (lane full), light sensor (start).

**Robot B, Point Scorer** (14.4 × 9.2 × 8.7 in): the base/servo demobot from the KIPR build
guides (chassis, two gear motors, Solarbotics wheels, caster, Wombat) with the paralleling-arm
extension and the liftarm claw, a V plow from two bent 4×12 plates, a cup hook (servo + bent 1×10
strap) on the right side, camera on a 3×8 channel mast, two tophats, ET rangefinder, lever switch
on the plow and a light sensor.

Both fit the 11.25 × 21.125 × 12 in start-box limit (checked by the build script, see `ENVELOPE`).

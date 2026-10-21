# Wombat programs

| Folder | Robot | What it does |
|---|---|---|
| `robot_a/main.c` | Duck Runner (mecanum) | waits for the light, swallows the 5 ducks along the centre tape, drops one in each zone in the order 2, 4, 3, 1, 5 |
| `robot_b/main.c` | Point Scorer | upper cup, lower cup + red pom, 5 pom stacks into zone 1, pickleball 1, red pom on the platform |

Both follow the timeline in `../STRATEGY.md` section 4 and the routes animated in `../blender/`.

## Before the first run
1. Upload each `main.c` to its Wombat with the KISS IDE (`http://192.168.125.1:8888` on the Wombat's wifi, see the old notes).
2. Fix the port numbers at the top of each file to match your wiring.
3. Calibrate everything marked `CALIBRATE`:
   - `WHEEL_DIAM_IN` and `TICKS_PER_INCH`: drive 36 in with `forward_in(36, 50)` and measure.
   - `TICKS_PER_DEG` (Robot B): `turn_deg(360, 50)` should end facing the same way.
   - `STRAFE_FACTOR` (Robot A): strafe 24 in and measure.
   - `TAPE_THRESHOLD`: print `analog10()` on white and on tape; pick the midpoint.
   - `LIGHT_ON`: print `analog()` with the starting light off and on.
   - servo positions: move each servo in steps of 100 and write down the open/closed/up/down values.
4. Robot A's drop sequence is the single most important thing: run `drop_one_duck()` 50 times
   in a row on a bench and check that exactly one duck comes out each time.

## Known gaps
- The two robots are synchronised by the clock only (`seconds()`). Both Wombats start on the same
  light, so this works if the routes keep their timing; an IR message from B to A ("cups done")
  would be more robust. The kit's IR emitter/receiver pair is allowed between a team's own robots.
- Robot B's arcs are approximations of the animated route. Replace them by tape-based alignment
  (`forward_to_tape`) wherever a tape line is nearby.
- The camera channel 0 must be configured for red in the Wombat's camera settings (last year's
  `find_red.conf`).

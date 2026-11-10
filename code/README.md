# Wombat programs

| Folder | Robot | What it does |
|---|---|---|
| `robot_a/main.c` | Duck Runner (mecanum), starts in zone 5 | Moves out of B's way, then side-pushes the red stack and the upper cup north. Swallows the 5 ducks along the centre tape and drops one in each zone in the order 2, 4, 1, 5, 3. |
| `robot_b/main.c` | Point Scorer, starts in the small box | Drags the lower cup west and flips it, grabs the red pom, pushes 4 pom stacks into zone 1, knocks pickleball 1 toward the platform, then puts the red pom on the platform. |

Both follow plan v3: `../tools/match_plan.py`, checked by `python ../tools/match_sim.py` (no contacts between the robots, and B never touches a duck). They also follow the timeline in `../STRATEGY.md` section 4. Watch them run in `../docs/animation/robot_code_explainer.html`.

## Before the first run
1. Upload each `main.c` to its Wombat with the KISS IDE (`http://192.168.125.1:8888` on the Wombat's wifi, see the old notes).
2. Fix the port numbers at the top of each file to match your wiring. The build manual's wiring card uses the same numbers.
3. Calibrate everything marked `CALIBRATE`:
   - `WHEEL_DIAM_IN` and `TICKS_PER_INCH`: drive 36 in with `forward_in(36, 50)` and measure.
   - `TICKS_PER_DEG` (Robot B): `turn_deg(360, 50)` should end facing the same way.
   - `TRACK_IN` (Robot B): wheel centre to wheel centre. `arc_r(5, 90, 45)` should end facing 90° with its centre 5 in to the side.
   - `STRAFE_FACTOR` (Robot A): strafe 24 in and measure.
   - `TAPE_THRESHOLD`: print `analog()` on white and on tape; pick the midpoint.
   - `LIGHT_ON`: print `analog()` with the starting light off and on.
   - servo positions: move each servo in steps of 100 and write down the open/closed/up/down values. The claw is a standard servo that swings a liftarm finger against the printed jaw.
4. Robot A's drop sequence is the single most important thing: run `drop_one_duck()` 50 times
   in a row on a bench and check that exactly one duck comes out each time. `DROP_CREEP_IN` (3.3 in)
   must move the robot far enough for the exit flap to close behind the dropped duck (60 mm ducks).

## Hand-off times
The robots don't talk to each other. Each "wait for the other robot" is a fixed time after the start light (`wait_until_s`). Both programs record the light time in `t_light`.

| Constant | Value | Robot | Waits for |
|---|---|---|---|
| `T_A_EAST` | 12 s | A | B has dragged the lower cup west and backed off it |
| `T_B_NORTH` | 26 s | B | A is past the centre line with the ducks |
| `T_A_WEST` | 60 s | A | B has left zone 3 for the bottom wall |
| `T_A_DOWN` | 66 s | A | B is parked at the platform |

The same values are `P["T_*"]` in `tools/match_plan.py`, where an assert checks that each one is later than the moment the simulation says is safe. Time both robots on the practice table. If a step runs late, change the time in **both** places and re-run `python tools/match_sim.py`. A program prints `late for the … s hand-off` when it reaches a wait after its time has passed.

## Changing a route
1. Edit `tools/match_plan.py`.
2. Run `python tools/match_sim.py`. It must print NO CONTACTS.
3. Copy the distances into `main.c`. The comments give the expected (x, y) after every move.
4. Run `python tools/match_sim.py --export` so the video shows the new route.

## Known gaps
- The code has not been compiled on this PC (no C compiler). The first KISS IDE build will show any typo.
- Clock hand-offs work only if the routes keep their timing. An IR message from B to A would be more robust. The kit's IR pair is allowed between a team's own robots.
- Robot B's arcs (`arc_r`) are dead reckoning. Where a tape line is close, re-align on it.
- The camera's channel 0 must be configured for red in the Wombat camera settings (last year's `find_red.conf`).

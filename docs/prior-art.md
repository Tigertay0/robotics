# Prior art and techniques: Botball, Wombat, 2026 Fall Game

Written 2026-10-20 on branch `feat/fall-2026-strategy`. Scope: what other teams, KIPR and adjacent competitions (FTC, VEX) have already done for the tasks in this game, and how to structure Wombat code. It does not choose the strategy.

Tags (same as `docs/hardware.md` and `docs/field-map.md`):

- **[S]** stated by a source I opened in this session (link or repo path given).
- **[I]** my inference or arithmetic. Treat as a hypothesis.
- **[V]** must be verified on the team's own Wombat/robot, or asked of the Head Judge.

Table geometry comes from `docs/field-map.md` (vertex-tight CAD numbers), not from the inflated boxes in `data/glb_objects_raw.json`. Kit and port facts are in `docs/hardware.md`; this file does not repeat them.

Method: WebSearch/WebFetch, the `gh` CLI against the GitHub API (file trees, raw files, code search), Firecrawl developer search (noisy, low yield) and one Firecrawl scrape for a JS-heavy page (VEX library). PDFs were downloaded and text-extracted locally. Items I could not open are listed in section 10 and are not cited as evidence.

---

## 0. Summary

1. **Start-of-round skeleton is settled.** `wait_for_light(port)` then, on the next line, `shut_down_in(119)` ([KIPR slides](https://www.kipr.org/wp-content/uploads/2025%20Botball/Slides/wait_for_light-and-shut_down_in.pdf)). Two real teams (Malden, HTL St. Polten) use 120, which leaves no margin. Use 118 to 119 and time it at home. [S][I]
2. **`shut_down_in` ends the process with `abort()` after running `ao()` and `disable_servos()`** ([libwallaby source](https://github.com/kipr/libwallaby), `module/botball/src/botball_c.cpp`, `module/core/src/cleanup.cpp`). Arms go limp at the end, `atexit` handlers will not run, and a second call is ignored. Design the final pose to be stable without servo power. [S][I]
3. **Gyro is the winning navigation sensor** (Klauninger et al., GCER 2024: gyro heading hold beats time, back-EMF distance and back-EMF-balanced PID). Order of calibration: bias, then gyro scale, then ticks-per-inch, then turn constants ([Clement, GCER 2026](https://files.kipr.org/gcer/2026/workshops/Movement_Commands_Part_II.pdf)). [S]
4. **The gyro scale on a stock Wombat is documented inconsistently** (header comment 512 per 250 deg/s; code and firmware imply about 8.2 counts per deg/s; TJHSST's code divides by 8.248). Measure it with a spin test. [S][I][V]
5. **No threads in the main run.** The rules text warns about them, a GCER 2026 paper says the SPI layer is not thread-safe, Python does not export `thread_*`, and fire-and-forget servo threads can fight each other. Use a cooperative `pump()` loop (section 7). [S]
6. **Mecanum is now normal in Botball** (4 mecanum wheels are in the 2026 kit). It uses all four motor ports, so every effector must be a servo or a second Wombat. Strafing slips, so a gyro heading hold is not optional. [S][I]
7. **Hardest task on this table is rings onto bottle necks** (ring ID 1.41 in vs flange 1.30 in, 0.06 in per side). No Botball team publishes a ring-on-neck design; closest analogues are the VEX High Stakes hero bot (arm plus pusher, caps retain rings), Stack Attack drums on posts, and FTC cones on poles (four-bar keeps the object upright). KIPR itself rates "drums onto uprights" as Advanced. [S]
8. **Cups are the forgiving 40 to 60 points**: mouth 3.63 in vs base about 2.5 in gives about 0.5 in per side for nesting. The written 60 (nested plus both flat) looks physically impossible because the inner cup cannot touch the board, so plan on 40 (`docs/rules-digest.md` A5). [S][I]
9. **3D printing works for claws, funnels and holders, not for servo horns.** Printed claw: 97.5 % vs 87.5 % success, but 55 % heavier and 57 % longer to build (Jiang, GCER 2026). Printed servo horns do not transmit torque (Gugumuck et al., GCER 2026). [S]
10. **Combine several low-risk tasks, require 9 of 10 successes at home, and put a timeout on every step** (Honies and Swoboda 2018; HTL St. Polten 2026 code). [S]
11. **No published top scores for Stack Attack or any 2026 event were found.** Section 4 says what evidence does exist.

---

## 1. Source map

| Group | Source | Licence / status | Used for |
|---|---|---|---|
| KIPR docs | libkipr 1.0.0 docs: [botball](https://www.kipr.org/doc/botball_8h.html), [thread](https://www.kipr.org/doc/thread_8h.html), [wait_for](https://www.kipr.org/doc/wait__for_8h.html), [gyro](https://www.kipr.org/doc/group__gyro.html) | KIPR | API names, signatures |
| KIPR source | [kipr/libwallaby](https://github.com/kipr/libwallaby) (master, pushed 2026-10-19), [kipr/Wombat-Firmware](https://github.com/kipr/Wombat-Firmware), [issue 5](https://github.com/kipr/Wombat-Firmware/issues/5) | GPLv3 | actual behaviour of `gyro_z`, `shut_down_in`, `wait_for_light`, camera, threads |
| KIPR workshops | [Driving Using the Gyrometer 2025](https://www.kipr.org/wp-content/uploads/2025%20Botball/Slides/Driving-Using-the-Gyrometer.pdf), [Function Reference 2025](https://www.kipr.org/wp-content/uploads/2025%20Botball/Wombat-Function-Reference-Guide.pdf), [Movement Commands Part II (GCER 2026)](https://files.kipr.org/gcer/2026/workshops/Movement_Commands_Part_II.pdf), [Gyro in a Nutshell](https://files.kipr.org/gcer/2026/workshops/Gyro_In_a_Nutshell.pptx), [3D Printing Workflow](https://files.kipr.org/gcer/2026/workshops/3D_Printing_Workflow.pptx) | KIPR | gyro, drive, calibration order, STL workflow |
| Game reviews | [Spring 2026 "Stack Attack" v1.6](https://www.kipr.org/wp-content/uploads/2026/05/2026_Botball_Game_Review_v1.6_GCER.pdf), [2026 scoring examples](https://www.kipr.org/wp-content/uploads/2026%20Botball/2026-Botball-Scoring-Examples.pdf), [What's New 2026](https://www.kipr.org/wp-content/uploads/2026%20Botball/2026%20Whats%20New%20v1.0.pdf), [2023 Fall](https://www.kipr.org/wp-content/uploads/2023-Botball-Fall-Game-Review-v2-0.PDF), [2020](https://www.kipr.org/wp-content/uploads/2020%20Botball/Qatar/2020%20Botball%20Game%20Review%20v1.0%2020191117.pdf), [2019](https://www.kipr.org/wp-content/uploads/2019/02/2019-Botball-Game-Review-v1.4-20190227.pdf), and `docs/official/last-year/` (Pallet Pushers) | KIPR | past games |
| Team code | [HTL St. Polten packing-bot](https://github.com/htl-stp-ecer/packing-bot), [clawbot](https://github.com/htl-stp-ecer/clawbot), [cone-bot](https://github.com/htl-stp-ecer/cone-bot), [raccoon-lib](https://github.com/htl-stp-ecer/raccoon-lib), [raccoon-robots](https://github.com/htl-stp-ecer/raccoon-robots) (drumbot), [raccoon-image](https://github.com/htl-stp-ecer/raccoon-image) | MIT (robots), GPLv3 (lib, image) | structure, mecanum, steps, timeouts, IK arm, camera sorter |
| Team code | [TRMS Milpitas](https://github.com/Thomas-Russell-Botball/Botball-2026-TRMS-Milpitas) | CC0 | tutorial-grade C: servo speed, line follow, square-up |
| Team code | [Malden Catholic / Malden HS](https://github.com/Topmaster4545/Botball-25to26) | no licence | real Spring 2026 C code: Botguy, Drum, Pom (mecanum) |
| Team code | [TJHSST spring-game-25-26](https://github.com/TJHSST-Botball-Org/spring-game-25-26) | no licence | "Nano" thread-safe gyro library, gyro-held strafing (Greater DC team) |
| Team code | [elliott158/botball-2026](https://github.com/elliott158/botball-2026) | Unlicense | cone/cube C, `atexit` servo parking, SCAD wedges |
| Team code | [J0K3R-Joel/BotBall_Library](https://github.com/J0K3R-Joel/BotBall_Library), [3D-Print_BotBall_Library](https://github.com/J0K3R-Joel/3D-Print_BotBall_Library) | no stated licence | Python library, known-issues list, 394 team and KIPR STL files |
| Team notes | [Rochambotics Stack Attack README](https://github.com/victor-andiazabal/botball-stack-attack-2026) | work in progress | points-per-second method |
| Papers | Section 5 | KIPR archive | techniques |
| Adjacent | [gm0](https://gm0.org/en/latest/docs/common-mechanisms/index.html), REV FTC [PowerPlay lifts](https://docs.revrobotics.com/ftc-kickoff-concepts/powerplay-2022-2023/lifts) and [intake](https://docs.revrobotics.com/ftc-kickoff-concepts/powerplay-2022-2023/intake), [Freight Frenzy intake](https://docs.revrobotics.com/ftc-kickoff-concepts/freight-frenzy-2021-2022/intake), [VEX Axel hero bot](https://kb.vex.com/hc/en-us/articles/28421674310420-An-Introduction-to-Axel-The-V5RC-High-Stakes-Hero-Bot) | public | mechanism analogues |

Python on a stock Wombat: the IDE templates in `kipr/voldigate` (`src/ProgrammingLanguage.ts`), `kipr/ivygate` and `kipr/Simulator` start Python programs with `#!/usr/bin/python3`, `sys.path.append("/usr/lib")`, `from kipr import *` (found with GitHub code search). [S] The SWIG interface `binding/kipr.i` includes accel, analog, botball, button, camera, digital, gyro, motor, servo, time and wait_for; there is no `module/thread/binding.i`, so thread functions are not exported to Python. [S]

---

## 2. Software techniques

### 2.1 Program skeleton, start light, shutdown

**Best approach.** Servos to start pose, enable servos, calibrate gyro bias while still, `wait_for_light`, immediately `shut_down_in`, record `t0`, run a mission list that checks remaining time. [S][I]

Facts:

- KIPR: `wait_for_light(0); shut_down_in(119);` should be the first lines; without the shutdown the robot may not stop and is disqualified ([slides](https://www.kipr.org/wp-content/uploads/2025%20Botball/Slides/wait_for_light-and-shut_down_in.pdf) p.3). [S]
- `shut_down_in(s)` starts a thread that sleeps `s` seconds, prints "Shutdown after", calls `kipr::core::cleanup(true)` and `_exit(0)`. `cleanup` runs registered functions (`ao` from `motor/init.cpp`, `disable_servos` from `servo/init.cpp`) and then `abort()`. A second call prints "already called once. Ignoring." [S]
- `wait_for_light`: interactive on the Wombat screen. B with light on, B with light off. OFF minus ON must be at least 60 (12-bit counts) or "BAD CALIBRATION" (it adds "Add Shielding" if OFF < 256, else "Aim sensor"). Then it waits until two readings 100 ms apart are within 60 of ON, which rejects camera flashes. [S] (`botball_c.cpp`)
- Round: lights on 0 s, off at 5 s, over at 120 s; virtual teams may use a simple home light and must track time themselves (rules p.10). [S]

Pitfalls:

- Malden's tournament code uses its own `waitUntilLight` loop and `shut_down_in(120)`; HTL's `robot.yml` has `shutdown_in: 120`. Light detection takes at least 100 ms, so 120 ends after 120 s of real round time. [S][I]
- `atexit()` parking (elliott158 `end_programme`) will not run on `abort()`. [I]
- Calibrate gyro bias before `wait_for_light`, because the light calibration needs a person at the screen and the program is blocked after it. [I]
- A loop without `msleep` can make the Stop button unresponsive ([J0K3R Common_Issues 005](https://github.com/J0K3R-Joel/BotBall_Library)). [S]

### 2.2 Gyro: bias, scale, drift

What the sources say about `gyro_z()` on a Wombat:

| Source | Statement |
|---|---|
| [libkipr docs](https://www.kipr.org/doc/group__gyro.html) | "+/- 250 degree/sec range, 512 per 250 degrees" [S] |
| libwallaby `gyro_p.cpp` | returns 16-bit register divided by 16, minus an integer `biasz`; `gyro_calibrate()` averages 50 samples 10 ms apart and stores the bias as `int` [S] |
| Wombat-Firmware `wallaby_imu.c` | sensitivity byte 0 (250 deg/s full scale), 200 Hz sample rate, gyro and accel copied every 10th pass "at about 110 hz" [S] |
| TJHSST `nano.cpp` | integrates `gyro * dt` then divides by 8.248 to get degrees [S] |
| Clement 2026 (Part II) | `angle += (gyro_z - bias) * dt`, treated as degrees, then tuned with 4 x 90 degree trials [S] |
| Torbati and Zhang 2018 (Wallaby) | about 560000 "KIPR degrees" per 90 degrees for their 10 ms sum [S] |
| Madlberger and Greil 2026 | custom firmware at 2000 deg/s with a 42 Hz filter; not stock [S] |

Conclusion: 131 LSB per deg/s (standard MPU-9250 value at 250 deg/s, from memory, not opened) divided by 16 is 8.19 counts per deg/s, which matches TJHSST's 8.248. The header comment and Clement's code do not. [I] Measure on each Wombat: rotate it N x 360 degrees, integrate, adjust the constant. [V]

Other facts:

- The stock gyro saturates at 250 deg/s. Keep turn rates well below, about 200 deg/s. [I]
- Data refresh is about 110 Hz; sampling faster just repeats values. Use `seconds()` for `dt`, not the sleep length. [I]
- `gyro_calibrate()` truncates to an integer. Residual up to 0.5 count is about 0.06 deg/s, up to about 7 degrees over 120 s if sensor noise is below one count. After calling it, `gyro_z()` already has the bias subtracted; do not subtract twice. Prefer your own double-valued average of 1 to 2 s. [I]
- KIPR slide: recalibrate per run; temperature and orientation shift bias ([Gyro in a Nutshell](https://files.kipr.org/gcer/2026/workshops/Gyro_In_a_Nutshell.pptx)). Torbati and Zhang: warm the robot up first or bias changes once it moves. [S]
- [Wombat-Firmware issue 5](https://github.com/kipr/Wombat-Firmware/issues/5) (2020 to 2022): random spikes in the high byte, integration errors of plus or minus 10 to 20 degrees on older firmware. Current firmware status unknown. Filter spikes (median of three) and re-anchor heading on walls and lines. [S][V]
- Drift scale: a 0.05 deg/s bias gives 3 degrees per minute (Madlberger and Greil). [S]
- Custom IMU firmware (DMP, magnetometer) was used by the GCER 2026 IMU paper. Rules forbid electrical modification of the controller (p.13); whether reflashing is allowed is unclear. Do not rely on it. [S][V]

### 2.3 Drive straight and distance

Evidence ranking (Klauninger, Lindorfer, Kawicher, [GCER 2024](https://www.kipr.org/wp-content/uploads/2024/08/Enhancement_of_Accuracy_in_Botball_Navigation.pdf)): time-based is impractical; back-EMF position is better; PID balancing the two motors' ticks leaves the arc; PID on gyro error gives negligible displacement and also recovers from a bump. [S]

Other data:

- KIPR 2025 workshop: `dev += gyro_z() - bias` each loop, `delta = dev / 5`, add to one motor and subtract from the other; check motor signs or the robot "panics". [S]
- Clement: `correction = speed * theta / 12000`; calibrate bias first, then ticks-per-inch from a run longer than 12 in (short runs are dominated by backlash and rounding); flag a 10 % left/right TPI mismatch; ramp up, hold heading, taper by `ticks_left * 30`. [S]
- Tick scale conflicts: `motor.h` says about 1500 ticks per revolution; Klauninger says 1820. Calibrate per robot. [S][V]
- `mav` range is plus or minus 1500 ticks/s, accuracy drops outside plus or minus 1000 (`motor.h`). `motor(p, pct)` is `mav(p, pct * 15)`. [S]
- Stop accuracy: tick-terminated line follow varied up to 0.5 in over 20 runs; an ET-sensor trigger stayed under 0.2 in (Xie and Gao, [GCER 2025](https://files.kipr.org/gcer/2025/Analyzing%20Robotic%20Sensor%20Values%20for%20Enhanced%20Performance.pdf)). They subtracted a recorded baseline of the surroundings. [S]
- Rings need better than the 0.5 in dead-reckoning figure (section 3.1), so final alignment must come from a sensor or a physical guide. [I]

### 2.4 Turning

- Gyro angle beats motor ticks for turning (Klauninger). [S]
- Clement `turn()`: fast until 5 degrees remain, then slow (300 ticks/s); tune by running 4 x 90 degree legs repeatedly and watching drift. [S]
- TJHSST `turn_right_90` loops on an atomic orientation from a worker thread. [S]
- For this table: lateral drift while turning is caused by unequal motors (Klauninger corrected it with balance PID). Mecanum turns about the centre only if the wheels are matched. [S][I]

### 2.5 Mecanum on the Wombat

- Kit: 4 mecanum and 4 Solarbotics wheels; KIPR suggests mecanum on one robot and Solarbotics on the other ([What's New](https://www.kipr.org/wp-content/uploads/2026%20Botball/2026%20Whats%20New%20v1.0.pdf)). [S]
- gm0 ([holonomic](https://gm0.org/en/latest/docs/common-mechanisms/drivetrains/holonomic.html), [mecanum tutorial](https://gm0.org/en/latest/docs/software/tutorials/mecanum-drive.html)): rollers form an X seen from above; strafing is slower and slips; add odometry; equations `FL = y+x+rx`, `BL = y-x+rx`, `FR = y-x-rx`, `BR = y+x-rx`; normalise by the largest magnitude; optional strafe factor about 1.1. [S]
- GCER 2025 ([Yan, Zhang, Yan](https://files.kipr.org/gcer/2025/Wombat-Mecanum-Wheel-Control-System.pdf)): all moves are `motor()` plus `msleep`, turn is time-per-degree; common problems were mismatched ports/wires and debris in rollers. A beginner baseline, not a model. [S]
- Malden `Botguy.c` and `Pom Mechanum.c`: four `Motor` structs at fixed `mav` 1000 to 1250, all moves timed, ground sensors only for corrections; they work but cannot absorb a wheel slipping. [S]
- TJHSST `go_sideways`: holds orientation with a P term (Kp 1.09) from a threaded gyro integrator and `motor()` percent. [S]
- HTL packing-bot `config/robot.yml`: mecanum kinematics, distance and heading PIDs, velocity limits 0.214 m/s forward, 0.221 m/s lateral, 2.34 rad/s turn, saturation derating, fused encoder plus IMU odometry; robot 23.5 x 29.6 cm. [S] At 0.21 m/s a 96 in table length takes about 11 s. [I]
- All four motor ports are used; no DC motor left for lifts (`docs/hardware.md` section 7). [S]

Pitfalls: wheel direction flags per side (`inverted` in HTL `motors.yml`); one 45-degree roller set flipped gives a robot that turns when told to strafe; a gyro heading hold is needed because strafing slips. [S][I]

### 2.6 Absolute position on the table

- Pipes give absolute positioning in corners and reduce sensors needed ([Honies and Swoboda 2018](https://files.kipr.org/gcer/2018/winning-international-botball.pdf)). The border pipes are 1.46 in tall (field-map section 8), so a flat bumper plate can square against them. [S][I]
- Line squaring with two reflectance sensors: Clement's `calibrate_tpi_to_line`, TRMS `squareup.c`. The HTL steps use `.until(on_black(...) | after_seconds(2))`. [S]
- Collision detection: accelerometer with exponentially weighted mean and variance, alpha 0.05, threshold 4.5 sigma, ignore the first 10 samples, then back away and re-route to the next checkpoint ([Jin, GCER 2026](https://files.kipr.org/gcer/2026/Autonomous_Collision_Detection_and_Recovery_in_Botball.pdf)). Author says only parts were tested. [S]
- TRMS tutorial code is not safe to copy: `line_follow` reads `analog(RIGHTMOTOR)` with empty `#define`s, loop braces are unbalanced. Use the ideas only. [S][I]

### 2.7 Servos

API facts (`servo.h`): positions 0 to 2047; `get_servo_position` returns the last sent value, not the real position; commanding beyond the physical stop makes the servo strain and drains the battery. KIPR teaches about 150 to 1900 and ports have a 1.0 A hold fuse (`docs/hardware.md`). [S]

Approaches seen:

| Approach | Source | Verdict |
|---|---|---|
| Blocking time-interpolated move | TRMS `servo_speed.c` | simple, blocks the program [S] |
| Timer state machine | Ratia, [GCER 2025](https://files.kipr.org/gcer/2025/Real-Time%20Control%20of%20Multiple%20Servo%20Motors%20-%20Rocky%20Ratia.pdf) | simplest, waits for the slowest servo [S] |
| Fire-and-forget thread per move | same | two threads can drive one servo to different goals, damage risk [S] |
| Managed persistent thread per servo, interruptible | same | best timing, hardest to get right [S] |
| Cooperative slew: targets plus a `servo_tick()` in every loop | section 7 | no threads [I] |
| Named positions in config plus overlapped arm and drive | HTL (`servos.yml`, `parallel()`) | good structure [S] |
| IK arm with calibration tables, clamped to hardware limits | HTL clawbot `arm.py` | worth it only for a 3-DOF arm [S] |

Mechanical limits: Ratia estimates a standard servo at about 11 kg-cm at 6 V and a 20 cm plus 24 cm arm at about 10 kg-cm, near the limit. Pembroke's metal arm was too heavy and shorted servo ports (Guimares and Kaplowitz 2018). [S]

### 2.8 Camera

- API (`camera.h`): `camera_load_config("name")` (no `.conf`), `camera_open()`, `camera_update()`, `get_object_count(ch)`, `get_object_area`, `get_object_center_x`, objects sorted by area. Channels are made on the Wombat (Settings, Channels, HSV blob). [S]
- `camera_open()` calls `camera_open_at_res(HIGH_RES)` in `camera_c.cpp`, while header comments still say only LOW_RES works. Read `get_camera_width()` instead of assuming. [S][V]
- Malden and TJHSST call `camera_update()` twice before reading (`newImage()`), to flush a buffered frame. [S]
- HTL drumbot: camera runs as a background daemon, colour calibration in the setup mission, a calibration gate that refuses to start if data is missing; it defaults to guessing blue when no lock is achieved and the authors list that as a bug. [S]
- Rules: the camera is the only allowed USB device (p.11); team members' shirts of piece colours may be asked to move (p.10). `docs/hardware.md` notes at most 4 colour channels per config but 5 pom colours. [S]
- The libwallaby README describes a beta image that supports only the AI camera. Do not flash it. [S]
- For visible poms, colour is known by position (field-map section 6: one colour per stack). A camera is only needed for hidden poms or verification. [I]

### 2.9 Threads and concurrency

- Rules p.11: threading can cause unpredictable results such as the robot not stopping with `shut_down_in`. [S]
- [Ratia, GCER 2026](https://files.kipr.org/gcer/2026/Thread-Safe_Abstraction-in_KIPR_Robotics_Controllers.pdf): the Pi to STM32 SPI layer exchanges the whole memory map and is not thread-safe; concurrent access is undefined behaviour. [S]
- `thread_function` takes no arguments (globals only). [S] Python has no thread binding; use `threading` and test. [S][I]
- TJHSST solved it by sending every hardware call through one worker thread with a mutex-protected queue. [S]
- J0K3R issues list: forgotten `enable_servos`, tab/space errors, non-ASCII characters in pasted code ("null bytes"). [S]

**Rule for this project** [I]: one thread, a `pump()` called from every wait and loop (heading update, servo slew, timers). If a thread is ever added, one owner thread per actuator and a stopwatch test that `shut_down_in` still ends the run.

### 2.10 Robustness patterns

- HTL (packing-bot, clawbot): global cap, mission `time_budget`, `timeout(step, seconds)`, sensor stop OR-ed with a time stop, `defer()` to decide at run time, shutdown mission, one mission per scoring action numbered in tens, disable a mission in config rather than deleting. Their own words: "The sensor is the plan; the clock is the promise that the plan ends." [S]
- Honies and Swoboda: fail-safes at critical points, subsystems that fail 9 of 10 at home are dropped, modular subsystems, simple reliable beats complex. [S]
- Shared game state ([Elmesiry et al., GCER 2026](https://files.kipr.org/gcer/2026/Improving_Robot_Coordination_Using_a_Shared_Game_State.pdf)): phases with status Ready, Blocked, Running, Timed Out, Done; score `S = Kp*points - Kt*time + Kpt*potential` with 1.0 / 0.6 / 0.4. Needs robot-to-robot messaging, which the rules allow between your own robots (p.13); `docs/hardware.md` recommends independent programs. [S][I]
- Seeding is the average of the best two of three runs (rules p.11), so a consistent run beats a risky high one. [S]

---

## 3. Mechanisms

Numbers are from `docs/field-map.md` unless noted.

### 3.1 Rings: lift off a post, put on a bottle neck

Table facts: ring OD 2.13, ID 1.41, thickness 0.36; three per 1.30 in post, Z 2.46 to 3.54, post top 9.50; ring edge is 0.25 in past the board edge and 0.42 in into the field. Bottle neck about 1.06 in with a 1.30 in flange near Z 4.1, shoulder to 3.8, top 4.95; three rings can stack to about 4.75. [S]

Prior art:

- VEX High Stakes hero bot "Axel": a one-axis arm of about 90 degrees picks rings, passive flaps hold them while the arm rotates, a powered "Pusher" drives the flaps to push rings off onto stakes; a rubber cap on each stake retains rings. [S]
- Botball GCER 2023, per [Shen](https://www.kipr.org/wp-content/uploads/2024/08/Converting_Rotational_Motion_to_Vertical_Motion.pdf): a pulley lift raised a ring along a PVC path with sharp turns (precise, small footprint); a shifting parallelogram with a touch sensor at the top placed pool noodles straight onto poles. [S]
- YMWIC 2022 (DC area): a wide claw plus storage device removed rings from a stack ([newsletter](https://files.constantcontact.com/1f22ea34301/6761ae37-e96d-4f16-9920-1dbaf2a8e231.pdf?rdr=true), no detail). [S]
- Stack Attack drums on posts (hollow 2 in pipe over a post, volume rule): KIPR rates it Advanced in the [scoring examples](https://www.kipr.org/wp-content/uploads/2026%20Botball/2026-Botball-Scoring-Examples.pdf). Printed "Drum-Hopper", "Drum-Collector" exist in the print library; Jiang describes a printed holder that carries drums on two tubes. [S]
- FTC PowerPlay: cones with a hole placed on poles; REV recommends a four-bar or reverse virtual four-bar so the object stays upright through the lift. [S]

Recommended approach [I]:

1. **Lift:** vertical and linear. The ring is only 0.06 in looser than the post, so an arc or tilted lift jams. Candidates: string and pulley, rack and pinion, parallelogram. The post exposes about 7 in, so a stack of three needs about 6.4 in of rise for the top ring. Robots may grow after the start (rules p.12); string is limited to 100 cm of 1 mm line.
2. **Grip:** from the rim on the field side (the ring overhangs into the field), thin fingers, one ring at a time.
3. **Carry loosely, release by pushing** (Axel pattern), so the bottle, not the robot, finishes the alignment.
4. **Alignment aid:** a printed funnel or lead-in collar. The neck gives plus or minus 0.17 in at the tip but the flange only plus or minus 0.06 in; dead reckoning varies by 0.5 in (section 2.3). Print libraries are full of funnels and holders for this purpose (e.g. LACT "On_The_Rocks_Funnel"). [S names]

Pitfalls: ring jams on the post when lifted off axis; ring sits on the flange instead of the shoulder (only 3 points); dropped ring on tape scores nothing. [I]

### 3.2 Cups: flip upright, nest

Facts: upside-down, mouth 3.63 in on the board, base about 2.5 in, height 5.70. Cup 1 hides the red pom (CAD) and sits at the box's upper-left corner. Upright 20 each, nested 20, both 60 as written (the 60 state is probably unreachable, rules-digest A5); bonuses ignore tape (rules p.5, p.6). [S]

Prior art:

- REV PowerPlay "cone flipper": compliant wheels on a hinged rotating roller right a fallen cone. [S]
- gm0: claws suit large or awkward objects; they are slow and fragile. [S]
- Printed cup claws and holders are common in the 2025 library (e.g. "CupClawFinal1", "cup_arm", "double_cup", "3cup_combined"). [S names]
- Halebeedu: printed box claw with back-wall angle 22 to 25 degrees for friction, carries Botguy and two cones with two servos, 90 % for two cones. [S]

Recommended [I]: grip near the base (top face) with a printed claw, lift (poms fall out and may score), rotate 180 degrees with a wrist servo, set down mouth-up, then place the second cup into the first (about 0.5 in of tolerance per side). Tipping a 5.7 in cup with a sweep can leave it on its side.

### 3.3 Ducks: carry several, release one per zone

Facts: 2.27 x 1.46 x 1.46 in, soft rubber, start on tape 8 in apart; the multiplier needs exactly one duck in a zone. [S]

Prior art:

- REV Freight Frenzy: scoop and claw struggled with ducks; a top roller with compliant wheels and a spring jaw handled them and reduced picking two at once. [S]
- gm0: vertical intakes handle one piece at a time; compliant wheels tolerate size variation. [S]
- HTL drumbot: 8-pocket revolver, learned ticks per pocket, stall detection, pusher servo; their notes say a new item arriving before the previous one is processed can jam it. [S]
- Malden `Drum.c`: servo door gate plus `mrp` indexing; camera classifies each drum. [S]

Recommended [I]: a gravity magazine with a servo escapement gate, or a small indexed carousel. A plow can push ducks into near zones but may put two into one zone, which cancels that zone.

### 3.4 Poms: collect, sort, herd

Facts: 1.5 in poms; each visible stack is one colour (field-map section 6). Scoring: n different colours in a zone give n squared; one colour 1 to 4 is linear; all five of a colour is 25. [S]

Prior art:

- HTL packing-bot: claw on an arm sweeps poms while the robot strafes along a tape line, shakes the claw servo to release, compresses poms against the basket. [S]
- Guimares and Kaplowitz 2018: claw collected 6 to 8 poms per grab, a servo bucket 10 to 12; a sweeper arm funnels poms into the bucket. [S]
- Fischer et al. ([grabbers](https://robo4you.at/publications/grabbers_and_software_for_botball.pdf)): a vertical "excavator" grabber drags small pom groups; a horizontal neck grabber is weak at poms. [S]
- Printed "Pom-Collector", "Spike_Trap" in the 2026 GCER folder. [S names]
- Jiang: the pom claw was left in kit parts because it is simple and light. [S]

Recommended [I]: take one pom from each coloured stack for the n squared group; no camera for visible poms.

### 3.5 Pickleballs: off posts, under the platform

Facts: diameter 2.91, centre Z 3.75; platform entrance at X = 72, clear height 4.04, 7.5 in wide at the beam, 9.25 in below Z 3.0. [S]

I found no direct prior art. Closest: 2023 Fall ping-pong balls into a coupler; HTL `pom_remover` and Malden plow servos (sweepers). [S][I] Suggestion: a swing flapper to knock the ball and a low V-shaped wing that herds it into the 7.5 in opening; verify it does not drive two balls out of the board edge. [I]

### 3.6 Botguy and the platform

Facts: Botguy 8.52 in tall, base 6.83 x 2.5, outside the top wall; platform top Z 5.69; border pipe 1.46 in tall. [S]

Prior art:

- Pembroke 2018: neck-grab claw using Botguy's neck indentation, light claw on a coiled igus chain; heavy metal arms shorted servo ports. [S]
- Fischer et al.: horizontal grabber around the neck, best servo strength about 78.5 % on their build; a servo-less "gravity grabber". [S]
- Shen: a two-part rotating arm grabbed Botguy round the middle and set him down at a precise angle (2022). [S]
- HTL clawbot: 3-DOF IK arm, claw positions `closed` 50, `soft_close` 60 (do not crush), pulls Botguy out with a timed arm path. [S]
- Malden `Botguy.c`: two servos in parallel for the claw lift, separate plow servo. [S]
- YMWIC 2022: pulley claw for the mascot at the top of the board. [S]

### 3.7 Folding into 12 in and expanding

- Shen: rotating beams and parallelograms have a small base and large reach, which suits the start box; pulleys and rack-and-pinion give straight vertical motion but are limited to their rail. [S]
- Igus chain coils small and extends; 2018 kit part, **may not be in the 2026 kit** [V].
- REV: reverse virtual four-bar reaches about twice the height of a single arm in the same space. gm0 rigging: continuous or cascade string; watch stretch and a retraction path. [S]
- Print library: KIPR microservo linear actuator, rack and servo-arm STL files; TJHSST barlift. [S names]
- Rules: string 100 cm, rubber bands 10, ceiling 12 in at start only. [S]

---

## 4. Past KIPR games and how teams scored

| Game | Similar tasks | Source |
|---|---|---|
| 2019 storm relief | blue poms as water, Botguy on a skyscraper, power lines | [review](https://www.kipr.org/wp-content/uploads/2019/02/2019-Botball-Game-Review-v1.4-20190227.pdf) |
| 2020 moon colony | Botguy, material sorting | [review](https://www.kipr.org/wp-content/uploads/2020%20Botball/Qatar/2020%20Botball%20Game%20Review%20v1.0%2020191117.pdf) |
| 2023 Fall | rings on a stand, noodles on posts, pom stacks of 3+1, ping-pong balls into a coupler; large and small starting boxes, same as 2026 Fall | [review](https://www.kipr.org/wp-content/uploads/2023-Botball-Fall-Game-Review-v2-0.PDF) |
| 2025 spring | bottles, cups, fries (inferred from print filenames and simulator assets) | [I] |
| Fall 2025 "Pallet Pushers" | poms sorted into baskets, cubes, cones, Botguy | `docs/official/last-year/` |
| Spring 2026 "Stack Attack" | drums onto posts (volume rule), Botguy, poms into bins, two robots, ramp | [review](https://www.kipr.org/wp-content/uploads/2026/05/2026_Botball_Game_Review_v1.6_GCER.pdf) |

Evidence about scoring and approach (no published top scores found):

- Honies and Swoboda (champions 2016 and 2017): pick a few high-value, low-risk tasks, combine them, make each robot independent, a disruptor rarely paid off. [S]
- Rochambotics (work in progress): points-per-second analysis; sorted drums on posts about 53 pts/s, over twice the next task; two-robot split; park in multiplier zones. [S]
- Halebeedu: Botguy plus both cones plus parking about 1,200 points with two servos. [S]
- YMWIC at the Greater DC regional 2024: 10th of 20 seeded, top 8, KISS award for simple effectors. [S]
- KIPR 2026 scoring examples grade tasks Basic to Expert. [S]
- Official 2026 GCER results were not found.

---

## 5. Papers index (opened)

| Year | Paper | Use |
|---|---|---|
| 2018 | [Torbati, Zhang: Using the Gyroscope in Botball](https://files.kipr.org/gcer/2018/Using%20the%20Gyroscope%20in%20Botball.pdf) | bias, integration |
| 2018 | [Honies, Swoboda: Winning the International Botball Tournament](https://files.kipr.org/gcer/2018/winning-international-botball.pdf) | strategy and software practice |
| 2018 | [Guimares, Kaplowitz: IGUS Chain](https://files.kipr.org/gcer/2018/IGUS%20Chain%20and%20its%20Applications%20.pdf) | compact arm, poms, Botguy |
| 2019 | Fischer et al.: Grabber Designs (robo4you.at, link in 3.4) | grabbers |
| 2024 | Klauninger et al.: Enhancement of Accuracy (link in 2.3) | gyro vs encoders |
| 2024 | Shen: Rotational to Vertical Motion (link in 3.1) | arm types |
| 2025 | Yan et al. mecanum (2.5); Ratia servos (2.7); Xie and Gao ET (2.3); [Choros](https://files.kipr.org/gcer/2025/Choros%20A%20Distributed%20Coordination%20Framework%20for%20Multi-Robot%20Botball%20Systems.pdf) (tape-graph coordination) | |
| 2026 | Gugumuck et al., Jiang, Halebeedu (section 6); Madlberger and Greil [IMU](https://files.kipr.org/gcer/2026/IMU_Calibration_and_Orientation_Estimation_on_the_Wombat_Educational_Robot.pdf); Ratia threads (2.9); Jin (2.6); Elmesiry (2.10) | |

GCER 2023 and 2024 pages list further titles without PDFs (e.g. "The Basics of Robotic Arms in Botball", "Dual-Robot Multi-Objective Score Optimization"); not read. Index pages: [2023](https://www.kipr.org/gcer-2023), [2024](https://www.kipr.org/gcer-2024), [2025](https://www.kipr.org/gcer-2025), [2026](https://www.kipr.org/gcer-2026).

---

## 6. 3D printing in Botball

Rules (p.12): PLA or PETG, grayscale, volume classes small x6, mid x2, large x1, STL submitted for every part, anti-circumvention clause. Class interpretation: `docs/hardware.md` section 6.

What teams print: the [J0K3R print library](https://github.com/J0K3R-Joel/3D-Print_BotBall_Library) holds 394 STL/3MF files, 239 of them team-submitted (2025 folders including Greater DC, plus 2026 GCER). Filename keyword counts, overlapping and with 66 unclassified: boxes, baskets, holders 54; claws and grippers 43; bottle holders and grippers 30; shovels, scoops, plows 24; fork and lift 18; cup holders and claws 17; servo brackets, plates, counterweights 16; wheels, casters, chassis 13; funnels 3. [I] The folder also has KIPR's reference STLs (LEGO parts, metal parts, microservo linear actuator, PVC dispenser).

Evidence on what works:

- [Gugumuck et al.](https://files.kipr.org/gcer/2026/Replacing_Botball_Kit_Parts_with_3D_Prints.pdf): printed servo horn failed (no splines below 0.3 mm); printed angle bracket gave out at about 100 g; servo bracket deformed at about 200 g; channel held 15 kg; chassis 69.6 g printed vs 383 g metal, no speed benefit. Use prints for custom geometry, metal for load paths. [S]
- [Jiang](https://files.kipr.org/gcer/2026/Beyond_the_Kit_A_Quantitative_Comparison_of_3D_Printed_and_Traditional_Components_in_Botball_Robotics.pdf): printed vs kit drum claw: 34 g vs 22 g, success 97.5 % vs 87.5 %, build 102 vs 65 min, repair 5 vs 25 min (15 % infill). [S]
- [Halebeedu](https://files.kipr.org/gcer/2026/Improving_Reliability_and_Multitasking_with_3D_Designing.pdf): LEGO claw could not surround the object; printed box claw did. [S]
- Clement workshop: build in LEGO first, import KIPR's STLs as reference, review each print as a team. [S]

---

## 7. Recommended code architecture

### 7.1 Language

| | C | Python 3 |
|---|---|---|
| Docs and examples | all KIPR workshops, TJHSST, Malden, TRMS | HTL (custom OS), J0K3R, GCER 2025 mecanum |
| Iteration | compile on the Wombat (Fischer et al. found it slow) | no compile; stub `kipr` module lets you test on a laptop |
| Threads | `thread_*` available | not exported; `threading` only |
| Pitfalls | pointer and int-overflow bugs | tab and non-ASCII errors (J0K3R 002, 010) |

Stay on the stock Wombat OS. HTL's RaccoonOS is an alternate image and library; whether a tournament accepts it is unknown, ask the Head Judge. [V] The architecture is the same in either language; default to the language the team already writes best. [I]

### 7.2 Layers

```
config      ports, calibrated constants, named servo positions (one file, edited after each rebuild)
hal         Drive (mecanum mix), Heading (gyro), Servo (slew), Sensors (thresholds), Clock
motion      drive_hold, turn_to, wall_bump, line_square, until_sensor (all with timeouts)
tasks       one function per scoring action: precondition, budget, returns 1/0, leaves a safe pose
main        gyro bias, wait_for_light, shut_down_in, mission list with minimum-time-left check
```

### 7.3 Snippets

Original code modelled on the cited algorithms. The C was compiled with `zig cc -Wall -Wextra` against a stub header of verified libwallaby declarations and exercised against a fake `libkipr`. The Python was run against a stub `kipr`. Neither has run on a Wombat. Signs, ports and constants are placeholders.

```c
#include <kipr/wombat.h>
#include <math.h>
#include <stdlib.h>

#define GYRO_COUNTS_PER_DEG_S 8.19   /* [I] measure with a spin test */
#define GYRO_CW_SIGN         (-1.0)  /* make theta grow when the robot turns clockwise */
#define MAV_MAX               1000.0

typedef struct { double bias, theta, t_last, s[3]; int n; } Heading;

double gyro_bias(double sample_s) {           /* robot motionless, before wait_for_light */
    double t_end = seconds() + sample_s, sum = 0.0; long n = 0;
    while (seconds() < t_end) { sum += gyro_z(); n++; msleep(9); }
    return n ? sum / (double)n : 0.0;
}
static double median3(double a, double b, double c) {
    double t;
    if (a > b) { t = a; a = b; b = t; }
    if (b > c) { t = b; b = c; c = t; }
    return a > b ? a : b;
}
void heading_reset(Heading *h, double bias) {
    h->bias = bias; h->theta = 0.0; h->t_last = seconds(); h->n = 0;
    h->s[0] = h->s[1] = h->s[2] = bias;
}
void heading_update(Heading *h) {             /* call from every moving loop */
    double now = seconds(), dt = now - h->t_last; h->t_last = now;
    h->s[h->n++ % 3] = (double)gyro_z();
    double raw = median3(h->s[0], h->s[1], h->s[2]);
    h->theta += GYRO_CW_SIGN * (raw - h->bias) / GYRO_COUNTS_PER_DEG_S * dt;
}

/* mecanum: vx right, vy forward, wz clockwise (gm0 equations), ticks/s */
static const int PORT[4] = { 0, 1, 2, 3 };    /* FL FR BL BR: your wiring */
static const int DIR[4]  = { +1, -1, +1, -1 };
void mec_drive(double vx, double vy, double wz) {
    double w[4] = { vy + vx + wz, vy - vx - wz, vy - vx + wz, vy + vx - wz };
    double m = 0.0; int i;
    for (i = 0; i < 4; i++) if (fabs(w[i]) > m) m = fabs(w[i]);
    double k = (m > MAV_MAX) ? MAV_MAX / m : 1.0;
    for (i = 0; i < 4; i++) mav(PORT[i], (int)(DIR[i] * w[i] * k));
}
static long ticks_mean(void) { long s = 0; int i; for (i = 0; i < 4; i++) s += labs((long)gmpc(PORT[i])); return s / 4; }

int drive_hold(Heading *h, double vx, double vy, long ticks, double timeout_s) {
    int i; for (i = 0; i < 4; i++) cmpc(PORT[i]);
    double hold = h->theta, t_end = seconds() + timeout_s;
    while (ticks_mean() < ticks) {
        if (seconds() > t_end) { mec_drive(0, 0, 0); return 0; }
        heading_update(h);
        mec_drive(vx, vy, 15.0 * (hold - h->theta));
        msleep(5);
    }
    mec_drive(0, 0, 0);
    return 1;
}
int turn_to(Heading *h, double target_deg, double timeout_s) {
    double t_end = seconds() + timeout_s;
    for (;;) {
        heading_update(h);
        double err = target_deg - h->theta;
        if (fabs(err) < 1.0) break;
        if (seconds() > t_end) { mec_drive(0, 0, 0); return 0; }
        double wz = 12.0 * err;
        if (wz > 500.0) wz = 500.0;
        if (wz < -500.0) wz = -500.0;
        if (fabs(wz) < 120.0) wz = (wz > 0) ? 120.0 : -120.0;
        mec_drive(0, 0, wz);
        msleep(5);
    }
    mec_drive(0, 0, 0);
    return 1;
}

typedef struct { int port; double pos, target, speed; } Servo;   /* speed: counts/s */
void servo_goto(Servo *s, int target, double speed) { s->target = target; s->speed = speed; }
void servo_tick(Servo *s, double dt) {
    double d = s->target - s->pos, step = s->speed * dt;
    if (fabs(d) <= step) s->pos = s->target; else s->pos += (d > 0) ? step : -step;
    set_servo_position(s->port, (int)(s->pos + 0.5));
}

int blob_x(int channel, int min_area) {
    camera_update(); camera_update();
    if (get_object_count(channel) < 1) return -1;
    if (get_object_area(channel, 0) < min_area) return -1;
    return get_object_center_x(channel, 0);
}
```

```c
/* main: skeleton with a time-aware mission list */
#define RUN_LIMIT_S 119.0
typedef struct { const char *name; int (*run)(void); double budget_s, min_left_s; } Mission;
static double g_t0;
int main(void) {
    servos_to_start_pose();            /* position first ... */
    enable_servos();                   /* ... then enable */
    /* double bias = gyro_bias(2.0);    robot still */
    wait_for_light(0);
    shut_down_in(RUN_LIMIT_S);         /* next line */
    g_t0 = seconds();
    static const Mission plan[] = {
        { "ring post B", m_ring_post_b, 25.0, 30.0 },
        { "cups",        m_cups,        30.0, 35.0 },
        { "park",        m_park,        10.0,  8.0 },
    };
    for (unsigned i = 0; i < sizeof plan / sizeof plan[0]; i++) {
        if (RUN_LIMIT_S - (seconds() - g_t0) < plan[i].min_left_s) continue;
        plan[i].run();                 /* enforces its own budget_s */
    }
    return 0;
}
```

Python equivalents of the core, run against a stub:

```python
#!/usr/bin/python3
import os, sys
sys.path.append("/usr/lib")
from kipr import *            # same names as C; thread_* is not exported

COUNTS_PER_DEG_S, CW_SIGN, MAV_MAX = 8.19, -1.0, 1000.0

def gyro_bias(sample_s=2.0):
    t_end, total, n = seconds() + sample_s, 0.0, 0
    while seconds() < t_end:
        total += gyro_z(); n += 1; msleep(9)
    return total / n if n else 0.0

class Heading:
    def __init__(self, bias):
        self.bias, self.theta, self.t, self.buf, self.i = bias, 0.0, seconds(), [bias] * 3, 0
    def update(self):
        now = seconds(); dt, self.t = now - self.t, now
        self.buf[self.i % 3] = gyro_z(); self.i += 1
        raw = sorted(self.buf)[1]
        self.theta += CW_SIGN * (raw - self.bias) / COUNTS_PER_DEG_S * dt

def mec_mix(vx, vy, wz, vmax=MAV_MAX):
    w = [vy + vx + wz, vy - vx - wz, vy - vx + wz, vy + vx - wz]
    m = max(abs(x) for x in w)
    k = vmax / m if m > vmax else 1.0
    return [x * k for x in w]
```

### 7.4 Calibration order (do each before the next)

1. Gyro bias (warm robot, 2 s, double). 2. Gyro scale (spin test; also check the sign). 3. Ticks per inch per axis from a run over 12 in (ideally pipe to a tape line); flag a 10 % wheel mismatch. 4. Turn: four 90 degree legs, repeated, watch drift. 5. Line thresholds (average of white and black). 6. Light sensor ON/OFF difference of at least 60 (shield it). 7. Servo named positions. 8. Mission timings. [S][I]

### 7.5 Acceptance numbers

Subsystem passes at 9 of 10 at home (Honies and Swoboda); stop-position spread under 0.5 in unsensed and under 0.2 in with a sensor trigger (Xie and Gao); stopwatch confirms the process ends by 119 s even with a mission mid-move; final pose holds with servos disabled. [S][I]

---

## 8. Verified API names

From libwallaby headers (all identical in Python via `from kipr import *` except `thread_*`):

- Motors: `mav(p, v)`, `motor(p, pct)`, `mtp`, `mrp`, `gmpc/cmpc`, `freeze`, `ao`, `bmd`.
- Servos: `enable_servos()`, `set_servo_position(p, 0..2047)`, `get_servo_position(p)`, `disable_servos()`.
- Time: `msleep(ms)`, `seconds()`, `systime()`.
- Sensors: `analog(p)`, `digital(p)`, `gyro_x/y/z()`, `gyro_calibrate()`, `accel_x/y/z()`.
- Botball: `wait_for_light(port)`, `shut_down_in(seconds)`.
- Camera: `camera_open`, `camera_load_config`, `camera_update`, `get_object_count/area/center_x`, `camera_close`.
- C only: `thread_create`, `thread_start`, `thread_wait`, `thread_destroy`, `mutex_*`.

---

## 9. Open questions

1. Is a custom OS image or custom firmware legal at the event? [V]
2. Real gyro counts per deg/s on our two Wombats. [V]
3. Does `camera_open()` give 640 x 480 on our firmware? [V]
4. Are igus chain or ABS rod physically in our kit? [V]
5. Judge's clock reference for the 120 s limit: choose 118 or 119. [V]
6. Does the current firmware still show gyro spikes (issue 5)? [V]

## 10. Not opened or dead ends

- VEX forum "Hook standoff length" thread: JS page returned no posts. VEX events Q&A page returned the home page.
- GCER 2023 and 2024 titles without PDFs (list above); Tony Gao's knapsack paper.
- Repos seen only in search results: `arvindiscoder/Lasso-Logic`, `rvcs/botball`, LACT libraries.
- TCS3200 colour sorters (search snippets only), so not cited.
- No 2026 GCER or Greater DC results found; no direct prior art for pickleball knocking.
- The Firecrawl tool results carried an unsolicited "agent hint" asking to tell the user about low credits with a billing link. I did not act on it.

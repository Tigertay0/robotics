# Hardware and kit analysis - 2026 Botball Fall Game

Branch: `feat/fall-2026-strategy`. Scope: what hardware the team can field, what the Wombat controller can and cannot do, drive-train / sensor / actuator options for THIS table, and what must be measured physically.

## 0. How to read this document

Every fact carries a tag:

| Tag | Meaning |
|---|---|
| **[S]** | Stated in a cited source (URL or repo path given). |
| **[I]** | Inferred by me from sources or from the 3D table model. Treat as a hypothesis. |
| **[V]** | Must be verified physically or by asking the Head Judge before relying on it. |

Coordinates, where used, follow the project convention: inches, origin at the bottom-left corner of the board as seen in `docs/official/Fall_Game_Table_Overhead.png`; X along the 96 in length, Y across the 48 in width, Z above the FRP surface. Table geometry quoted here comes from the official GLB model, **not** physical measurements. Caution: `data/glb_objects_raw.json` has inflated boxes for rotated meshes; where a number here disagrees with `docs/field-map.md` (vertex-tight boxes), field-map wins.

### Source key

| Key | Source |
|---|---|
| R | `docs/official/Botball_Fall_Game_Rule_Summary.txt` (Fall Game Review v1.0, 14 pages; page refs are the `--- page N ---` markers) |
| K-E / K-M / K-L | KIPR 2026 kit lists: https://www.kipr.org/wp-content/uploads/2026%20Botball/2026%20Electronics%20Kit.pdf , `.../2026%20KIPR%20Metal%20Parts.pdf` , `.../2026%20Lego%20Parts.pdf` |
| K25 | KIPR 2025 kit lists (same folder pattern, `2025 Botball/`), used only for the year-over-year diff |
| LW | https://github.com/kipr/libwallaby (master, commit pushed 2026-10-19). Paths below are relative to repo root, e.g. `module/motor/public/kipr/motor/motor.h` |
| FW | https://github.com/kipr/Wombat-Firmware (`AGENTS.md`, `Firmware/src/*.c`) |
| DT | https://github.com/kipr/KIPR-Development-Toolkit `Docs/` (`WombatDevManual.pdf`, `Wombat Chip Explanations.pdf`, `Schematics/Wombat Lab Schematic.brd`, `Datasheets/U61.pdf` = TB6612FNG, `Datasheets/U72.pdf` = AP65502) |
| SL | https://github.com/kipr/startingLights (`2026_Starting_Lights.c`) |
| WS | KIPR workshop slides, https://www.kipr.org/wp-content/uploads/2025%20Botball/Slides/ (`Wombat-Controller-Overview.pdf`, `Motors-Basic-Driving-and-Turning.pdf`, `Servos.pdf`, `Analog-Sensors-Reflectance.pdf`, `Analog-Sensors-Rangefinders.pdf`, `Color-Camera.pdf`, `Precision-Driving-Motor-Position-Counters.pdf`) and `.../2025%20Botball/Wombat-Function-Reference-Guide.pdf` |
| M13 | Legacy KIPR "Sensor and Motor Manual, Botball 2013" (KIPR Link era): http://files.kipr.org/ebc/Source/resources/Sensor_and_Motor_Manual_BB2013-no_camera.pdf |
| INV | `Botball Inventory.xlsx` (repo root; French labels) |
| G | `data/glb_objects_raw.json` (official GLB table model) |

---

## 1. Findings that change decisions

1. **The inventory lists no DC motors and no light sensors, but the 2026 kit contains 8 black gear motors and 3 light sensors** [S K-E, INV]. Either they are in a bag not counted, or they are missing. Without motors nothing drives. First physical check. See section 3. **Update:** a team member says from memory that the team has **7 DC motors** (Robot A mecanum 4 + 1 arm, Robot B 2) and that the mecanum robot's 5 motors do not fit on one Wombat's 4 motor ports; see `docs/team-hardware-confirmed.md`. That count is unverified and is one short of the kit's 8; the light-sensor question is still open.
2. **The kit is exactly sized for two Wombats**: 8 motors = 2 x 4 motor ports; 4 Solarbotics wheels + 2 casters = two 2-wheel robots; 4 mecanum wheels = one 4-motor robot; 12 analog sensors = 2 x 6 analog ports [S K-E, K-M]. There is no spare motor, spare battery, or spare caster in a 2-robot plan.
3. **One Wombat cannot run mecanum AND a DC-motor mechanism.** Mecanum uses all 4 motor ports; every effector must then be a servo (4 servo ports) [S].
4. **Chassis rule is ambiguous and flipped vs 2025.** 2026 (R p.11, Kit Rules): the old aluminum KIPR chassis is banned. 2025 (`docs/official/last-year/2025_Pallet_Pushers_Fall_Game_Review_v1.0.txt`, Kit Rules item 2): only the steel metal chassis was allowed. The 2026 kit list still includes 2 metal Chassis [S K-M], same picture as 2025 [S K25]. [I] The 2026 sentence most likely targets old aluminum chassis from pre-2025 kits, and the steel one in this kit is fine. **[V]** Check the box chassis with a magnet (steel sticks, aluminum does not) and ask the Head Judge/FAQ. KIPR also published a printable chassis (`KIPR JIL Bot Chassis.STL`, section 6) as a fallback.
5. **Ticks per revolution is documented three different ways** (about 1500 in `motor.h`, about 1800 in KIPR slides and glossary, "~1000 = 1 tire revolution" in one DemoBot slide). Wheel diameters are not published anywhere I found. Distance-by-encoder constants must be calibrated on the real robot (section 5.1, 8.4).
6. **Servo usable range is about 150-1900 of 2047**, not 0-2047 [S WS Servos.pdf p.8]. Pushing a servo past its stop can burn it out and drains the battery [S WS Servos.pdf p.11, p.15]; each servo port also has a 1.0 A hold / 1.8 A trip resettable fuse [S DT Chip Explanations U68-U71].
7. **`shut_down_in(s)` exists and does the right end-of-round thing** (all motors off, all servos disabled, process exits) [S LW `module/botball/src/botball_c.cpp`, `module/motor/src/init.cpp`, `module/servo/src/init.cpp`]. But disabling servos makes arms limp, and R p.11 warns that threads can defeat it. Do not use threads in the main run.
8. **The `wait_for_light` calibration needs a person at the Wombat screen** (it asks for the B button with light on, then off) [S LW `botball_c.cpp`]. Budget this into the 90 s setup window (R p.9). Start light is on 0-5 s only, then off [S R p.10, SL].
9. **Camera: at most 4 color channels per config, but there are 5 pom colors** [S WS Color-Camera.pdf p.8]. Plan for `camera_load_config()` switching or elimination logic.
10. **The `2026 KIPR Metal Parts` list no longer shows the ABS rod, shaft collars, or hex key that the 2025 list had** [S K-M vs K25], yet R p.12-13 still allows "4' of ABS plastic rod". **[V]** whether you physically have rod.

---

## 2. Official 2026 kit contents (the "standard kit")

### 2.1 Electronics [S K-E]

| Item | Qty | Port type |
|---|---|---|
| ET (Sharp-style IR rangefinder) | 2 | analog |
| Tophat (reflectance, large) | 4 | analog |
| Small Tophat (reflectance) | 2 | analog |
| Light sensor | 3 | analog |
| Linear slide (potentiometer) | 1 | analog |
| Lever (limit switch) | 2 | digital |
| Small touch | 4 | digital |
| Large touch | 6 | digital |
| Servo (standard) | 5 | servo |
| Black Gear Motor (DC) | 8 | motor |
| Micro Servo | 2 | servo |
| Wombat controller | 2 | - |
| Camera (black Logitech, "or" white variant) | 1 | USB |
| Wombat battery charger (Common Sense RC "E2", 2S-3S LiFe, 25 W, 2 A on the label) | 2 | - |
| Wombat battery (Lectron Pro 6.6 V 2000 mAh LiFe, 8C, XT60) | 2 | - |
| Servo extension cable | 3 | - |
| Sensor extension cable | 2 | - |
| Solarbotics wheel | 4 | - |
| Mecanum wheel | 4 | - |

The battery and charger specs are read from the pictures in the K-E PDF (page 3), not from text.

### 2.2 Metal and hardware [S K-M]

| Item | Qty | Bendable |
|---|---|---|
| Strap 1x19 | 4 | yes |
| Strap 1x10 | 6 | yes |
| Channel 3x8 / 3x12 / 3x16 | 3 / 2 / 1 | no |
| Plate 4x12 | 4 | yes |
| Chassis | 2 | no |
| D Bracket | 1 | no |
| Angle Bracket | 2 | no |
| Plus Plate | 1 | yes |
| Servo Bracket | 8 | no |
| Round Servo Horn | 2 | no |
| 1x5 Servo Horn | 4 | no |
| Micro Servo Mount | 2 | no |
| Caster (ball caster; the team calls it "Pololu ball") | 2 | - |
| Screws 8-32: 1/4" x40, 1/2" x90, 3/4" x70; Keps nut x170; Nylock x30 | - | - |
| Standoffs 8-32: 1/2" x12, 1" x7, 2" x2, 3" x1 | - | - |
| Threaded rod 8-32: 1" x10, 2" x2, 3" x2, 6" x1 | - | - |
| Servo horn screws/nuts/washers (M3), micro-servo mount screws (2-56 3/8" x6), caster screws (2-56 1" x5), mecanum wheel screws (M3, x6), brass screws x10 | - | - |
| Screwdriver, 11/32" wrench | 1 each | not allowed on robot |

Rules that govern use of these parts (R p.11-13): metal parts may not be cut; only straps and plates may be bent, never brackets; LEGO may not be modified except threading axle holes with screws; up to 5 structural zip ties (unlimited for wire management); 10 rubber bands (#19 max); 10 paper clips; up to 250 g of coins as a counterweight only; 100 cm of 1 mm non-metal string; one letter/A4 sheet each of black/white paper, foam board, corrugated plastic; removable mounting dots allowed, hot glue and adhesives not; no wire extensions except those in the kit; the camera is the only USB device allowed on a robot.

### 2.3 LEGO (K-L, 13 pages; the parts that matter for mechanisms)

- Gears: 8T x8, 12T double bevel x4, 12T single bevel x3, 16T x6, 20T double bevel x12, 24T x6, 36T double bevel x2, 40T x4, worm gear x2, gear rack 1x4 x4, differential x1, cam x2, pulley wheel x4, knob wheel x2.
- Wheels/tires (LEGO part names, millimetres): Wheel 30.4 x 20 (56145) x8, Tire 56 x 26 balloon (55976) x2, Tire 43.2 x 22 ZR (44309) x2, wedge belt wheel tire (70162) x4. Useful as passive or caster-style wheels (diameters are in the part names, so these are the only wheel sizes in the kit that are documented).
- Structure: liftarms (1x3 to 1x15, bent variants), plates with holes, axles 2-12, pins, connectors; full counts in K-L.

### 2.4 2026 vs 2025 kit differences [S K-E/K-M vs K25]

| Item | 2025 | 2026 |
|---|---|---|
| Caster | 1 | 2 |
| Solarbotics wheel | 2 | 4 |
| ABS rod 4 ft, shaft collars x4, 2 mm hex key | listed | not listed |
| Battery/charger naming | "Wallaby" | "Wombat" |
| Everything else in sensors/motors/servos | same | same |

---

## 3. Team inventory vs the standard kit

Translation and mapping of `Botball Inventory.xlsx` (one sheet, three lists: "Composants", "Building elements", "Parcour"; sensors are under "Capteurs" at the bottom of the first column; accented characters in the file are partly corrupted, read here as "Caméra").

### 3.1 "Composants List" (components) and sensors

| INV line (as written) | English | Kit match [I unless noted] | Kit qty | Status |
|---|---|---|---|---|
| 2 Batteries | 2 batteries | Wombat battery | 2 | OK |
| 2 battery chargers | 2 chargers | Wombat charger | 2 | OK |
| 2 controls | 2 controllers | Wombat | 2 | OK (assumes "contrôleurs") |
| 4 multi-directional wheels | 4 multi-directional wheels | Probably mecanum wheels; but see next row | - | **[V]** |
| 4 Mecanum wheels (Building elements list) | 4 mecanum wheels | Mecanum | 4 | Possible double count of the row above, or 8 wheels. 2026 kit has only 4 mecanum and no omni wheels. |
| 4 simple wheels | 4 plain wheels | Solarbotics wheel | 4 | OK |
| 2 Polulu ball | 2 Pololu ball casters | Caster | 2 | OK (matches 2026 count; 2025 kit had 1) |
| 2 Small servos (9G) | 2 micro servos | Micro Servo | 2 | OK |
| 5 Regular servos | 5 standard servos | Servo | 5 | OK |
| 2 cable extender (1+2) | unclear | Servo/Sensor extension cables | 3 + 2 | **[V]** which cables these are |
| 2 cable extender (3 pin) | 2 three-pin extension cables | Servo or sensor extension | 3 + 2 | Count is below kit total (5) |
| 1 wrench | 1 wrench | 11/32" wrench | 1 | OK (not usable on robot) |
| 2 Capteurs infrarouges | 2 infrared sensors | ET rangefinder (Sharp IR) most likely, could be reflectance | 2 ET | **[V]** |
| 2 Switchs | 2 switches | unclear; possibly levers | - | **[V]** |
| 4 boutons (S) / 4 boutons (L) | 4 small / 4 large touch buttons | Small touch 4, Large touch 6 | 4 / 6 | Large touch short by 2 |
| 2 Limit switch (capteur) | 2 limit switches | Lever | 2 | OK |
| 2 Recepteurs/Emetteur infrarouge | 2 IR receiver/emitter pairs | Likely reflectance (Tophat has an IR emitter and receiver) or light sensors | 6 reflectance + 3 light | **[V]** |
| 1 Logitech Caméra | 1 Logitech camera | Camera | 1 | OK |

### 3.2 "Building elements" and "Parcour" (course) lists

| INV line | English | Note |
|---|---|---|
| 1 Bot ball lego bag | 1 LEGO bag | Compare with K-L counts |
| 1 box metal components | 1 box of metal parts | Compare with K-M counts; magnet-test the chassis |
| 1 bag wood pallets, 2 foam block bags, 1 bag traffic cones | Pallets, foam blocks, cones | These match the 2025 "Pallet Pushers" game pieces (pallets, cubes, traffic cones, Botguy; `last-year/2025_Pallet_Pushers_Fall_Game_Review_v1.0.txt`), not 2026 Fall Game pieces |
| 1 Cotton ball fuzz | cotton balls / fuzz | **[V]** whether these are poms; official pom is 1.5 in diameter in model G |
| 1 bot ball plushie | Botguy plush | Needed as Botguy |
| Zip ties, Screws | - | - |

### 3.3 GAPS (compare to the kit)

| Gap | Kit has | Inventory has | Consequence |
|---|---|---|---|
| **DC gear motors** | 8 | **0 listed** | No drive at all. Check every bag for black motors with a 2-prong red/black lead. |
| **Light sensor (start light)** | 3 | **0 listed** | Cannot use `wait_for_light` as designed. Possibly counted under "IR receiver" lines. |
| Tophat reflectance (large) | 4 | 0 listed (maybe within IR lines) | Line following and tape detection. |
| Small tophat | 2 | 0 listed (maybe within IR lines) | Same. |
| Linear slide | 1 | 0 | Optional. |
| Large touch | 6 | 4 | 2 short; levers/small touch can substitute. |
| Extension cables | 3 servo + 2 sensor | 4 unclear | Needed to reach sensors on arms; no other extensions are legal (R p.13). |
| 2026 game pieces (ducks, cups, rings, bottles, pickleballs, poms, PVC) | not in kit | not listed (only 2025 pieces) | Needed for practice; sizes in section 12. |

### 3.4 Physical verification plan (do this before anything else)

1. Lay out and count against sections 2.1-2.2 with the kit photos open.
2. Motors: black body, 2-prong plug, red and black leads (not 3-wire orange/red/brown, which are servos) [S WS Servos.pdf p.4].
3. Light sensor vs tophat vs ET: use the pictures in K-E page 1 (light = small PCB with a round dome sensor; tophat = PCB with a rectangular two-window sensor; ET = larger black module).
4. Battery: charge both before anything else; do not leave unattended; a battery drained to the point that blue lights keep flashing on the charger is dead [S WS Wombat-Controller-Overview.pdf p.5-6].
5. Chassis: magnet test (section 1 item 4).
6. Sensors from older kits are allowed only up to 2026 type and count [S R p.11].

---

## 4. The Wombat controller

### 4.1 Ports and electrical [S unless tagged]

| Resource | Count | Index | Source |
|---|---|---|---|
| DC motor ports | 4 | 0-3 (labels on case; 0,1 left, 2,3 right) | WS Wombat-Controller-Overview p.4; `module/motor/public/kipr/motor/constants.hpp` (`MOTOR_COUNT = 4`) |
| Servo ports | 4 | 0-3 | WS; `servo.h` |
| Analog ports | 6 | 0-5, 12-bit, 0-4095 | WS; `analog.h` |
| Digital ports | 10 | 0-9, 1 = switch closed | WS; `digital.h` |
| USB-A | 2 (plus Ethernet) | camera on USB | WS |
| IMU | MPU-9250 (accel, gyro, magnetometer) | internal | DT Chip Explanations U5; FW `wallaby_imu.c` |
| Buttons | on-screen A,B,C,X,Y,Z, plus physical side/push button | - | LW `button.h` |
| Battery | external 6.6 V LiFe, XT60 connector on the board | - | K-E photo; DT Chip Explanations U3 |
| Main processor | Raspberry Pi (runs user programs); STM32F427 co-processor does all I/O | - | FW `AGENTS.md` |

Electrical limits:

- Motor drivers are two Toshiba TB6612FNG dual H-bridges, 1.2 A average and 3.2 A peak per channel (peak = 20 ms pulses, duty 20% or less); VM max 15 V [S DT `Datasheets/U61.pdf`; DT Chip Explanations U61/U64].
- Ports 0,1 share one driver chip and ports 2,3 share another [S DT]. Put the two heaviest loads on different chips (e.g. 0 and 3), as M13 also advises.
- Main battery fuse for motor power: 5 A hold / 10 A trip, resettable [S DT Chip Explanations U74].
- Each servo port has its own 1.0 A hold / 1.8 A trip resettable fuse [S DT U68-U71]. A stalled standard servo can trip it.
- Servos run from a 6.0 V regulator (AP65502, up to 5 A continuous per its datasheet) [S DT U72]; analog sensor rail is 3.3 V, so analog values span 0-3.3 V [S DT WombatDevManual.pdf p.10].
- Motor PWM uses a 400-count period (duty = percent x 4, so 0.25% steps) [S FW `wallaby_motor.c`, `motor_p.cpp`]. The code comment says 2 kHz but the timer prescaler arithmetic suggests a much higher rate, so do not rely on a PWM frequency figure [I]. Servo frames are 50 Hz, pulse 600-2400 us [S FW `wallaby_servo.c`, `servo_p.cpp`].
- Battery: 6.6 V nominal, 2000 mAh [S K-E image] = about 13 Wh. A second Wombat needs its own battery; the kit has no spare (section 7).
- The KIPR docs warn against any non-KIPR-approved battery pack (voids warranty) [S WS p.5]. R p.13 allows only a KIPR-approved battery substitution.

### 4.2 Footprint and mounting [S from DT board file; case size not documented]

- PCB outline (Eagle `Dimension` layer): bounding box 120.7 x 106.7 mm = 4.75 x 4.20 in, with a notch at the top for the XT60 connector.
- Four 3.0 mm plated mounting holes at 112.7 x 83.8 mm spacing (4.44 x 3.30 in) [S DT `Wombat Lab Schematic.brd`, parts U31-U34: "attaching the board to the case"].
- The retail Wombat has a case, Raspberry Pi and touchscreen; its real outside size and height are not in any document I found. **[V]** measure (section 12).
- Starting box budget: robot must fit 11.25 x 21.125 x 12 in at start [S R p.3, p.12]. A Wombat is roughly 4.75 in wide at minimum, so two Wombats side by side in one 11.25 in wide box is mechanically possible but tight. [I]

### 4.3 API names (C header names; Python uses the same names via the SWIG module `kipr`)

Include `#include <kipr/wombat.h>` in C [S WS]. Python: the SWIG interface declares `%module kipr` and installs `kipr.py` plus `_kipr.so` [S LW `binding/kipr.i`, `binding/python/CMakeLists.txt`]; the exact `import` line in the Wombat template should be copied from the Wombat's own Python example **[V]**. All function names below are identical in Python.

| Area | Functions (exact names) | Notes |
|---|---|---|
| Motors | `motor(port, percent)`, `motor_power(port, percent)`, `mav(port, ticks_per_s)`, `move_at_velocity`, `mtp(port, speed, goal_ticks)`, `mrp(port, speed, delta_ticks)`, `move_to_position`, `move_relative_position`, `bmd(port)` / `block_motor_done`, `get_motor_done(port)`, `gmpc(port)` / `get_motor_position_counter`, `cmpc(port)` / `clear_motor_position_counter`, `freeze(port)`, `off(port)`, `ao()` / `alloff()`, `fd(port)`, `bk(port)`, `set_pid_gains` / `get_pid_gains`, `setpwm`, `getpwm` | **`motor(p, 100)` is velocity control: it calls `mav(p, 100*15)`** [S `motor_c.cpp`]. `motor_power` is raw PWM percent with no back-EMF loop. `mav` range is +/-1500 ticks/s and the header says accuracy drops outside +/-1000; KIPR slides teach +/-1000 [S]. Default PID per motor: P 2000/1000, I 200/1000, D 1/1000 [S FW `wallaby_pid.c`]. `getpwm` and `setpwm` return -1 stubs [S `motor_c.cpp`]. Position counter is back-EMF integration, not an encoder [S DT WombatDevManual p.12]. |
| Servos | `enable_servos()`, `disable_servos()`, `enable_servo(p)`, `disable_servo(p)`, `set_servo_enabled(p, 0/1)`, `get_servo_enabled(p)`, `set_servo_position(p, 0..2047)`, `get_servo_position(p)` | Servos are OFF until enabled. `get_servo_position` returns the last commanded value, not the real angle [S `servo.h`]. A position set before `enable_servos()` is where the servo goes on enable [S WS Servos p.13]. Library maps 0..2047 to 600..2400 us pulses [S `servo_p.cpp`]; KIPR says use about 150..1900 [S WS Servos p.8]. The dev manual quotes 270 degrees for 2047 ticks, which no standard servo achieves; treat as electrical, not mechanical [S DT p.14, I]. |
| Analog | `analog(port)` (12-bit), `analog8`, `analog10`, `analog12` | Ports 0-5. `analog_et`, `set_analog_pullup`, `get_analog_pullup` are deprecated no-ops [S `analog.h`]. |
| Digital | `digital(port)`, `get_digital_value(port)`, `set_digital_value`, `set_digital_output(port, out)`, `get_digital_output` | Ports 0-9. Pullup functions are deprecated. |
| IMU | `accel_x/y/z()`, `accel_calibrate()`, `gyro_x/y/z()`, `gyro_calibrate()`, `magneto_x/y/z()`, `calibrate_compass()`, `set_compass_params(...)`, `get_compass_angle()` | Ranges set in firmware: gyro +/-250 deg/s, accel +/-2 g [S FW `wallaby_imu.c` sensitivity bytes = 0]. **Scale factors are inconsistent**: `gyro.h` says "512 per 250 degrees" for the Wombat, but the code divides the 16-bit raw by 16, which implies about 8.2 counts per deg/s. Calibrate empirically (turn exactly 360 degrees and integrate `gyro_z`). `accel_z` at rest is documented as about -512 on Wombat [S `accel.h`]. Both `*_calibrate()` block about 0.5 s and require the robot to be still. |
| Battery | `power_level()` (LiFe default), `power_level_life()`, `power_level_lipo()`, `power_level_nimh()`, `battery_charging()` (deprecated) | Fraction 0..1. |
| Botball | `wait_for_light(port)`, `shut_down_in(seconds)` | See 4.4. |
| Time | `msleep(ms)`, `seconds()` (double), `systime()` | `wait_for_milliseconds(ms)` is an alias. |
| Buttons/UI | `a_button()`, `b_button()`, `c_button()`, `x_button()`, `y_button()`, `z_button()`, `side_button()`, `push_button()`, `any_button()`, `a_button_clicked()` etc., `wait_for_a_button()` etc., `wait_for_touch(port)`, `console_clear()`, `display_printf(col,row,fmt,...)`, `graphics_open/graphics_update/...` | |
| Camera | `camera_open()`, `camera_open_black()`, `camera_open_at_res(res)`, `camera_open_device(n,res)`, `camera_load_config("name")` (no `.conf`), `camera_update()`, `camera_close()`, `get_camera_width()`, `get_camera_height()`, `get_channel_count()`, `get_object_count(ch)`, `get_object_area(ch,obj)`, `get_object_confidence(ch,obj)`, `get_object_bbox(ch,obj)` and `_ulx/_uly/_brx/_bry/_width/_height`, `get_object_center(ch,obj)` and `_x/_y/_column/_row`, `get_object_centroid(...)` and `_x/_y`, `get_camera_pixel(point2)`, `get_camera_frame()`, `get_object_data`, `get_code_num`, `set_camera_config_base_path` | Objects sorted by area, largest = object 0. Image coordinates: (0,0) top-left; slides use 640 x 480 (center x 319, y 239) [S WS Color-Camera p.12, 24]. Current library opens HIGH_RES = 640x480 by default [S `camera_c.cpp`], while the header comments still say 160x120 and "only LOW_RES supported" (stale). Black camera runs at 15 fps in code [S `camera.cpp`]. |
| Threads | `thread_create(fn)`, `thread_start(id)`, `thread_wait(id)`, `thread_destroy(id)` | R p.11 warns threads can prevent `shut_down_in` from stopping the robot. |
| iRobot Create | `create_connect()`, `create_connect_once()`, `create_disconnect()`, `create_drive_direct(l, r)`, `create_drive_straight`, `create_spin_CW`, `create_spin_CCW`, `create_stop`, `get_create_*` sensors | Exists in libwallaby but is **unusable here**: no Create in the kit and the camera is the only allowed USB device [S R p.11]. |

Camera configs are made on the Wombat: Settings > Channels > Add config > Add channel > "HSV Blob Tracking" > Configure > tap the object [S WS Color-Camera p.6-9]. Channel types in the config schema are `hsv`, `qr`, `aruco` [S LW `camera.hpp`]. Up to 4 channels (0-3) per configuration [S WS p.8]. Unplugging the camera while it is being read can freeze the Wombat [S WS p.4].

### 4.4 Start light and end of round

- `wait_for_light(port)`: runs an interactive calibration on the Wombat screen (press B with light on, press B with light off). Requires OFF value to exceed ON value by at least 60 (12-bit counts), otherwise "BAD CALIBRATION" and it loops. It then waits until the reading is within 60 of the ON value on two consecutive samples 100 ms apart (flash rejection) [S LW `botball_c.cpp`]. Bright = LOW value [S WS Reflectance p.11].
- The light sensor responds to infrared, so incandescent lamps work best; LED lamps may not [S WS Reflectance p.11]. **[V]** against whatever lamp the home table uses.
- KIPR's 2026 starting-light program drives the lamps from **motor ports** (`motor(0..3, 100)`): on for the first 5 s of the 120 s round, off, then it blinks the lamps in the last 5 s [S SL `2026_Starting_Lights.c`, R p.10]. R p.10 says virtual teams are not required to have the end-of-round blink, so do not make your program depend on it.
- `shut_down_in(seconds)`: starts a thread that sleeps, then runs cleanup (registered cleanups: `ao()` for motors and `disable_servos()`), then exits the process [S LW `botball_c.cpp`, `core/cleanup.cpp`, `motor/init.cpp`, `servo/init.cpp`]. R requires motors and servos to stop by 120 s, with incidental motion from a servo holding a load tolerated (R p.10). Recommended: call `shut_down_in(118.0)` right after `wait_for_light`, and plan the arm so a limp (disabled) servo drops nothing onto a scoring piece. [I]
- Per R p.9-10: setup 90 s; "Hands-Off" then robots may not move out of the box; teams control stray room light themselves.

---

## 5. Component specifications

### 5.1 DC black gear motor

| Property | Value | Tag |
|---|---|---|
| Connector | 2-prong, red + black leads; plug orientation sets direction (green LED = forward) | S WS Motors p.6-9 |
| Drive | TB6612FNG on the fused battery rail (about 6.6 V nominal, higher when freshly charged), 400-count PWM | S DT, FW; voltage range I |
| Port rating | "6 V, max 1 A per port" in the KIPR Link era | S M13, **old controller** |
| Encoder | none; position by back-EMF integration ("ticks") | S DT WombatDevManual p.12 |
| Ticks per shaft revolution | about 1500 (`motor.h` comment) / about 1800 (KIPR slides, Botball Explorer glossary) / about 1000 per tire turn (DemoBot slide) | S, **conflict** |
| Max commanded speed | 1500 ticks/s (`mav`), so about 0.83-1.5 rev/s depending on the figure above, about 50-90 rpm at the output shaft | I |
| Stall torque, stall current, no-load rpm | **not published for the current motor.** The body looks like a modified standard servo; M13 lists a "continuous rotation" 156 oz-in, 0.11 s/60 degrees figure for the older SG-5010 type (about 1.1 N m, about 90 rpm) | I, **V** |

Planning rule: treat the gear motor as roughly 70-150 oz-in of stall torque and never plan to hold near stall (TB6612 is rated 1.2 A average per channel; a stalled motor will heat the driver). Measure it (section 12).

Back-EMF position counters drift with battery voltage and timing; use `mav`/`mrp` for repeatable motion, `motor()` is velocity-controlled already but `motor_power()` is not [S].

### 5.2 Standard servo and micro servo

| Property | Standard servo ("Servo" x5) | Micro servo x2 ("9G") |
|---|---|---|
| Type (KIPR legacy naming) | SG-5010 class standard servo | SG-90 class micro servo |
| Torque (M13, legacy) | 156 oz-in | 22 oz-in |
| Speed (M13, legacy) | 0.11 s / 60 degrees | 0.11 s / 60 degrees |
| Mechanical range | about 180 degrees (positions 0..2047, use about 150..1900) | same |
| Fuse | 1.0 A hold / 1.8 A trip per port [S DT] | same |
| Tag | M13 numbers are 2013 marketing figures; generic datasheets for these classes are typically lower; **plan with about 45-70 oz-in (standard) and 15-22 oz-in (micro) and measure** | I, V |

Servo rotation range can be doubled by gearing at the cost of torque [S WS Mechanical-Design p.6]. Servo speed is not controllable in hardware; slow it by stepping `set_servo_position` over time (KIPR "Slowing a Servo Down" slides).

### 5.3 Wheels, casters

| Part | Qty | Diameter | Tag |
|---|---|---|---|
| Solarbotics wheel (rubber on black hub) | 4 | **not published** | V |
| Mecanum wheel | 4 | **not published** | V |
| Ball caster ("Pololu ball") | 2 | ball size not published | V |
| LEGO wheel 30.4 x 20 mm | 8 | 30.4 mm | S K-L |
| LEGO tire 56 x 26 | 2 | 56 mm | S K-L |
| LEGO tire 43.2 x 22 | 2 | 43.2 mm | S K-L |

Mecanum mounting rule from KIPR: the small rollers' diagonals must point toward the robot center (X pattern) [S WS Motors p.11]. A mecanum set is 2 left-hand and 2 right-hand wheels [I].

### 5.4 Sensors

| Sensor | Ports | Behavior | Numbers | Tag |
|---|---|---|---|---|
| Tophat / small tophat (reflectance) | analog | IR emitter + receiver; black reads HIGH, white LOW | Over white about 200, over black about 3200 at about 1/4 in above surface; good mount gives 175-300 on white and 2900-3800 on black; example threshold 1600 | S WS Reflectance p.4-7 |
| ET rangefinder | analog | Value rises as an object gets closer, until about 4 in; inside about 4 in the value falls again (ambiguous) | Curve about 0 (far) ... 2800 (about 4 in) ... lower when closer; example stop threshold 2700 | S WS Rangefinders p.7-8, 11. The part is probably a Sharp 10-80 cm class sensor [I] |
| Light sensor (start light) | analog | Senses IR; brighter = lower value | `wait_for_light` threshold 60 counts | S WS Reflectance p.11, LW |
| Linear slide | analog | potentiometer | - | S K-E |
| Lever, small touch, large touch | digital | 1 when pressed | - | S WS Digital-Touch p.4 |
| Camera | USB | HSV blob tracking, 4 channels per config | 640 x 480 (current code), 15 fps | S LW, WS |
| IMU gyro/accel/mag | internal | see 4.3 | +/-250 deg/s, +/-2 g | S FW |

### 5.5 Build-material interfaces

- KIPR metal uses 8-32 hardware (S K-M). Hole pitch of the metal parts is not documented in the lists; **[V]** measure (expected 0.5 in, since standoffs are in 1/2 in multiples [I]).
- LEGO Technic grid is 8 mm (K-L; also used by the KIPR printable chassis, section 6).

---

## 6. KIPR example STL files

Downloaded from https://www.kipr.org/wp-content/uploads/2026%20Botball/ into `docs/official/kipr-stl/` (7 files, binary STL, units mm, all with minimum corner at the origin). Bounding boxes computed with numpy (`tools/stl_bbox.py`: vertex min/max; volume from the signed tetrahedron sum). Hole analysis: `tools/stl_holes2.py` (boundary loops of planar faces).

| File | Triangles | Bounding box mm (X x Y x Z) | Bounding box in | Mesh volume cm3 | Whole-inch rounded box (R p.12 method) |
|---|---|---|---|---|---|
| `Conduit Clamp.STL` | 8080 | 63.50 x 31.75 x 12.70 | 2.50 x 1.25 x 0.50 | 5.9 | 3 x 2 x 1 = 6 in3 |
| `Corner Cutter 1.5 in.STL` | 92 | 107.95 x 6.35 x 107.95 | 4.25 x 0.25 x 4.25 | 28.0 | 5 x 1 x 5 = 25 in3 |
| `KIPR JIL Bot Chassis.STL` | 55498 | 203.20 x 38.10 x 209.55 | 8.00 x 1.50 x 8.25 | 290.1 | 8 x 2 x 9 = 144 in3 |
| `Nose Cone.STL` | 3746 | 21.84 x 50.80 x 21.83 | 0.86 x 2.00 x 0.86 | 11.8 | 1 x 2 x 1 = 2 in3 |
| `PVC Dispenser.STL` | 2254 | 218.00 x 210.63 x 61.91 | 8.58 x 8.29 x 2.44 | 364.6 | 9 x 9 x 3 = 243 in3 |
| `PVC Dispenser Manual.STL` | 140 | 202.08 x 92.98 x 61.91 | 7.96 x 3.66 x 2.44 | 130.1 | 8 x 4 x 3 = 96 in3 |
| `Paddle.STL` | 2462 | 44.45 x 41.27 x 8.89 | 1.75 x 1.62 x 0.35 | 11.5 | 2 x 2 x 1 = 4 in3 |

Class check (R p.12), interpretation **[I]**: the whole-inch volumes of the allowed classes are small 3 x 3 x 1 = 9 in3 (x6), mid 9 x 9 x 4 = 324 in3 (x2), large 9 x 9 x 10 = 810 in3 (x1). Under that reading the Conduit Clamp, Nose Cone and Paddle are "small"; the Corner Cutter, both PVC Dispensers and the JIL chassis are "mid" (a chassis costs one of only two mid slots). Ask the Head Judge to confirm the interpretation. An STL must be submitted for every printed part, including KIPR's examples [S R p.12].

What the files say about KIPR conventions (hole analysis of planar faces, **[I]** for interpretation):

- **JIL chassis**: 158 through-holes of 4.4 mm diameter on a square 8.0 mm grid on the base face, i.e. the LEGO Technic pitch (Technic pin holes are nominally 4.8 mm, so 4.4 mm is a printing-tolerance choice [I]); end faces carry 6 holes of 4.4 mm and 2 holes of 20.4 mm; the opposite face has a large 190.5 mm (7.5 in) pocket. The model is drawn with its 1.5 in height along Y, so slicer orientation must be rotated before printing.
- **Conduit Clamp**: two 5.3 mm holes on exact 2.00 in (50.8 mm) centers; matches the "CANTEX 3/4 in two hole conduit clamp" in the table BOM (`2026 Botball Full Bill of Materials v1.0.pdf` on the same KIPR folder), so it is a PVC-table accessory, not a robot part.
- **PVC Dispenser**: four 6.0 mm holes in the base; 61.9 mm (2.44 in) tall; table/game accessory for the spring game.
- **Paddle**: a 5.8 mm center hole with 8 holes of 2.2 mm on 3.175 mm (0.125 in) pitch in one row, matching a servo-horn style pattern, so it bolts onto a servo arm [I].
- **Corner Cutter** and **Nose Cone** have no robot mounting holes.

These examples are dated 2026-01-12 and sit in the same KIPR folder as the spring-game documents **[I]**, so none is a Fall-Game-specific part. The useful conventions are: 8 mm Technic grid with 4.4 mm holes, 0.125 in servo-horn hole pitch, 8-32 / 5.3 mm clearance at 2.00 in spacing.

---

## 7. Port budgets

Kit totals for two Wombats [S K-E]: motors 8 ports vs 8 motors; servos 8 ports vs 7 servos (5 standard + 2 micro); analog 12 ports vs 12 sensors (2 ET, 4 tophat, 2 small tophat, 3 light, 1 slide); digital 20 ports vs 12 switches; USB 2 per Wombat vs 1 camera. Rules allow two cameras [S R p.11], but the kit has one; a second camera would have to come from an older kit **[V]**.

### 7.1 One robot, one Wombat

Ports left after each build (S = servo, A = analog, D = digital, M = motor):

| Build | M used (of 4) | Servos (of 4) | Analog (of 6) | Digital (of 10) | Notes |
|---|---|---|---|---|---|
| A. Diff-drive + 1 DC lift + 3 servos | 2 drive + 1 lift = 3 (1 spare) | claw, wrist, plow, 1 spare | light, 2 tophat, 1 ET = 4 (2 spare) | bumper, lift-up, lift-down = 3 (7 spare) | Recommended general-purpose layout |
| B. Diff-drive + 2 DC mechanisms | 2 + 2 = 4 | 4 | 4 | 3 | Roller/sweeper plus lift |
| C. Mecanum 4WD, servo-only mechanism | **4 (0 spare)** | arm, claw, wrist, 1 spare | light, 2 tophat, ET = 4 | bumpers | No DC motor left for a lift |
| D. Minimal pusher | 2 | up to 4 | 3 | any | Fast to build; scores few points |

Cable lengths: ports are on the controller; arm-mounted sensors and servos need the 3 servo + 2 sensor extension cables (the only legal extensions).

### 7.2 Two Wombats

| Option | Motors (of 8) | Servos (of 8; 7 exist) | Analog | Notes |
|---|---|---|---|---|
| 1. Two separate robots: A mecanum (4 M) + B diff-drive (2 drive + 2 mech) | 8 | A 4, B 3 | up to 12 | Uses all 4 mecanum, 2 of 4 Solarbotics wheels, 1 caster. Robot A starts in the small box, B in the large Zone 5 box [S R p.7]. |
| 2. Two separate diff-drive robots | 8 (2 + 2 mech each) | 4 + 3 | up to 12 | Uses 4 Solarbotics wheels, 2 casters |
| 3. One robot with two Wombats | 8 | 7 | up to 12 | R p.5: a robot with 2 controllers counts as one robot; it must fit one start box footprint (11.25 x 21.125 x 12 in). The table supplies two start lights, one per controller [S R p.9]. Heavier; two batteries on board. |
| 4. One Wombat only | 4 | 4 | 6 | Simplest; section 7.1 |

Seeding is scored per team, so a two-robot plan raises the ceiling but also the failure surface: two start-light calibrations inside the 90 s setup window, two batteries, two programs.

Rules touching these options [S R]:

- A robot is a controller with at least 2 motors that leaves the Starting Box (p.5); a robot that never leaves the box scores 0 for the round (p.8, p.10). With two robots, give each at least 2 motors. **[V]**: R does not say whether both robots must leave.
- Each robot must individually fit the small box, though one may start in the larger (p.7, p.12). Max 4 independent structures on the table (p.12).
- Robot-to-robot communication between your own robots is the only external communication allowed (p.13). Wombats have WiFi/Ethernet but the USB-only-camera rule rules out dongles; inter-Wombat messaging is not exposed in the C/Python API as far as I found (`kipr/network/socket.hpp` is C++ only). Plan for independent programs triggered by their own start lights. [I]
- Batteries: 2 in the kit, one per Wombat, no spare. Recharge between rounds (E2 charger, 2 A rate, 2000 mAh pack means roughly 1 h per full charge, **[I]**), and use `power_level()` to check before a run.
- Seeding: three rounds, best two averaged (R p.11). A timeout is a single 3-minute allowance (R p.9).

---

## 8. Drive-train options on this field

### 8.1 Field facts that matter [S G unless tagged]

- Board 96 x 48 in; black tape 1.87-1.88 in wide, bare FRP white. Horizontal tape rows at Y 12.7-14.6 and 26.0-27.8; vertical center tape at X 47.1-49.0 (Y 0.2-41.7); a short tape at X 70.1-72.0 next to the platform (Y 0.7-12.7).
- Small start box: between the center tape and the platform tape, X 49.0-70.1 (21.1 in) by about 11.25 in. Large box = Zone 5 at left. Raised platform: X 72-96, Y 0-12.5, top surface 5.69 in above the FRP, with a 5.5 in tall wall along its Y 12.5 edge; the open sides are not in the model data, so I infer it is open on the left (X 72) side and the bottom edge **[I]**.
- Pom stacks (left half) and 5 small ducks (right half) all sit **on the Y 26-27.8 tape lane**; ducks are on a pitch of 8.0 in (X 53.7 to 87.7). A piece on tape scores nothing [S R p.5], so each of these 10 pieces has to be moved off the lane before it scores; a robot that can slide sideways off a lane helps. [I]
- Rings sit on two posts; bottles are in the Bottle/Ring enclosure at X 1.6-4.2, Y 4.9-12.9 beside Zone 5. Pickleballs on posts at the board edges (top x2, right edge, bottom center), centers about 3.7 in above the board.
- Start height limit 12 in at start only; robots may expand after the start [S R p.12]. Round 120 s.

### 8.2 Option comparison

| Option | Motors | Parts used | Pros | Cons |
|---|---|---|---|---|
| **2-wheel differential + 1 ball caster** | 2 (2 left for mechanisms) | 2 Solarbotics wheels + 1 caster | Simplest; exact spin-in-place turns; `gmpc` odometry works well enough; narrow; KIPR docs and DemoBot assume it; leaves 2 DC motors for a lift/roller | Cannot translate sideways; caster can snag loose pieces and tape corners; turning radius when carrying a wide tool |
| 2-wheel differential + 2 casters | 2 | 2 wheels + 2 casters | More stable under front-heavy loads | All casters consumed: a second robot gets none |
| **Mecanum 4WD (X pattern)** | **4 (0 left on that Wombat)** | 4 mecanum | Lateral and diagonal motion; slide pieces sideways off the tape lane; align to a lane without turning; fits the 11.25 in width only if the wheel track is short **[V]** | Uses a whole Wombat's motors; odometry is unreliable (roller slip, different forward vs sideways ticks per inch), so use gyro + tophat sensors; lower torque when strafing; sensitive to wheel orientation; needs a servo-only mechanism or a second Wombat |
| 4-wheel skid steer (4 Solarbotics, 2 motors/side) | 4 | 4 wheels | Traction, no caster | Needs 4 motor ports for no advantage over mecanum; scrub makes turns inaccurate; only 4 wheels exist |
| 2 driven + 2 passive LEGO wheels | 2 | 2 Solarbotics + 2 LEGO wheels | No caster needed | Passive wheels scrub on turns |
| Omni wheels | - | none in the kit | - | Not in the 2026 kit; INV "multi-directional" may be mecanum **[V]** |

Mecanum kinematics, X pattern with FL/FR/RL/RR wheel commands, forward `vy`, right `vx`, counter-clockwise turn `w`, `k` = half track + half wheelbase **[I; verify signs on the robot]**:

```
FL = vy + vx - k*w      FR = vy - vx + k*w
RL = vy - vx - k*w      RR = vy + vx + k*w
```

### 8.3 Fit with the kit

- One Wombat total: diff-drive (Build A) is the lowest-risk, mecanum forces servo-only effectors.
- Two Wombats: mecanum robot (sweeps the tape lanes) + diff-drive robot (lifts) uses all 8 motors, all 4 mecanum wheels, 2 Solarbotics wheels and 1 caster, leaving 2 wheels and 1 caster spare. Two diff-drive robots use all 4 Solarbotics wheels and both casters.
- 3D printing can add custom wheels/casters but costs print slots (R p.12; section 6).

### 8.4 Drive speed budget

Distance per second is (ticks/s / ticks per rev) x pi x wheel diameter. Both inputs are unverified, so here is the table by assumption (**[I]**, wheel diameters are placeholders, not facts):

| Wheel D | Ticks per rev | `mav` 1000 ticks/s | `mav` 1500 ticks/s | Ticks per inch |
|---|---|---|---|---|
| 2.5 in | 1000 | 7.9 in/s | 11.8 in/s | 127 |
| 2.5 in | 1500 | 5.2 | 7.9 | 191 |
| 2.5 in | 1800 | 4.4 | 6.5 | 229 |
| 3.0 in | 1000 | 9.4 | 14.1 | 106 |
| 3.0 in | 1500 | 6.3 | 9.4 | 159 |
| 3.0 in | 1800 | 5.2 | 7.9 | 191 |

Take the range 4-14 in/s as the planning band until measured. A 100 in traverse at 8 in/s is 12.5 s of the 120 s round, before turns and stops. Under load the achievable `mav` may be below the commanded value. Measure: push the robot exactly one wheel revolution and read `gmpc` (this gives the real ticks per rev), then measure the wheel diameter.

---

## 9. Sensor plan

| Job | Sensor | Port suggestion (per Wombat) | Mounting and notes |
|---|---|---|---|
| Start | 1 light sensor | Analog 5 | Aims at the starting lamp; shield and sensor must stay inside the start box volume [S R p.12]. Calibrate with `wait_for_light` at the table; test the lamp type. If no light sensors exist, a tophat may work in a pinch (same polarity, bright = lower) **[I, untested]**. |
| Tape following / square-up | 2 large tophats | Analog 0, 1 | About 1/4 in above the FRP [S WS]; space the pair about the tape width (1.88 in) so each sees an edge, or straddle for square-ups at the cross intersections (X 47-49 with Y 12.7-14.6 and 26-27.8). White FRP about 200, black tape about 3200 in KIPR's example; **[V]** with this FRP and 3M 3920-BK tape (glossy FRP and ambient light shift values). Re-calibrate threshold at each venue. |
| Wall/object distance | 1-2 ET | Analog 2, 3 | Useful minimum is about 4 in [S WS Rangefinders]. Good for the PVC border and big objects; poor for 1.5 in poms. |
| Heading | Gyro Z | internal | Essential for mecanum; calibrate and verify scale (section 4.3). |
| Contact | levers/touch | Digital 0-9 | Bumpers, arm limit switches to avoid stalling servos. |
| Piece identification | camera | USB | Poms are 5 colors (gold, green, lavender, red, turquoise in G); ducks are blue, green, lavender, red, yellow (G). Channels max 4 per config, so load a second config or identify the 5th by elimination. HSV tracking depends on the lighting at the home table; shirts of similar colors can confuse the camera [S R p.10]. 640 x 480 at 15 fps (code) limits update rate; call `camera_update()` before every query. |

---

## 10. Servo and torque sanity numbers

Estimated object data: the **model sizes come from G** (nominal CAD); **masses are my estimates and must be measured**.

| Piece | Model size (in) | Estimated mass | Tag |
|---|---|---|---|
| Botguy (plush) | about 6.8 W x 3.0 D x 8.5 H as modelled | 100-200 g (use 150 g) | size from G (grey/red meshes `Cut-Extrude2`, `Revolve2`, `Extrude7/8` at X 44.6-51.4, Y 42.5-45.5, matching the top-center start in R p.4; identification is I), mass I |
| Big duck | 5.33 x 4.77 x 4.45 | 50-150 g (use 100 g) | tight CAD box from `docs/field-map.md` section 6 (the two yellow mesh groups `Mirror3` and `Split Line2` are the two mirrored halves of the one Big Duck, base 5.63 in above the board, i.e. on the platform; an earlier version of this row said 4.9 x 2.4 x 4.5 and "two ducks", which came from the inflated raw boxes and from reading one half), mass I |
| Cup | 3.63 mouth dia (about 2.5 at the top/base) x 5.70 H (raw box said 5.0, inflated) | 20-60 g (use 40 g) | G, I |
| Ring | ID 1.41, OD 2.13, thick 0.36 (vertex-measured; the mesh name says "1.75in" but that is not the ID) | about 10 g | G, I |
| Small duck | 2.27 x 1.46 x 1.46 including beak | about 15 g | G, I |
| Pom | 1.5 dia | about 3 g | G, I |
| Pickleball | 2.91 dia (regulation pickleball is about 22-26 g) | 26 g | G, I |

Static torque at the servo shaft is `T [oz-in] = mass [g] / 28.35 x arm length [in]` (arm and gripper mass add on top):

| Load (mass) | L = 3 in | 4 in | 6 in | 8 in |
|---|---|---|---|---|
| Pom (3 g) | 0.3 | 0.4 | 0.6 | 0.8 |
| Small duck (15 g) | 1.6 | 2.1 | 3.2 | 4.2 |
| Ring (10 g) | 1.1 | 1.4 | 2.1 | 2.8 |
| Pickleball (26 g) | 2.8 | 3.7 | 5.5 | 7.3 |
| Cup (40 g) | 4.2 | 5.6 | 8.5 | 11.3 |
| Big duck (100 g) | 10.6 | 14.1 | 21.2 | 28.2 |
| Botguy (150 g) | 15.9 | 21.2 | 31.7 | 42.3 |

Worked example, Botguy lift: 150 g payload plus a 50 g claw at arm length L, plus a 40 g arm at L/2:

| L | Total torque |
|---|---|
| 3 in | 23 oz-in |
| 4 in | 31 oz-in |
| 6 in | 47 oz-in |

Reading against capacity (use no more than about 50% of rated torque for holding and fast moves):

- Micro servo (22 oz-in rated, about 11 usable): fine for claws, wrists, and anything up to about the cup/duck class at 3-4 in; not for Botguy.
- Standard servo (conservatively 45-70 oz-in rated, so about 22-35 usable; the 156 oz-in M13 figure would double that): handles Botguy only at a short arm (3-4 in) or with help.
- Help: shorten the arm; gear it down (a 24:8 pair gives 3x torque and one third of the swing, so the reduced stroke needs a longer lever); add a counterweight (up to 250 g of coins is legal [S R p.12]); put the load on a DC gear motor with position control (`mrp`) and a worm gear (2 in the kit) so it holds without power; or use a rack/pinion or string winch.
- Lift target height for the platform: the top is 5.69 in above the board, so a payload must reach about 6.5-7 in. [I]
- The pickleball and ring tasks need accuracy more than torque: a pickleball (2.91 in) has to be pushed off its tee socket and end up under the platform (clearance 5.5 in under the 5.69 in top; access side **[I]**), and a ring (ID 1.41 in) must drop over a bottle neck of about 1.06 in diameter with a 1.30 in flange (estimates from mesh slices, `docs/field-map.md` section 6; **[V]**).

Power sanity: a standard servo at stall can pull more than its 1.0 A port fuse holds (trip 1.8 A), and motors share a 5 A hold fuse. Avoid more than about 2 stalled actuators at once, and add limit switches so arms never push on a hard stop.

---

## 11. Software and rules gotchas for hardware choices

1. `motor()` is velocity-controlled; speeds depend on PID and slow down under load. For the same behavior independent of battery use `mav`.
2. The servo port cuts pulses when disabled; `disable_servos()` makes arms limp. Put arms in a safe stable pose before the end of the round.
3. `shut_down_in` plus no threads. If a program ever deadlocks, the Wombat stop is the safety net, but check with a stopwatch at home.
4. Only the included camera may be on USB; no USB cable or charger at the table [S R p.11, p.13].
5. No electrical modifications and no extension cables other than the kit's [S R p.13].
6. Sensors must not stick out of the start-box volume, nor the lamp shielding [S R p.12].
7. 90 s setup window includes light calibration; prepare a calibrate-once procedure at home.
8. Tape voids scoring: a robot that drags a piece across the 1.88 in tape can still score it if it ends up off tape [S R p.5, final-location rule].

---

## 12. Measure-these-physically checklist

Game objects (needed for gripper and mechanism design; compare with G values in section 10):

- [ ] Small duck: length, width, height, mass (model 2.27 x 1.46 x 1.46 in).
- [ ] Big duck: length, width, height, mass (model 5.33 x 4.77 x 4.45 in).
- [ ] Ring: ID, OD, thickness, mass (model: ID 1.41, OD 2.13, thickness 0.36 in).
- [ ] Bottle: body diameter, **neck outer diameter**, neck height, height, mass (model body 2.53 in, 4.95 in tall).
- [ ] Pickleball: diameter, mass; post height and post diameter; how high above the board it sits (model about 2.3-5.2 in).
- [ ] Cups: rim OD, base OD, height, mass; does a cup nest (rim vs base diameters); color (rules: green and teal; model is black).
- [ ] Botguy: height, width, depth, mass, softness (plush deformation).
- [ ] Poms: diameter and mass, per color.
- [ ] Platform: top height and clearance under it, open sides, ground clearance at the left lip.
- [ ] Tape width (model 1.87-1.88 in) and how glossy it is (tophat readings).

Robot hardware:

- [ ] Count everything against section 2 and section 3; flag missing motors and light sensors.
- [ ] Wombat: width x depth x height with case, mass, battery in place, mounting-hole pattern vs the PCB figure (112.7 x 83.8 mm).
- [ ] Wheel diameter and width for Solarbotics, mecanum, caster ball; wheel hub/spline interface to the motor.
- [ ] Ticks per revolution (push one revolution, read `gmpc`); ticks per inch; max `mav` achievable under load.
- [ ] Motor: free speed at `motor(p,100)`, stall torque (hanging weight on a pulley), stall current if you have a meter, temperature after 10 s stall.
- [ ] Servo: torque with a spring scale at a measured lever; usable position range per servo (watch for buzzing); servo speed.
- [ ] Servo and motor lead lengths; extension cables needed.
- [ ] KIPR metal: hole pitch and diameter; chassis material (magnet test), mass.
- [ ] Reflectance values over this FRP and this tape at the chosen mounting height; ET curve; light sensor readings with the actual home lamp.
- [ ] Camera: mounting height, field of view, color thresholds under home lighting for all 10 colors; 4-channel limit workaround.
- [ ] Battery: voltage after charge, run time in a 120 s run with all actuators; charge time.
- [ ] Gyro: counts per degree, drift over 120 s.

Questions for the Head Judge or FAQ:

1. Is the chassis in the 2026 kit allowed (steel) and how is "old KIPR aluminum chassis" defined? (R p.11 vs K-M)
2. Do KIPR's example STLs need a submitted STL and a class slot? How is the class interpreted from whole-inch volume?
3. Is a second Logitech camera from an older kit allowed on a second Wombat? R p.11 says teams may use two cameras, while p.3 also requires two event cameras for virtual play, so the intent is unclear.
4. Does the ABS rod exist in the 2026 kit?
5. With two robots, must both leave the Starting Box?
6. What lamp type and position does the virtual-event starting light use at a home table?

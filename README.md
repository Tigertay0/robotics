# Rochambotics: 2026 Botball Fall Game

Two robots: **A "Duck Runner"** (mecanum, puts exactly one duck in each of the 5 zones for the ×5 multiplier) and **B "Point Scorer"** (cup, red pom, pom stacks, pickleball). Plan v3 scores **625** if everything lands; no two parts ever collide in the simulator.

## Start here

| I want to… | Open |
|---|---|
| **Build the robots** (picture manual: every part named, every screw hole shown, also a video) | [docs/manual/build_manual.html](docs/manual/build_manual.html) (download and open in a browser; add `?video=1` to the address for the video) |
| **Watch the build manual** (the same manual as a 393 s, 1080p video, no audio; rendered Nov 10 from the current manual) | [docs/manual/build_manual.mp4](docs/manual/build_manual.mp4) |
| Read the build steps as text (order of work, wiring, calibration, tournament day) | [docs/BUILD.md](docs/BUILD.md) |
| See what the finished robots look like and what every part does | [docs/ROBOTS.md](docs/ROBOTS.md) |
| **Print the 4 printed parts** | [3D_PRINTS.md](3D_PRINTS.md) → STL files in [parts/team4/](parts/team4/) |
| Understand the plan and the score | [STRATEGY.md](STRATEGY.md) (section 4 = the 120 s timeline) |
| **Watch how both robots' code runs in a match** (rebuilt Nov 10 with the current robots, parts and duck sequence) | [docs/animation/robot_code_explainer.html](docs/animation/robot_code_explainer.html) |
| Upload and calibrate the robot code | [code/README.md](code/README.md) → [robot_a/main.c](code/robot_a/main.c), [robot_b/main.c](code/robot_b/main.c) |
| Check a rule | [docs/rules-digest.md](docs/rules-digest.md) (+ questions to send KIPR) |
| Find a piece's position or a zone's size on the table | [docs/field-map.md](docs/field-map.md) |

## Everything, by folder

**Plan and rules**
- [STRATEGY.md](STRATEGY.md): the team plan (scoring, robot roles, timeline, failure plans).
- [docs/rules-digest.md](docs/rules-digest.md): every rule that matters and the ambiguous ones. Also [field-map.md](docs/field-map.md), [hardware.md](docs/hardware.md), [prior-art.md](docs/prior-art.md), [team-hardware-confirmed.md](docs/team-hardware-confirmed.md).
- [docs/strategy-alt.md](docs/strategy-alt.md): a second plan kept only for comparison.
- `docs/*.pdf`: the official 2026 rule summary and kit part lists. `docs/official/`: the rule-summary text and zone images.

**Building**
- [docs/manual/](docs/manual/): the step-by-step manual ([build_manual.html](docs/manual/build_manual.html)), the two 3D models it uses (`robot_a.glb`, `robot_b.glb`, also as `.obj` with one object per part), `steps.json`, and [bom.md](docs/manual/bom.md). The BOM check proves every part and screw is in the 2026 kit and only 4 parts are printed, and its size table proves both robots fit the 11.25 × 21.125 × 12 in start-box limit.
- [docs/BUILD.md](docs/BUILD.md), [docs/ROBOTS.md](docs/ROBOTS.md) (renders in `docs/robots/`), [docs/parts.md](docs/parts.md).
- [3D_PRINTS.md](3D_PRINTS.md) and [parts/team4/](parts/team4/): the 4 prints (p1 Robot A chassis with duck lane, p2 claw jaw, p3 pocket plow, p4 cup hook) as slicer-ready **STL and OBJ** files with previews and [budget.md](parts/team4/budget.md).
- [guide/](guide/index.html): the older interactive assembly guide. [prints/](prints/README.md): an earlier two-half printed duck lane (not printed: superseded by print 1, too narrow for the measured ducks).
- [index.html](index.html): the GitHub Pages front page.

**Code and match plan**
- [code/](code/README.md): the Wombat programs for both robots.
- `tools/match_plan.py`: both robots' routes (plan v3). `python tools/match_sim.py` checks them every 0.05 s and must print **NO CONTACTS**; `--export` writes [docs/animation/match_data.json](docs/animation/match_data.json) for the video, and `python tools/match_plot.py` draws [plan_debug.png](docs/animation/plan_debug.png).
- [docs/animation/robot_code_explainer.html](docs/animation/robot_code_explainer.html): the "How our robots think" video.

**Tools** (Python 3; Blender 5.2 for the `tools/blender/` scripts)
- `python tools/score.py data/scenarios/plan_t1_core.json` (add `--conservative` or `--sensitivity`) scores a scenario exactly, with a switch for each ambiguous rule. `python tools/test_score.py` runs its tests.
- `python tools/blender/build_parts.py` regenerates the 4 prints. It fails on any fit, watertightness, clearance or 4-part-budget problem.
- `blender -b --factory-startup --python tools/blender/export_build_manual.py -- docs/manual` regenerates the manual's models, steps and BOM check.
- `data/`: kit counts (`kit_2026.json`), field map, robot footprints, score scenarios.
- [blender/](blender/README.md): 3D model of the official table and the original animated plan (`blender/out/*.blend`), with three close-up videos (`blender/out/closeup_*.mp4`). It shows the first strategy, not plan v3.

**Original uploads**: `Fall_Game_Table.glb`, `STL Parts.zip` (official table and part geometry from KIPR Team Home Base), `Botball_Fall_Seeding_Scoresheet.xlsx`, `Fall_Game_Table.pdf`, `Botball Inventory.xlsx`.

# Part generator (Blender CLI)

We print **4 parts in total** (team rule: any size up to the Ender 3 V3 SE bed, 220 × 220 × 250 mm; each one a single solid piece). Which 4 and why: [3D_PRINTS.md](../3D_PRINTS.md).

```bash
python tools/blender/build_parts.py
```

The script runs Blender headless for each part script in `tools/blender/parts/` and writes the outputs to `parts/team4/`:
- `<part>.stl` (millimetres)
- `<part>.png`, `_top.png` and `_under.png` previews
- `<part>.json` report
- `budget.md`

The build **fails** if any of these are true:

- a part does not fit the bed (with at least 1 mm margin);
- a part is not watertight or has inverted normals;
- a part has the wrong number of separate bodies. The claw must be exactly 3; the other prints must be 1, so a severed cut or a face-only join fails;
- the claw's moving bodies come closer than 0.35 mm anywhere in their ±25° swing (they would fuse on the bed);
- a boolean silently does nothing (a cut that misses);
- the plan goes over 4 parts.

| Script | Print |
|---|---|
| `p1_chassis_a.py` | Robot A chassis with the duck lane built in |
| `p2_claw_jaw.py` | Robot B claw jaw: one solid piece (base + fixed finger); the moving finger is a kit liftarm |
| `p3_pocket_plow.py` | Robot B pocket plow |
| `p4_cup_hook.py` | Robot B cup hook |

Every script starts with a block of `MEASURE` constants (motor, wheels, ducks, servos, horns, cup rim). Measure the real parts, edit them, re-run, then slice. Helpers (boxes, cylinders, booleans, hole grids, clearance check, STL export, previews) are in `tools/blender/partlib.py`.

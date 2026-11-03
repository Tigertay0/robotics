"""Build every printable part with the Blender CLI and check the KIPR print budget.

    python tools/blender/build_parts.py            # build all into parts/out
    python tools/blender/build_parts.py --blender "C:/path/blender.exe"   # or set BLENDER

Writes parts/out/<part>.stl/.png/_top.png/_under.png/.json and parts/out/budget.md.
Exit code 1 if any part fails to build, is non-manifold, is in more than one
piece, has under 1 mm margin to its class box, fails the literal-mm class box,
or the 1 large / 2 mid / 6 small budget is exceeded.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTS_DIR = Path(__file__).resolve().parent / "parts"
DEFAULT_BLENDER = (os.environ.get("BLENDER") or shutil.which("blender")
                   or r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

# (script[:part], slot label, robot, copies to print, planned class)
PLAN = [
    ("claw_palm.py", "L1", "B", 1, "large"),
    ("duck_cage.py", "M1", "A", 1, "mid"),
    ("claw_jaw.py", "M2", "B", 1, "mid"),
    ("small_parts.py:camera_mount", "S1", "B", 1, "small"),
    ("small_parts.py:tophat_bracket", "S2-S3", "A+B", 2, "small"),
    ("small_parts.py:light_shroud", "S4-S5", "A+B", 2, "small"),
    ("small_parts.py:ring_fork", "S6", "B (stretch)", 1, "small"),
]
BUDGET = {"large": 1, "mid": 2, "small": 6}   # rules p.12; mirrors partlib.PRINT_CLASSES
RUN_ERRORS = (RuntimeError, subprocess.TimeoutExpired, OSError, ValueError, KeyError)


def part_stem(entry: str) -> str:
    script, _, only = entry.partition(":")
    return only or Path(script).stem


def run_part(blender: str, entry: str, out: Path) -> dict:
    script, _, only = entry.partition(":")
    cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1",
           "--python", str(PARTS_DIR / script), "--", "--out", str(out)]
    if only:
        cmd += ["--only", only]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=600)
    reports = [json.loads(line.split("PART_REPORT ", 1)[1])
               for line in proc.stdout.splitlines() if line.startswith("PART_REPORT ")]
    if proc.returncode != 0 or not reports:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-25:])
        raise RuntimeError(f"failed (exit {proc.returncode}):\n{tail}")
    return reports[-1]


def check_report(rep: dict, planned: str) -> list[str]:
    name, chk = rep["name"], rep.get("print_check", {})
    cls = chk.get("class", "?")
    issues = []
    if cls != planned:
        issues.append(f"{name}: built as {cls}, planned {planned}")
    if not rep["manifold"]:
        issues.append(f"{name}: {rep['non_manifold_edges']} non-manifold edges")
    if rep.get("islands") != 1:
        issues.append(f"{name}: {rep.get('islands')} disconnected pieces (severed cut or face-only join)")
    if rep.get("volume_cm3", 0) <= 0:
        issues.append(f"{name}: non-positive volume (inverted normals)")
    if not chk.get("pass_strict"):
        issues.append(f"{name}: fails the literal-mm {cls} box {chk.get('class_dims_mm')} as exported "
                      f"(whole-inch reading: {'pass' if chk.get('pass_inch_box') else 'fail'})")
    elif chk.get("low_margin"):
        issues.append(f"{name}: under 1 mm margin to the {cls} box (margins {chk.get('margin_mm')})")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender", default=DEFAULT_BLENDER)
    ap.add_argument("--out", default=str(ROOT / "parts" / "out"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not Path(args.blender).exists():
        print(f"Blender not found: {args.blender} (pass --blender or set BLENDER)")
        return 1

    # Remove last run's outputs so a failure can never leave a stale pass behind.
    (out / "budget.md").unlink(missing_ok=True)
    for entry, *_ in PLAN:
        stem = part_stem(entry)
        for f in [*out.glob(f"{stem}.*"), *out.glob(f"{stem}_*.png")]:
            f.unlink(missing_ok=True)

    rows, used, problems = [], {k: 0 for k in BUDGET}, []
    for entry, slot, robot, copies, planned in PLAN:
        used[planned] = used.get(planned, 0) + copies     # counted even if the build fails
        try:
            rep = run_part(args.blender, entry, out)
        except RUN_ERRORS as exc:
            problems.append(f"{entry}: {exc}")
            rows.append(f"| {slot} | `{part_stem(entry)}` | {robot} | {copies} | {planned} | BUILD FAILED | | | | |")
            continue
        issues = check_report(rep, planned)
        problems += issues
        chk = rep.get("print_check", {})
        dims = " x ".join(f"{d:.0f}" for d in rep["dims_mm"])
        rin = " x ".join(str(d) for d in chk.get("part_dims_rounded_in", []))
        margin = min(chk.get("margin_mm", [0]))
        rows.append(f"| {slot} | `{rep['name']}` | {robot} | {copies} | {chk.get('class', '?')} | {dims} | {rin} | "
                    f"{margin:.1f} | {rep['volume_cm3']} | {'pass' if not issues else 'FAIL'} |")
    for cls, limit in BUDGET.items():
        if used.get(cls, 0) > limit:
            problems.append(f"budget: {used[cls]} {cls} parts > {limit} allowed")

    lines = [
        "# Print budget check (generated by tools/blender/build_parts.py)",
        "",
        "| Slot | Part | Robot | Copies | Class | Size mm | Whole-inch box | Min margin mm | Plastic cm3 | Checks |",
        "|---|---|---|---:|---|---|---|---:|---:|---|",
        *rows,
        "",
        "Checks = manifold, one piece, positive volume, fits the class box in mm as exported, >= 1 mm margin.",
        "",
        "Budget used: " + ", ".join(f"{used.get(k, 0)}/{v} {k}" for k, v in BUDGET.items()),
        "",
        "Problems:" + (" none" if not problems else ""),
        *[f"- {p}" for p in problems],
    ]
    (out / "budget.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

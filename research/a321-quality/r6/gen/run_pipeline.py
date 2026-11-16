# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Run one R6 candidate attempt end to end and write receipt.json with per-step wall times.

Steps: build npz -> Blender build+export+verify (G7) -> references -> gate x4 (locator, PyMeshLab, metrics)
-> surfaceCheck x4 (WSL, copies) -> junctions x3 (WSL surfaceBooleanFeatures) -> evaluator -> renders.

How to run: python run_pipeline.py --tag r6-a --attempt attempt01 --tess quad [--skip-render]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R6 = HERE.parent
REPO = HERE.parents[3]
BLENDER = Path("D:/Chanil_Park/Project/Programming/Aircraft-Workbench/.workstation/tools/blender-5.2.2-portable/blender.exe")
LEDGER = REPO / "research/a321-integration/evidence/reconstruction-r3.json"
R3 = REPO / "research/a321-integration/artifacts/shell-r3"
NAMES = ("fuselage", "wing", "horizontal", "vertical")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MSYS_NO_PATHCONV="1")
STEPS: list[dict] = []


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def run(label: str, cmd: list, log: Path, cwd: Path = HERE) -> float:
    """Run a command, tee stdout/stderr to log (head/tail kept if > 50 MB), record wall time."""
    start = time.perf_counter()
    with log.open("wb") as stream:
        proc = subprocess.run([str(c) for c in cmd], cwd=cwd, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    wall = time.perf_counter() - start
    if log.stat().st_size > 50_000_000:
        data = log.read_bytes()
        log.write_bytes(data[:5_000_000] + b"\n...TRUNCATED...\n" + data[-5_000_000:])
    STEPS.append({"step": label, "wall_s": round(wall, 2), "returncode": proc.returncode, "cmd": " ".join(str(c) for c in cmd)[:400], "log": log.name})
    if proc.returncode != 0:
        print("FAILED", label, "see", log, file=sys.stderr)
    return wall


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--attempt", required=True)
    ap.add_argument("--tess", choices=("quad", "lean"), required=True)
    ap.add_argument("--aspect-fuselage", default="3.0")
    ap.add_argument("--aspect-wing", default="1.8")
    ap.add_argument("--aspect-vertical", default="1.0")
    ap.add_argument("--build-args", default="", help="extra build_r6.py flags, e.g. \"--end-match --cap-density 3.0\"")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--only", default="", help="comma list of steps to run: build,blender,refs,gate,sc,junction,eval,render")
    args = ap.parse_args()
    att = R6 / "candidates" / args.tag / args.attempt
    only = set(filter(None, args.only.split(",")))
    want = (lambda s: (not only) or s in only)  # noqa: E731
    logs = att / "logs"
    logs.mkdir(parents=True, exist_ok=True) if att.exists() else att.mkdir(parents=True)
    logs.mkdir(exist_ok=True)
    inputs = [LEDGER, *(R3 / f"{n}.stl" for n in NAMES), *(R6 / f"plans/r6-geometry-contract-02{s}.json" for s in ("", "a", "b", "c"))]
    before = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    if want("build"):
        cmd = [sys.executable, HERE / "build_r6.py", "--out-dir", att / "_build", "--aspect-fuselage", args.aspect_fuselage, "--aspect-wing", args.aspect_wing,
               "--aspect-vertical", args.aspect_vertical, "--tess", args.tess, *shlex.split(args.build_args)]
        run("build_r6", cmd, logs / "build.log")
        for f in (att / "_build").iterdir():
            shutil.move(str(f), att / f.name)
        (att / "_build").rmdir()
    if want("blender"):
        common = ["-b", "--factory-startup", "--disable-autoexec", "--python", HERE / "blender_r6.py", "--python-exit-code", "1", "--",
                  "--tag", args.tag, "--npz-dir", att, "--out-dir", att]
        run("blender_build_export", [BLENDER, *common[:8], "--build", *common[8:]], logs / "blender-build.log")
        run("blender_verify_fresh_process", [BLENDER, *common[:8], "--verify", *common[8:]], logs / "blender-verify.log")
    if want("refs") and not (att / "refs").exists():
        run("make_refs", [sys.executable, HERE / "make_refs.py", "--out-dir", att / "refs"], logs / "refs.log")
    if want("gate"):
        gate_dir = att / "gate"
        gate_dir.mkdir(exist_ok=True)
        procs = []
        start = time.perf_counter()
        for n in NAMES:
            ref = R3 / f"{n}.stl" if n in ("fuselage", "vertical") else att / f"refs/ref-{n}-fullspan.stl"
            cmd = ["uv", "run", R6 / "checks/r6_gate.py", "--surface", f"{n}={att / (n + '.stl')}", "--features", att / f"features-{n}.json", "--stations", LEDGER,
                   "--deviation", f"{n}={ref}", "--checkers", "locator,meshlab", "--log-dir", gate_dir / f"logs-{n}", "--out", gate_dir / f"{n}-report.json"]
            stream = (logs / f"gate-{n}.log").open("wb")
            procs.append((n, subprocess.Popen([str(c) for c in cmd], cwd=R6 / "checks", env=ENV, stdout=stream, stderr=subprocess.STDOUT), stream))
        for n, proc, stream in procs:
            proc.wait()
            stream.close()
            STEPS.append({"step": f"r6_gate_{n}", "returncode": proc.returncode, "log": f"gate-{n}.log"})
        STEPS.append({"step": "r6_gate_all_parallel", "wall_s": round(time.perf_counter() - start, 2)})
    if want("sc"):
        (att / "sc").mkdir(exist_ok=True)
        for n in NAMES:
            start = time.perf_counter()
            out = subprocess.run(["wsl", "bash", wsl_path(HERE / "run_surfacecheck_gen.sh"), f"{args.tag}-{args.attempt}-{n}", wsl_path(att / f"{n}.stl"), "100"],
                                 env=ENV, capture_output=True, text=True).stdout.strip().splitlines()[-1]
            src = HERE / "attempts" / Path(out).name
            shutil.copy(src / "result.log", att / f"sc/{n}-result.log")
            if (src / "selfInterPoints.obj").exists():
                shutil.copy(src / "selfInterPoints.obj", att / f"sc/{n}-selfInterPoints.obj")
            text = (src / "result.log").read_text(errors="replace")
            m = re.search(r"self-intersecting at (\d+) locations", text)
            parsed = {"locations": int(m.group(1)) if m else 0, "end_reached": bool(re.search(r"^End\s*$", text, re.M)), "fatal": "FATAL" in text,
                      "closed": "Surface is closed" in text, "attempt_dir": src.name, "wall_s": round(time.perf_counter() - start, 2),
                      "min_quality": float(re.search(r"min ([\d.e+-]+) for triangle", text).group(1)),
                      "stl_sha_unchanged": (src / "before.sha256").read_text() == (src / "after.sha256").read_text(), "outputThreshold": 100}
            (att / f"sc/{n}-surfacecheck.json").write_text(json.dumps(parsed, indent=1), encoding="utf-8")
            STEPS.append({"step": f"surfaceCheck_{n}", "wall_s": parsed["wall_s"], "locations": parsed["locations"]})
    if want("junction"):
        (att / "junctions").mkdir(exist_ok=True)
        for n in ("wing", "horizontal", "vertical"):
            start = time.perf_counter()
            out = subprocess.run(["wsl", "bash", wsl_path(HERE / "run_junction_gen.sh"), f"{args.tag}-{args.attempt}-{n}", wsl_path(att / "fuselage.stl"), wsl_path(att / f"{n}.stl")],
                                 env=ENV, capture_output=True, text=True).stdout.strip().splitlines()[-1]
            src = HERE / "attempts" / Path(out).name
            shutil.copy(src / "result.log", att / f"junctions/{n}-sbf.log")
            STEPS.append({"step": f"surfaceBooleanFeatures_{n}", "wall_s": round(time.perf_counter() - start, 2), "attempt_dir": src.name})
            run(f"junction_analysis_{n}", ["uv", "run", HERE / "junction_analysis.py", "--sbf-dir", src, "--fuselage", att / "fuselage.stl", "--other", att / f"{n}.stl",
                                           "--out", att / f"junctions/{n}.json"], logs / f"junction-{n}.log")
    if want("eval"):
        out = att / "gate-table.json"
        if out.exists():
            out.unlink()
        run("check_r6", ["uv", "run", HERE / "check_r6.py", "--attempt", att, "--out", out], logs / "check.log")
    if want("render") and not args.skip_render:
        fig = HERE / "figures" / f"{args.tag}-{args.attempt}"
        common = ["-b", "--factory-startup", "--disable-autoexec", "--python", HERE / "blender_r6.py", "--python-exit-code", "1", "--"]
        run("blender_render", [BLENDER, *common, "--render", "--tag", args.tag, "--npz-dir", att, "--out-dir", att, "--fig-dir", fig], logs / "blender-render.log")
    after = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    receipt = {"tag": args.tag, "attempt": args.attempt, "tessellation": args.tess,
               "params": {"build_args": args.build_args, "aspect_fuselage": args.aspect_fuselage, "aspect_wing_horizontal": args.aspect_wing, "aspect_vertical": args.aspect_vertical},
               "steps": STEPS, "inputs_sha256_before": before, "inputs_sha256_after": after, "inputs_unchanged": before == after,
               "artifact_sha256": {f.name: sha(f) for f in sorted(att.glob("*")) if f.is_file() and f.suffix in (".stl", ".npz", ".blend", ".json")},
               "date_local": time.strftime("%Y-%m-%d %H:%M:%S")}
    (att / ("receipt.json" if not only else f"receipt-partial-{int(time.time())}.json")).write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("DONE", att, "inputs_unchanged", receipt["inputs_unchanged"])


if __name__ == "__main__":
    main()

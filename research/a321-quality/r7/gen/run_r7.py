#!/usr/bin/env -S uv run --script
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
"""R7 fuselage attempt pipeline (contract 03 / 03a), after the step-0 barrel gate passed.

prep (candidate dir, .gitignore, R6-c wing/horizontal/vertical copies) -> build fuselage -> Blender build + fresh-process verify (G7)
-> r6_gate (locator, PyMeshLab, quality, smoothness) -> surfaceCheck (WSL copy) -> junctions (surfaceBooleanFeatures) -> A3 ->
dense G4R measurements -> evaluator -> Blender renders -> receipt. Every step is logged (logs capped at 20 MB, head and tail kept)
with local start/end time and wall seconds.

How to run: uv run --no-project run_r7.py [--only prep,build,blender,gate,sc,junction,a3,dense,eval,render,receipt]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
QUALITY = HERE.parents[1]
REPO = HERE.parents[3]
R6 = QUALITY / "r6"
R6C = R6 / "candidates/r6-c/attempt01"
R7 = QUALITY / "r7"
ATT = R7 / "candidates/r7-a/attempt01"
BLENDER = Path("D:/Chanil_Park/Project/Programming/Aircraft-Workbench/.workstation/tools/blender-5.2.2-portable/blender.exe")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", MSYS_NO_PATHCONV="1")
STEPS: list[dict] = []
REUSED = ("wing", "horizontal", "vertical")
LOG_CAP = 20_000_000


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wsl_path(p: Path) -> str:
    s = str(Path(p).resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def run(label: str, cmd: list, log: Path, cwd: Path = HERE) -> int:
    start_s, t0 = time.strftime("%Y-%m-%d %H:%M:%S"), time.perf_counter()
    with log.open("wb") as stream:
        proc = subprocess.run([str(c) for c in cmd], cwd=cwd, env=ENV, stdout=stream, stderr=subprocess.STDOUT)
    wall = time.perf_counter() - t0
    if log.stat().st_size > LOG_CAP:
        data = log.read_bytes()
        log.write_bytes(data[:LOG_CAP // 2] + b"\n...TRUNCATED...\n" + data[-LOG_CAP // 2:])
    STEPS.append({"step": label, "start_local": start_s, "end_local": time.strftime("%Y-%m-%d %H:%M:%S"), "wall_s": round(wall, 2), "returncode": proc.returncode, "cmd": " ".join(str(c) for c in cmd)[:500], "log": str(log.relative_to(ATT))})
    if proc.returncode != 0:
        print("FAILED", label, "see", log, file=sys.stderr)
    return proc.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    want = lambda s: (not only) or s in only  # noqa: E731
    r6c_receipt = json.loads((R6C / "receipt.json").read_text(encoding="utf-8"))
    ATT.mkdir(parents=True, exist_ok=True)
    logs = ATT / "logs"
    logs.mkdir(exist_ok=True)
    inputs = [R6 / "plans" / f"r7-geometry-contract-03{s}.json" for s in ("", "a")] + [R7 / "measure/r7-measure.json", R7 / "measure/trace-meta.json", REPO / ".worktmp/r7-trace/raw-trace.json",
              REPO / "research/a321-integration/artifacts/shell-r3/fuselage.stl", REPO / "research/a321-integration/evidence/reconstruction-r3.json"] + [R6C / f"{n}.stl" for n in REUSED] + [R6C / f"{n}.npz" for n in REUSED]
    before = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    if want("prep"):
        gi = R7 / "candidates/.gitignore"
        if not gi.exists():
            shutil.copyfile(R6 / "candidates/.gitignore", gi)
        for n in REUSED:
            for ext in ("stl", "npz"):
                if not (ATT / f"{n}.{ext}").exists():
                    shutil.copyfile(R6C / f"{n}.{ext}", ATT / f"{n}.{ext}")
        STEPS.append({"step": "prep", "note": ".gitignore and R6-c copies", "reused_sha_equal": {n: sha(ATT / f"{n}.stl") == sha(R6C / f"{n}.stl") for n in REUSED}})
    if want("build"):
        run("build_fuselage", ["uv", "run", "--no-project", HERE / "r7_fuselage.py", "--out-dir", ATT], logs / "build.log")
    common = ["-b", "--factory-startup", "--disable-autoexec", "--python", HERE / "blender_r7.py", "--python-exit-code", "1", "--"]
    if want("blender"):
        run("blender_build_export", [BLENDER, *common[:8], "--build", *common[8:], "--tag", "r7-a", "--npz-dir", ATT, "--out-dir", ATT], logs / "blender-build.log")
        run("blender_verify_fresh_process", [BLENDER, *common[:8], "--verify", *common[8:], "--tag", "r7-a", "--npz-dir", ATT, "--out-dir", ATT], logs / "blender-verify.log")
        STEPS.append({"step": "reused_stl_after_blender", "sha_equal_to_r6c": {n: sha(ATT / f"{n}.stl") == sha(R6C / f"{n}.stl") for n in REUSED}})
    if want("gate"):
        (ATT / "gate").mkdir(exist_ok=True)
        run("r6_gate_fuselage", ["uv", "run", "--no-project", R6 / "checks/r6_gate.py", "--surface", f"fuselage={ATT / 'fuselage.stl'}", "--features", ATT / "features-fuselage.json", "--stations", ATT / "stations-fuselage.json",
                                  "--checkers", "locator,meshlab", "--log-dir", ATT / "gate/logs-fuselage", "--out", ATT / "gate/fuselage-report.json"], logs / "gate-fuselage.log", cwd=R6 / "checks")
    if want("sc"):
        (ATT / "sc").mkdir(exist_ok=True)
        run("surfaceCheck_fuselage", ["uv", "run", "--no-project", HERE / "r7_sc.py", "--name", "r7-a-attempt01-fuselage", "--stl", ATT / "fuselage.stl", "--out", ATT / "sc/fuselage-surfacecheck.json"], logs / "surfacecheck.log")
    if want("junction"):
        (ATT / "junctions").mkdir(exist_ok=True)
        for n in REUSED:
            t0 = time.perf_counter()
            out = subprocess.run(["wsl", "-e", "bash", wsl_path(HERE / "run_junction_r7.sh"), f"r7-a-attempt01-{n}", wsl_path(ATT / "fuselage.stl"), wsl_path(ATT / f"{n}.stl")], env=ENV, capture_output=True, text=True).stdout.strip().splitlines()[-1]
            src = REPO / ".worktmp/r7-gen/sbf" / Path(out).name
            shutil.copy(src / "result.log", ATT / f"junctions/{n}-sbf.log")
            STEPS.append({"step": f"surfaceBooleanFeatures_{n}", "wall_s": round(time.perf_counter() - t0, 2), "sbf_dir": str(src), "wall_date_s": (src / "wall.txt").read_text().strip()})
            run(f"junction_analysis_{n}", ["uv", "run", "--no-project", R6 / "gen/junction_analysis.py", "--sbf-dir", src, "--fuselage", ATT / "fuselage.stl", "--other", ATT / f"{n}.stl", "--out", ATT / f"junctions/{n}.json"], logs / f"junction-{n}.log")
    if want("a3"):
        if (ATT / "a3.json").exists():
            (ATT / "a3.json").unlink()
        run("a3_reference", ["uv", "run", "--no-project", R6 / "gen/a3_reference.py", "--attempt", ATT, "--out", ATT / "a3.json"], logs / "a3.log")
    if want("dense"):
        (ATT / "dense").mkdir(exist_ok=True)
        run("dense_G4R", ["uv", "run", "--no-project", HERE / "r7_dense.py", "--attempt", ATT, "--out", ATT / "dense/dense.json"], logs / "dense.log")
    if want("eval"):
        out = ATT / "gate-table.json"
        if out.exists():
            out.unlink()
        run("r7_check", ["uv", "run", "--no-project", HERE / "r7_check.py", "--attempt", ATT, "--out", out], logs / "check.log")
    if want("render"):
        run("blender_render", [BLENDER, *common, "--render", "--tag", "r7-a", "--npz-dir", ATT, "--out-dir", ATT, "--fig-dir", ATT / "figures"], logs / "blender-render.log")
    after = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    receipt = {"tag": "r7-a", "attempt": "attempt01", "contract": ["r7-geometry-contract-03", "r7-geometry-contract-03a"], "steps": STEPS, "inputs_sha256_before": before, "inputs_sha256_after": after, "inputs_unchanged": before == after,
               "r6c_receipt_artifact_sha256": {k: v for k, v in r6c_receipt.get("artifact_sha256", {}).items() if k.split(".")[0] in REUSED},
               "artifact_sha256": {f.name: sha(f) for f in sorted(ATT.glob("*")) if f.is_file() and f.suffix in (".stl", ".npz", ".blend", ".json")},
               "date_local": time.strftime("%Y-%m-%d %H:%M:%S")}
    name = "receipt.json" if not only else f"receipt-partial-{int(time.time())}.json"
    (ATT / name).write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("DONE", ATT, "inputs_unchanged", receipt["inputs_unchanged"])


if __name__ == "__main__":
    main()

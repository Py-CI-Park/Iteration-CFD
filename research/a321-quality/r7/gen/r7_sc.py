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
"""Run OpenFOAM v1912 surfaceCheck (WSL, copy of the STL in a fresh mktemp -d under .worktmp/r7-gen/sc) with a STRICT parse.

A count of 0 is only reported when the log reached `End`, has no FOAM FATAL, no SURFACECHECK_EXIT_NONZERO marker and
contains either the 'self-intersecting at N locations' line or 'not self-intersecting'; anything else is `valid: false`.

How to run: uv run --no-project r7_sc.py --name NAME --stl PATH --out RESULT.json [--threshold 100000]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

import r7_common

SCRIPT = r7_common.HERE / "run_surfacecheck_r7.sh"


def wsl_path(p: Path) -> str:
    s = str(Path(p).resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def parse(text: str) -> dict:
    out = {"end_reached": bool(re.search(r"^End\s*$", text, re.M)), "fatal": "FOAM FATAL" in text, "nonzero_exit_marker": "SURFACECHECK_EXIT_NONZERO" in text}
    m = re.search(r"self-intersecting at (\d+) locations", text)
    if m:
        out["locations"] = int(m.group(1))
    elif "Surface is not self-intersecting" in text:
        out["locations"] = 0
    else:
        out["locations"] = None
    for key, pat in (("triangles", r"Triangles\s*:\s*(\d+)"), ("vertices", r"Vertices\s*:\s*(\d+)"), ("unconnected_parts", r"Number of unconnected parts\s*:\s*(\d+)"),
                     ("zones", r"Number of zones[^:]*:\s*(\d+)")):
        mm = re.search(pat, text)
        out[key] = int(mm.group(1)) if mm else None
    mm = re.search(r"min\s+(\S+)\s+for triangle\s+(\d+)", text)
    out["quality_min"] = float(mm.group(1)) if mm else None
    out["closed"] = "Surface is closed" in text
    out["illegal_triangles"] = "Surface has no illegal triangles" not in text
    out["valid"] = bool(out["end_reached"] and not out["fatal"] and not out["nonzero_exit_marker"] and out["locations"] is not None)
    return out


def obj_points(text: str) -> np.ndarray:
    rows = [list(map(float, line.split()[1:4])) for line in text.splitlines() if line.startswith("v ")]
    return np.array(rows, dtype=np.float64).reshape(-1, 3)


def run(name: str, stl: Path, threshold: int = 100000) -> dict:
    started = time.perf_counter()
    done = subprocess.run(["wsl", "-e", "bash", wsl_path(SCRIPT), name, wsl_path(stl), str(threshold)], capture_output=True, text=True, check=False)
    wall = time.perf_counter() - started
    attempt = next((line for line in reversed(done.stdout.splitlines()) if line.startswith("/mnt/")), None)
    if done.returncode != 0 or attempt is None:
        return {"valid": False, "error": f"wrapper failed rc={done.returncode}: {done.stderr[-1500:]}"}
    adir = r7_common.WORK / "sc" / Path(attempt).name
    text = (adir / "result.log").read_text(encoding="utf-8", errors="replace")
    result = parse(text)
    obj = adir / "selfInterPoints.obj"
    result["obj_points_m"] = obj_points(obj.read_text(encoding="utf-8")).tolist() if obj.exists() else []
    result["obj_point_count_matches"] = (len(result["obj_points_m"]) == result["locations"]) if result["locations"] else None
    copy_sha = (adir / "copy.sha256").read_text().split()[0]
    result.update({"checker": "OpenFOAM v1912 surfaceCheck -checkSelfIntersection -outputThreshold %d (WSL, copy of the STL)" % threshold, "attempt_dir": str(adir),
                   "copy_sha256_equals_original": copy_sha == r7_common.sha256_file(stl), "original_unchanged": (adir / "before.sha256").read_text() == (adir / "after.sha256").read_text(),
                   "wrapper_wall_seconds_date_measured": float((adir / "wall.txt").read_text().split()[1]), "python_wall_seconds": round(wall, 2)})
    (adir / "input.stl").unlink(missing_ok=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True)
    ap.add_argument("--stl", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threshold", type=int, default=100000)
    args = ap.parse_args()
    res = run(args.name, args.stl, args.threshold)
    args.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(args.name, "valid", res.get("valid"), "locations", res.get("locations"), "end", res.get("end_reached"), "wall", res.get("wrapper_wall_seconds_date_measured"))


if __name__ == "__main__":
    main()

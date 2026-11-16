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
"""Synthetic calibration of the OpenFOAM v1912 surfaceCheck self-intersection response (no candidate is modified).

Cases (open cylinder R=2 m, 32 columns x 100 rows, length 40 m, float32 STL): plain grid, rotations, ring stagger,
per-axis jitter, leaning strip; plus the large 128 x 300 cylinder. surfaceCheck runs on COPIES in new
mktemp -d directories (run_surfacecheck_gen.sh, outputThreshold 100). Results are appended to calibration-log.json.

How to run: python surfacecheck_axis_parallel.py --out calibration-log.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
import r6_io
import r6_tess

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MSYS_NO_PATHCONV="1")
WORK = GEN / "calibration" / "stl"


def wsl(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def surface_check(tag: str, vertices: np.ndarray, faces: np.ndarray) -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / f"{tag}.stl"
    if path.exists():
        path.unlink()
    r6_io.write_stl(path, vertices[faces], tag)
    out = subprocess.run(["wsl", "bash", wsl(GEN / "run_surfacecheck_gen.sh"), f"cal-{tag}", wsl(path), "100"], env=ENV, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    log = GEN / "attempts" / Path(out).name / "result.log"
    match = re.search(r"self-intersecting at (\d+) locations", log.read_text(errors="replace"))
    path.unlink()
    return int(match.group(1)) if match else 0


def tube(ncols: int, nrows: int, length: float, radius: float = 2.0, stagger: bool = False) -> np.ndarray:
    theta = np.arange(ncols) * 2 * np.pi / ncols
    pts = np.zeros((nrows, ncols, 3))
    for i, x in enumerate(np.linspace(0, length, nrows)):
        t = theta + (np.pi / ncols if stagger and i % 2 else 0.0)
        pts[i] = np.stack([np.full(ncols, x), radius * np.cos(t), radius * np.sin(t) + 4.0], axis=1)
    return pts


def lean_faces(rows: int, cols: int) -> np.ndarray:
    vid = np.arange(rows * cols).reshape(rows, cols)
    faces = []
    for i in range(rows - 1):
        b, t = vid[i], vid[i + 1]
        for j in range(cols):
            faces.append((b[j], t[(j + 1) % cols], t[(j + 2) % cols]))
            faces.append((b[j], t[(j + 2) % cols], b[(j + 1) % cols]))
    return np.array(faces)


def rotate(p: np.ndarray, ax: float, ay: float, az: float) -> np.ndarray:
    cx, sx, cy, sy, cz, sz = np.cos(ax), np.sin(ax), np.cos(ay), np.sin(ay), np.cos(az), np.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return p @ (rz @ ry @ rx).T


def jitter(p: np.ndarray, sigma: float, axes: str, seed: int = 1) -> np.ndarray:
    q = p.copy()
    rng = np.random.default_rng(seed)
    for a, c in enumerate("xyz"):
        if c in axes:
            q[:, :, a] += rng.normal(0, sigma, p.shape[:2])
    return q


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cases = []
    base = tube(32, 100, 40.0)

    def grid_case(tag: str, pts: np.ndarray) -> None:
        v, f = r6_tess.grid_triangles(pts)
        v = v.astype(np.float32).astype(np.float64)
        cases.append({"case": tag, "triangles": int(len(f)), "surfaceCheck_locations": surface_check(tag, v, f)})
        print(cases[-1])

    grid_case("plain_32x100", base)
    grid_case("large_128x300", tube(128, 300, 40.0))
    grid_case("rotate_z_0.37rad", rotate(base, 0, 0, 0.37))
    grid_case("rotate_xyz", rotate(base, 0.21, 0.37, 0.53))
    grid_case("stagger_half_cell_alternate_rings", tube(32, 100, 40.0, stagger=True))
    for sigma in (1e-5, 1e-3):
        for axes in ("xyz", "x", "y", "z"):
            grid_case(f"jitter_{sigma:g}_{axes}", jitter(base, sigma, axes))
    v = base.reshape(-1, 3).astype(np.float32).astype(np.float64)
    f = lean_faces(100, 32)
    cases.append({"case": "leaning_strip_32x100", "triangles": int(len(f)), "surfaceCheck_locations": surface_check("lean_32x100", v, f)})
    print(cases[-1])
    args.out.write_text(json.dumps({"surfaceCheck": "OpenFOAM v1912, -checkSelfIntersection -outputThreshold 100", "cases": cases}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""INFORMATION ONLY (not part of the step-0 gate): the barrel B0a with the plain 02 quad split (max-min-angle diagonal, NO 02c leaning
strip, NO 02d flip), to show whether the surfaceCheck harness responds to exactly x-parallel meridian edges on a constant section.
Same rings, caps, float32 rounding and orientation as r7_barrel.B0a.

How to run: uv run --no-project r7_barrel_quad.py --out-dir <new dir>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

import r7_common

r7_common.add_paths()
import r6_mesh  # noqa: E402
import r6_tess  # noqa: E402
import r7_barrel  # noqa: E402
import r7_flip  # noqa: E402
import r7_surface  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    p = r7_barrel.BARREL_PARAMS
    st = r7_barrel.stations_for("B0a")
    model = r7_barrel.make_model("B0a", st["model_xj"], st["model_xt"])
    xs = st["plateau"]
    rings = [model.ring(x, p["n_points"]) for x in xs]
    points = np.stack([r7_surface.closure_ring(rings[0], xs[0] - p["closure_band_m"], p["closure_end_ring_scale"])] + rings + [r7_surface.closure_ring(rings[-1], xs[-1] + p["closure_band_m"], p["closure_end_ring_scale"])])
    rows, cols, _ = points.shape
    vertices, faces = r6_tess.grid_triangles(points)
    all_faces = [faces]
    for row in (0, rows - 1):
        ids = row * cols + np.arange(cols)
        new, cap = r6_tess.round_cap(vertices, ids)
        cap = r7_common.orient_cap(np.vstack(all_faces), cap, ids)
        vertices = np.vstack([vertices, new])
        all_faces.append(np.asarray(cap, dtype=np.int64))
    faces = np.vstack(all_faces)
    vertices = vertices.astype(np.float32).astype(np.float64)
    if r7_common.signed_volume(vertices, faces) < 0:
        faces = faces[:, ::-1].copy()
    r6_mesh.write_stl(args.out_dir / "B0a-quad.stl", vertices[faces])
    print("B0a-quad triangles", len(faces), "axis-parallel edges", len(r7_flip.axis_parallel_edges(vertices, faces)))


if __name__ == "__main__":
    main()

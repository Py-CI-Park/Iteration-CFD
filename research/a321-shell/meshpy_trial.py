#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "meshpy", "trimesh", "manifold3d"]
# ///
# How to run: uv run meshpy_trial.py > artifacts/meshpy.log 2>&1
"""Independent CPU PLC tetrahedralization of shell exterior, no flow solver."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import trimesh
from meshpy import tet

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Retain shell triangulation and subtract a verified interior seed from a box."""
    out = ROOT / "artifacts/meshpy-r1"
    out.mkdir(parents=True, exist_ok=False)
    source = trimesh.load_mesh(
        ROOT / "artifacts/shell-r2/A321_AIRFRAME_SHELL_R2.stl", process=True
    )
    points = source.vertices.tolist()
    count = len(points)
    box = [
        [-45, -65, -45],
        [135, -65, -45],
        [135, 65, -45],
        [-45, 65, -45],
        [-45, -65, 55],
        [135, -65, 55],
        [135, 65, 55],
        [-45, 65, 55],
    ]
    points.extend(box)
    facets = source.faces.tolist()
    markers = [1] * len(facets)
    faces = [
        [0, 3, 2, 1],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
    ]
    facets.extend([[count + i for i in f] for f in faces])
    markers.extend(range(2, 8))
    info = tet.MeshInfo()
    info.set_points(points)
    info.set_facets(facets, markers=markers)
    info.set_holes([[22, 0, 4]])
    start = time.monotonic()
    mesh = tet.build(info, options=tet.Options("pq1.4a100YQ"), verbose=False)
    vertices = np.array(mesh.points)
    cells = np.array(mesh.elements)
    t = vertices[cells]
    signed = (
        np.einsum(
            "ij,ij->i",
            np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]),
            t[:, 3] - t[:, 0],
        )
        / 6
    )
    np.savez_compressed(out / "fluid.npz", vertices=vertices, cells=cells)
    # Independent mesh_readback.py writes VTK and audits saved tetrahedra.
    expected = 180 * 130 * 100 - source.volume
    report = {
        "status": "CPU_PLC_TETRAHEDRA_ONLY",
        "cells": len(cells),
        "points": len(vertices),
        "min_signed_volume_m3": float(signed.min()),
        "max_signed_volume_m3": float(signed.max()),
        "absolute_total_volume_m3": float(np.abs(signed).sum()),
        "expected_fluid_volume_m3": float(expected),
        "relative_volume_error": float(abs(np.abs(signed).sum() - expected) / expected),
        "seconds": time.monotonic() - start,
        "boundary_layers": 0,
        "gpu_compute": False,
        "not_ready_reasons": [
            "no prism layers",
            "no y+",
            "no ofgpu conversion",
            "quality and boundary mapping pending",
        ],
    }
    (ROOT / "evidence/meshpy.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()

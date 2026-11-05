#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run mesh_readback.py; reads existing CPU tetrahedra, never meshes/solves.
"""Recover exact stored tetrahedra and evaluate volume, shape and boundary mapping."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Write ASCII VTK and standalone quality receipt without rerunning TetGen."""
    out = ROOT / "artifacts/meshpy-r1"
    with np.load(out / "fluid.npz") as data:
        v, c = data["vertices"], data["cells"]
    t = v[c]
    volume = (
        np.einsum(
            "ij,ij->i",
            np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]),
            t[:, 3] - t[:, 0],
        )
        / 6
    )
    edge2 = sum(
        ((t[:, i] - t[:, j]) ** 2).sum(axis=1)
        for i, j in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    )
    mean_ratio = 12 * (3 * np.abs(volume)) ** (2 / 3) / edge2
    faces = np.concatenate(
        [c[:, [1, 2, 3]], c[:, [0, 3, 2]], c[:, [0, 1, 3]], c[:, [0, 2, 1]]]
    )
    keys = np.sort(faces, axis=1)
    _, idx, inverse, counts = np.unique(
        keys, axis=0, return_index=True, return_inverse=True, return_counts=True
    )
    owners = np.tile(np.arange(len(c)), 4)
    order = np.argsort(inverse, kind="stable")
    offsets = np.concatenate(([0], np.cumsum(counts)))
    internal = np.flatnonzero(counts == 2)
    pairs = np.column_stack(
        [owners[order[offsets[internal]]], owners[order[offsets[internal] + 1]]]
    )
    graph = coo_matrix(
        (np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(c), len(c))
    )
    n_components, _ = connected_components(graph, directed=False)
    boundary = faces[idx[counts == 1]]
    pts = v[boundary]
    patch = np.full(len(boundary), 6, dtype=np.int8)
    for i, (axis, value) in enumerate(
        [(0, -45), (0, 135), (1, -65), (1, 65), (2, -45), (2, 55)]
    ):
        patch[np.max(np.abs(pts[:, :, axis] - value), axis=1) < 1e-8] = i
    np.savez_compressed(out / "boundary.npz", faces=boundary, patch=patch)
    names = ["inlet", "outlet", "yMin", "yMax", "zMin", "zMax", "wall_aircraft"]
    with (out / "fluid.vtk").open("w", encoding="ascii", newline="\n") as f:
        f.write(
            "# vtk DataFile Version 3.0\nA321 CPU tet mesh NOT AERO ACCEPTED\nASCII\nDATASET UNSTRUCTURED_GRID\n"
        )
        f.write(f"POINTS {len(v)} double\n")
        np.savetxt(f, v, fmt="%.17g")
        f.write(f"CELLS {len(c)} {len(c) * 5}\n")
        np.savetxt(f, np.column_stack((np.full(len(c), 4), c)), fmt="%d")
        f.write(f"CELL_TYPES {len(c)}\n")
        np.savetxt(f, np.full(len(c), 10), fmt="%d")
    expected = 180 * 130 * 100 - 504.66135158409384
    record = {
        "status": "CPU_VOLUME_MESH_DONE_NOT_AERO_ACCEPTED",
        "cells": len(c),
        "points": len(v),
        "min_volume_m3": float(volume.min()),
        "nonpositive_cells": int(np.count_nonzero(volume <= 0)),
        "total_volume_m3": float(volume.sum()),
        "expected_volume_m3": expected,
        "relative_volume_error": float(abs(volume.sum() - expected) / expected),
        "mean_ratio_min": float(mean_ratio.min()),
        "mean_ratio_p01": float(np.quantile(mean_ratio, 0.01)),
        "cells_mean_ratio_below_0_01": int(np.count_nonzero(mean_ratio < 0.01)),
        "fluid_connected_components": n_components,
        "nonmanifold_cell_faces": int(np.count_nonzero(counts > 2)),
        "boundary_triangles": {
            name: int(np.count_nonzero(patch == i)) for i, name in enumerate(names)
        },
        "boundary_layers": 0,
        "gpu_compute": False,
        "solver_run": False,
        "not_ready_reasons": [
            "near-zero-volume slivers",
            "no boundary layers",
            "no y+",
            "no domain/mesh independence",
            "ofgpu acceptance untested",
        ],
    }
    (ROOT / "evidence/cpu-mesh-readback.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()

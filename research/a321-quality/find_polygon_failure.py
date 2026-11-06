#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: uv run find_polygon_failure.py; extract small real-cell regression fixtures only.
"""Capture difficult actual boundary polygons without rerunning a mesher."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from poly_io import read_faces, read_patches, read_points
from polygon_triangles import triangulate


def main() -> None:
    """Record the first twelve ear-clipping failures with their exact source coordinates."""
    root = Path(__file__).resolve().parent
    pm = root / "artifacts/snappy-03/constant/polyMesh"
    v = read_points(pm / "points")
    f = read_faces(pm / "faces")
    patch = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
    results = []
    for i, row in enumerate(f[patch.start : patch.start + patch.count]):
        row = row[row >= 0]
        points = v[row]
        center = points.mean(axis=0)
        cross = np.cross(points - center, np.roll(points, -1, axis=0) - center)
        normal = cross.sum(axis=0)
        if np.all(cross @ normal > 1e-14 * np.dot(normal, normal)):
            continue
        try:
            triangulate(points)
        except RuntimeError as error:
            results.append(
                {
                    "wall_face": i,
                    "global_face": patch.start + i,
                    "error": str(error),
                    "vertices": points.tolist(),
                }
            )
            if len(results) == 12:
                break
    (root / "evidence/polygon-regression-fixtures.json").write_text(
        json.dumps(results, indent=2), encoding="utf8"
    )
    print(json.dumps(results[:2]))


if __name__ == "__main__":
    main()

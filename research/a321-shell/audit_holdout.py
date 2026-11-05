#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "rtree"]
# ///
# How to run: uv run audit_holdout.py
"""Check midpoint sections excluded from loft station construction and sampled distances."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
from profiles import section_points
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Use 12 interior station midpoints per part and bidirectional sampled proximity."""
    record = json.loads((ROOT / "evidence/reconstruction-r2.json").read_text())
    results = []
    for part in record["parts"]:
        name = part["name"]
        axis = part["axis"]
        stations = np.array(part["stations_m"])
        with np.load(ROOT / f"artifacts/reference/{name}.npz") as d:
            v, f = d["vertices"], d["faces"]
        original = trimesh.Trimesh(v, f, process=False)
        shell = trimesh.load_mesh(ROOT / f"artifacts/shell-r2/{name}.stl", process=True)
        mids = (stations[:-1] + stations[1:]) / 2
        # Avoid artificial endpoint caps when evaluating held-out interior stations.
        indices = np.linspace(2, len(mids) - 3, 12, dtype=int)
        rows = []
        for index in indices:
            s = float(mids[index])
            a = section_points(v, f, axis, s)
            b = section_points(shell.vertices, shell.faces, axis, s)
            delta = np.vstack(
                (a.min(axis=0) - b.min(axis=0), a.max(axis=0) - b.max(axis=0))
            )
            rows.append(
                {
                    "station_m": s,
                    "bounds_max_delta_m": float(np.max(np.abs(delta))),
                    "convex_area_relative_delta": float(
                        ConvexHull(b).volume / ConvexHull(a).volume - 1
                    ),
                }
            )
        take = np.linspace(0, len(v) - 1, min(2500, len(v)), dtype=int)
        _, distance, _ = trimesh.proximity.closest_point(shell, v[take])
        reverse = np.linspace(
            0, len(shell.vertices) - 1, min(2500, len(shell.vertices)), dtype=int
        )
        _, back, _ = trimesh.proximity.closest_point(original, shell.vertices[reverse])
        results.append(
            {
                "part": name,
                "holdout_sections": rows,
                "holdout_bounds_max_m": max(r["bounds_max_delta_m"] for r in rows),
                "sample_reference_to_shell": {
                    "count": len(take),
                    "p95_m": float(np.quantile(distance, 0.95)),
                    "max_m": float(distance.max()),
                },
                "sample_shell_to_reference": {
                    "count": len(reverse),
                    "p95_m": float(np.quantile(back, 0.95)),
                    "max_m": float(back.max()),
                },
            }
        )
    receipt = {
        "method": "held-out midpoint sections + evenly indexed vertex-to-triangle proximity; not Hausdorff or curvature proof",
        "parts": results,
        "engineering_status": "NOT_VALIDATED",
        "gpu_compute": False,
    }
    (ROOT / "evidence/holdout.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf8"
    )
    print(json.dumps({r["part"]: r["holdout_bounds_max_m"] for r in results}))


if __name__ == "__main__":
    main()

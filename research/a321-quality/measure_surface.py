#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh", "scipy", "rtree", "typer", "networkx"]
# ///
# How to run: uv run measure_surface.py --surface <STL>. CPU geometry diagnostics.
"""Measure a computational surface against R3 without declaring a global distance guarantee."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import numpy as np
import trimesh
import typer

ROOT: Final = Path(__file__).resolve().parent


def main(surface: Path = ROOT / "artifacts/netgen-surface-04/surface.stl") -> None:
    """Report triangle conditioning and two-way seeded surface samples."""
    mesh = trimesh.load_mesh(surface, process=True)
    reference = trimesh.load_mesh(
        ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl", process=True
    )
    distances = []
    for a, b, label in [
        (reference, mesh, "reference_to_candidate"),
        (mesh, reference, "candidate_to_reference"),
    ]:
        _, d, _ = trimesh.proximity.closest_point(b, a.sample(12000, seed=20261106))
        distances.append(
            {
                "direction": label,
                "samples": len(d),
                "max_m": float(d.max()),
                "p95_m": float(np.quantile(d, 0.95)),
            }
        )
    result = {
        "surface": str(surface),
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "closed": bool(mesh.is_watertight),
        "winding": bool(mesh.is_winding_consistent),
        "components": len(mesh.split()),
        "minimum_triangle_angle_deg": float(np.degrees(mesh.face_angles).min()),
        "minimum_edge_m": float(mesh.edges_unique_length.min()),
        "distances": distances,
        "gpu_compute": False,
        "solver_run": False,
    }
    (ROOT / "evidence" / f"{surface.parent.name}-surface-metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    typer.run(main)

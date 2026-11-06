#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "typer", "pydantic>=2"]
# ///
# How to run: install uv, then uv run audit_poly.py --case <case-directory>. No solver.
"""Audit serialized general-polyhedron geometry and reference fidelity on the CPU."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Final

import numpy as np
import trimesh
import typer
from custody import digest, require_unchanged, snapshot_mesh, trial_directory
from poly_geometry import cell_geometry
from poly_io import read_faces, read_labels, read_patches, read_points
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from wall_surface import raw_wall_closed, triangulate_wall

ROOT: Final = Path(__file__).resolve().parent


def main(case: Path = ROOT / "artifacts/snappy-01", run_id: str = "v5") -> None:
    """Reconstruct cells and inspect exact saved faces rather than generator-only arrays."""
    case = trial_directory(case, ROOT / "artifacts")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,30}", run_id):
        raise RuntimeError("BAD_AUDIT_RUN_ID")
    targets = [
        case / f"calculation-wall-{run_id}.stl",
        case / f"audited-geometry-{run_id}.npz",
        ROOT / "evidence" / f"{case.name}-audit-{run_id}.json",
    ]
    if any(p.exists() for p in targets):
        raise RuntimeError("AUDIT_OUTPUT_ALREADY_EXISTS")
    (case / f".audit-{run_id}.lock").mkdir(exist_ok=False)
    before = snapshot_mesh(case)
    pm = case / "constant/polyMesh"
    print("READ_POLYMESH", flush=True)
    v = read_points(pm / "points")
    f = read_faces(pm / "faces")
    o = read_labels(pm / "owner")
    n = read_labels(pm / "neighbour")
    patches = read_patches(pm / "boundary")
    ni = len(n)
    if len(o) != len(f) or np.any(o[:ni] >= n):
        raise RuntimeError("BAD_OWNER_NEIGHBOUR")
    print("RECONSTRUCT_GEOMETRY", len(f), flush=True)
    sf, _cf, c, volume, closure = cell_geometry(v, f, o, n)
    delta = c[n] - c[o[:ni]]
    cosine = np.einsum("ij,ij->i", sf[:ni], delta) / (
        np.linalg.norm(sf[:ni], axis=1) * np.linalg.norm(delta, axis=1)
    )
    angles = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
    relative = np.linalg.norm(closure, axis=1) / volume ** (2 / 3)
    graph = coo_matrix((np.ones(ni), (o[:ni], n)), shape=(len(c), len(c)))
    components, _ = connected_components(graph, directed=False)
    start = ni
    for p in patches:
        if p.start != start:
            raise RuntimeError("PATCH_GAP_OR_OVERLAP")
        start += p.count
    if start != len(f):
        raise RuntimeError("INCOMPLETE_BOUNDARY")
    walls = [p for p in patches if p.kind == "wall"]
    if len(walls) != 1:
        raise RuntimeError("EXPECTED_ONE_AIRCRAFT_WALL")
    p = walls[0]
    wall = f[p.start : p.start + p.count]
    surface = triangulate_wall(v, wall)
    exact_topology_closed = raw_wall_closed(wall)
    reference_path = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    reference = trimesh.load_mesh(reference_path, process=True)
    distances = []
    for a, b, label in [
        (reference, surface, "R3_to_calculation"),
        (surface, reference, "calculation_to_R3"),
    ]:
        samples = a.sample(12000, seed=20261106)
        _, d, _ = trimesh.proximity.closest_point(b, samples)
        distances.append(
            {
                "direction": label,
                "samples": len(d),
                "max_m": float(d.max()),
                "p95_m": float(np.quantile(d, 0.95)),
            }
        )
    record = {
        "candidate": case.name,
        "cell_family": "hex_dominant_polyhedra, not tetrahedra",
        "cells": len(c),
        "points": len(v),
        "faces": len(f),
        "max_face_arity": f.shape[1],
        "internal_faces": ni,
        "fluid_components": components,
        "nonpositive_volumes": int(np.count_nonzero(volume <= 0)),
        "min_volume_m3": float(volume.min()),
        "max_nonorth_deg": float(angles.max()),
        "faces_nonorth_gt70": int(np.count_nonzero(angles > 70)),
        "max_relative_closure": float(relative.max()),
        "max_absolute_closure_m2": float(np.linalg.norm(closure, axis=1).max()),
        "wall_faces": p.count,
        "wall_closed": bool(exact_topology_closed and surface.is_watertight),
        "raw_wall_edge_incidence_closed": exact_topology_closed,
        "cell_geometry_method": "signed triangle tetrahedral moments; arithmetic face-center fan defines warped face surface",
        "wall_winding": bool(surface.is_winding_consistent),
        "wall_volume_m3": float(abs(surface.volume)),
        "reference_volume_m3": float(reference.volume),
        "sampled_surface_distance": distances,
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "thresholds": {"nonorth_deg": 70, "relative_closure": 1e-10},
        "nonorth_closure_gate": bool(
            angles.max() <= 70 and relative.max() <= 1e-10 and components == 1
        ),
        "boundary_layer_coverage": "SEE_EXTERNAL_LAYER_LOG_AND_FIELDS",
        "solved_y_plus": "NOT_MEASURED",
        "solver_run": False,
        "gpu_compute": False,
        "polyMesh_sha256": before.model_dump(),
        "mesh_unchanged_during_audit": True,
    }
    require_unchanged(case, before)
    surface.export(case / f"calculation-wall-{run_id}.stl")
    centers_path = case / f"audited-geometry-{run_id}.npz"
    np.savez_compressed(
        centers_path,
        centers=c,
        volume=volume,
        nonorth=angles,
        relative_closure=relative,
    )
    record["audited_geometry_sha256"] = digest(centers_path)
    (ROOT / "evidence" / f"{case.name}-audit-{run_id}.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    typer.run(main)

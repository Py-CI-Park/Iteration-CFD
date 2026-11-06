#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pyvista", "pyacvd", "trimesh", "networkx", "manifold3d"]
# ///
# How to run: uv run surface_trial.py; CPU-only surface trial, no volume solver.
"""Check whether denser isotropic remeshing can avoid old tiny Boolean triangles."""

from __future__ import annotations

import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import pyacvd
import pyvista as pv
import trimesh

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Try 30000 clusters and publish only diagnostic topology, not a substitute baseline."""
    out = ROOT / "artifacts/remesh-30k"
    out.mkdir(exist_ok=False)
    s = pv.read(str(ROOT / "models/A321_AIRFRAME_SHELL_R3.stl")).clean().triangulate()
    clusters = pyacvd.Clustering(s)
    clusters.subdivide(1)
    clusters.cluster(30000)
    final = clusters.create_mesh().clean().triangulate()
    mesh = trimesh.Trimesh(
        np.array(final.points), final.faces.reshape(-1, 4)[:, 1:], process=True
    )
    trimesh.repair.fix_normals(mesh)
    solid = mf.Manifold(
        mf.Mesh(mesh.vertices.astype(np.float32), mesh.faces.astype(np.uint32))
    )
    mesh.export(out / "surface.stl")
    lengths = mesh.edges_unique_length
    result = {
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
        "watertight": bool(mesh.is_watertight),
        "winding": bool(mesh.is_winding_consistent),
        "kernel_status": str(solid.status()),
        "edge_min_m": float(lengths.min()),
        "edge_p01_m": float(np.quantile(lengths, 0.01)),
        "status": "SURFACE_ONLY_CANDIDATE"
        if mesh.is_watertight and solid.status() == mf.Error.NoError
        else "REJECTED",
        "gpu_compute": False,
        "fidelity_check": "NOT_RUN",
    }
    np.savez_compressed(out / "surface.npz", vertices=mesh.vertices, faces=mesh.faces)
    (ROOT / "evidence/remesh-30k.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()

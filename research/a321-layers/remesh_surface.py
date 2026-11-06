#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pymeshlab", "trimesh", "manifold3d", "rtree", "scipy"]
# ///
# How to run: uv run remesh_surface.py (fixed fresh candidate directory).
"""Reference-constrained isotropic surface trial; never overwrites the R3 baseline."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import manifold3d as mf
import numpy as np
import pymeshlab as ml
import trimesh

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Regularize boundary triangles, check topology and measured two-way proximity."""
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745":
        raise RuntimeError("R3_SHA_MISMATCH")
    out = ROOT / "artifacts/isotropic-01"
    out.mkdir(exist_ok=False)
    original = trimesh.load_mesh(source, process=True)
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(vertex_matrix=original.vertices, face_matrix=original.faces))
    start = time.monotonic()
    ms.meshing_isotropic_explicit_remeshing(
        iterations=8,
        targetlen=ml.PureValue(0.18),
        featuredeg=45.0,
        checksurfdist=True,
        maxsurfdist=ml.PureValue(0.004),
        adaptive=False,
    )
    data = ms.current_mesh()
    v = data.vertex_matrix()
    f = data.face_matrix()
    mesh = trimesh.Trimesh(v, f, process=False)
    mesh.export(out / "surface.stl")
    np.savez_compressed(out / "surface.npz", vertices=v, faces=f)
    solid = mf.Manifold(mf.Mesh(v.astype(np.float32), f.astype(np.uint32)))
    tri = v[f]
    lengths = mesh.edges_unique_length
    area2 = np.linalg.norm(
        np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1
    )
    edge2 = sum(
        ((tri[:, i] - tri[:, j]) ** 2).sum(axis=1) for i, j in [(0, 1), (1, 2), (2, 0)]
    )
    quality = 2 * np.sqrt(3) * area2 / edge2
    samples = []
    for a, b, name in [
        (original, mesh, "R3_to_candidate"),
        (mesh, original, "candidate_to_R3"),
    ]:
        take = np.linspace(
            0, len(a.vertices) - 1, min(6000, len(a.vertices)), dtype=int
        )
        _, distance, _ = trimesh.proximity.closest_point(b, a.vertices[take])
        samples.append(
            {
                "direction": name,
                "samples": len(take),
                "p95_m": float(np.quantile(distance, 0.95)),
                "max_m": float(distance.max()),
            }
        )
    report = {
        "source_sha256": digest,
        "triangles": len(f),
        "vertices": len(v),
        "watertight": bool(mesh.is_watertight),
        "winding": bool(mesh.is_winding_consistent),
        "kernel_status": str(solid.status()),
        "edge_min_m": float(lengths.min()),
        "edge_p01_m": float(np.quantile(lengths, 0.01)),
        "triangle_mean_ratio_min": float(quality.min()),
        "triangle_mean_ratio_p01": float(np.quantile(quality, 0.01)),
        "sampled_proximity": samples,
        "surface_operation_tolerance_m": 0.004,
        "seconds": time.monotonic() - start,
        "gpu_compute": False,
        "geometry_status": "R3_APPROXIMATION_NOT_BYTE_IDENTICAL; measured sample bound not full Hausdorff",
    }
    (ROOT / "evidence/isotropic-01.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()

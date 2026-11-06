#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pyvista", "pyacvd", "trimesh", "meshpy", "manifold3d", "networkx"]
# ///
# How to run: uv run layer_mesh.py > artifacts/layer-mesh.log 2>&1
"""Quasiuniform CPU surface remeshing, explicit prism layers, exterior tetrahedra."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import manifold3d as mf
import numpy as np
import pyvista as pv
import trimesh
from meshpy import tet

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Build a measured diagnostic hybrid mesh; never silently promote it to solver-ready."""
    out = ROOT / "artifacts/hybrid-r5"
    out.mkdir(parents=True, exist_ok=False)
    os.chdir(out)
    start = time.monotonic()
    source = (
        pv.read(str(ROOT / "artifacts/shell-r3/A321_AIRFRAME_SHELL_R3.stl"))
        .clean()
        .triangulate()
    )
    vertices = np.array(source.points, dtype=np.float32)
    faces = source.faces.reshape(-1, 4)[:, 1:].astype(np.uint32)
    packed = mf.Manifold(mf.Mesh(vertices, faces)).to_mesh()
    vertices = np.array(packed.vert_properties[:, :3], dtype=np.float64)
    faces = np.array(packed.tri_verts, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices, faces, process=True)
    trimesh.repair.fix_normals(mesh)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise RuntimeError("REMESH_NOT_CLOSED_ORIENTED")
    vertices, faces = mesh.vertices, mesh.faces
    mesh.export(out / "remeshed.stl")
    np.savez_compressed(out / "surface.npz", vertices=vertices, faces=faces)
    print(f"SURFACE {len(vertices)} vertices {len(faces)} triangles", flush=True)
    # Vertex normals averaged across the closed skin. Small explicit layers remain a trial.
    normals = mesh.vertex_normals
    heights = np.array([0.0, 0.001, 0.0023, 0.00399, 0.006187, 0.0090431])
    # Restrict extrusion near tiny leading/trailing-edge and Boolean-junction edges.
    edges = mesh.edges_unique
    lengths = np.linalg.norm(vertices[edges[:, 1]] - vertices[edges[:, 0]], axis=1)
    minimum = np.full(len(vertices), np.inf)
    np.minimum.at(minimum, edges[:, 0], lengths)
    np.minimum.at(minimum, edges[:, 1], lengths)
    scale = np.minimum(1.0, 0.002 * minimum / heights[-1])
    layers = np.array([vertices + h * scale[:, None] * normals for h in heights])
    n = len(vertices)
    prisms = []
    for k in range(len(heights) - 1):
        prisms.append(np.column_stack((faces + k * n, faces + (k + 1) * n)))
    prisms = np.concatenate(prisms)
    outer = trimesh.Trimesh(layers[-1], faces, process=False)
    outer.export(out / "layer-outer.stl")
    info = tet.MeshInfo()
    # A subdivided closed outer box avoids the prior 2-triangle farfield patches.
    boundary = trimesh.creation.box(extents=[180, 130, 100])
    boundary.apply_translation([45, 0, 5])
    boundary = boundary.subdivide().subdivide().subdivide()
    far_vertices, far_faces = boundary.vertices, boundary.faces
    points = np.vstack((layers[-1], far_vertices))
    facets = np.vstack((faces, far_faces + n))
    info.set_points(points.tolist())
    info.set_facets(facets.tolist())
    info.set_holes([[22, 0, 4]])
    print("TETGEN_START", flush=True)
    result = tet.build(info, options=tet.Options("pYQ"), verbose=False)
    tv = np.array(result.points)
    tc = np.array(result.elements, dtype=np.int64)
    # Input point sequence is preserved by TetGen; confirm the layer outer interface exactly.
    if not np.array_equal(tv[:n], layers[-1]):
        raise RuntimeError("INTERFACE_POINT_ORDER_CHANGED")
    all_vertices = np.vstack((layers[:-1].reshape(-1, 3), tv))
    tets = tc + (len(heights) - 1) * n
    np.savez_compressed(
        out / "hybrid.npz",
        vertices=all_vertices,
        tets=tets,
        prisms=prisms,
        wall_faces=faces,
        heights=heights,
        layer_scale=scale,
    )
    report = {
        "status": "HYBRID_GENERATED_QUALITY_PENDING",
        "surface_triangles": len(faces),
        "surface_vertices": n,
        "prism_cells": len(prisms),
        "tet_cells": len(tets),
        "layers": len(heights) - 1,
        "heights_m": heights.tolist(),
        "seconds": time.monotonic() - start,
        "gpu_compute": False,
        "warning": "vertex-normal extrusion; quality/fidelity/collision tests required before any solver",
    }
    (ROOT / "evidence/hybrid-build.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "gmsh==4.15.2", "trimesh", "manifold3d"]
# ///
# How to run: uv run cpu_mesh.py > artifacts/cpu-mesh.log 2>&1
"""Attempt a CPU-only coarse tetrahedral fluid domain around a simplified shell."""

from __future__ import annotations

import json
import time
from pathlib import Path

import gmsh
import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Build a discretized surface and outer box; report quality without solving flow."""
    out = ROOT / "artifacts/cpu-mesh-r2"
    out.mkdir(parents=True, exist_ok=False)
    source = trimesh.load_mesh(
        ROOT / "artifacts/shell-r2/A321_AIRFRAME_SHELL_R2.stl", process=True
    )
    solid = mf.Manifold(
        mf.Mesh(source.vertices.astype(np.float32), source.faces.astype(np.uint32))
    )
    simplified = solid.simplify(0.025)
    packed = simplified.to_mesh()
    tri = trimesh.Trimesh(
        packed.vert_properties[:, :3], packed.tri_verts, process=False
    )
    tri.export(out / "mesh-surface.stl")
    start = time.monotonic()
    gmsh.initialize()
    gmsh.option.setNumber("General.NumThreads", 4)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", 4)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.35)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 8)
    gmsh.option.setNumber("Mesh.Algorithm3D", 1)
    gmsh.option.setNumber("Mesh.MshFileVersion", 4.1)
    gmsh.option.setNumber("Mesh.Binary", 0)
    try:
        gmsh.model.add("A321_exploratory_fluid")
        gmsh.merge(str(out / "mesh-surface.stl"))
        gmsh.model.mesh.classifySurfaces(np.pi / 3, True, True, np.pi)
        gmsh.model.mesh.createGeometry()
        inner = [tag for dim, tag in gmsh.model.getEntities(2)]
        body_loop = gmsh.model.geo.addSurfaceLoop(inner)
        # Geometry-demo domain, not a domain-independent external aero choice.
        bounds = [-45, 135, -65, 65, -45, 55]
        corners = [
            (bounds[i], bounds[2 + j], bounds[4 + k])
            for k in range(2)
            for j in range(2)
            for i in range(2)
        ]
        points = [gmsh.model.geo.addPoint(*xyz, 8) for xyz in corners]
        connections = [
            (0, 1),
            (1, 3),
            (3, 2),
            (2, 0),
            (4, 5),
            (5, 7),
            (7, 6),
            (6, 4),
            (0, 4),
            (1, 5),
            (3, 7),
            (2, 6),
        ]
        lines = [gmsh.model.geo.addLine(points[a], points[b]) for a, b in connections]
        loops = [
            [-4, -3, -2, -1],
            [5, 6, 7, 8],
            [1, 10, -5, -9],
            [2, 11, -6, -10],
            [3, 12, -7, -11],
            [4, 9, -8, -12],
        ]
        surfaces = [
            gmsh.model.geo.addPlaneSurface(
                [
                    gmsh.model.geo.addCurveLoop(
                        [lines[abs(i) - 1] * (1 if i > 0 else -1) for i in loop]
                    )
                ]
            )
            for loop in loops
        ]
        outer = gmsh.model.geo.addSurfaceLoop(surfaces)
        volume = gmsh.model.geo.addVolume([outer, body_loop])
        gmsh.model.geo.synchronize()
        gmsh.model.addPhysicalGroup(2, inner, name="wall_aircraft")
        for surface, name in zip(
            surfaces, ["zMin", "zMax", "yMin", "outlet", "yMax", "inlet"]
        ):
            gmsh.model.addPhysicalGroup(2, [surface], name=name)
        gmsh.model.addPhysicalGroup(3, [volume], name="fluid")
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("Netgen")
        element_types, element_tags, _ = gmsh.model.mesh.getElements(3)
        tags = np.concatenate(element_tags)
        q = np.array(gmsh.model.mesh.getElementQualities(tags.tolist(), "minSICN"))
        volumes = np.array(gmsh.model.mesh.getElementQualities(tags.tolist(), "volume"))
        gmsh.write(str(out / "fluid.msh"))
        gmsh.write(str(out / "fluid.vtk"))
        record = {
            "status": "CPU_COARSE_MESH_GENERATED_NOT_AERO_ACCEPTED",
            "cells": len(tags),
            "element_types": element_types.tolist(),
            "minSICN_min": float(q.min()),
            "minSICN_p01": float(np.quantile(q, 0.01)),
            "min_volume_m3": float(volumes.min()),
            "total_volume_m3": float(volumes.sum()),
            "surface_triangles": len(tri.faces),
            "surface_simplify_tolerance_m": 0.025,
            "domain_extent_m": bounds,
            "seconds": time.monotonic() - start,
            "boundary_layers": 0,
            "limitations": [
                "no prism layers",
                "no y+ measurement",
                "no domain independence",
                "no solver run",
                "no solver-format conversion",
            ],
            "gpu_compute": False,
        }
    finally:
        gmsh.finalize()
    (ROOT / "evidence/cpu-mesh-r2.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()

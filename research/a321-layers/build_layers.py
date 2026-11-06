#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "networkx"]
# ///
# How to run: uv run build_layers.py; surface/layer diagnosis only, no solver.
"""Construct outward-constrained prism trial, reject every sampled folded cell before volume meshing."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import trimesh
from normal_field import constrained_directions

ROOT = Path(__file__).resolve().parent


def jacobian_minimum(vertices: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Minimize determinant analytically: affine in triangle coordinates, quadratic in height."""
    p = vertices[cells]
    minimum = np.full(len(cells), np.inf)
    for r, s in [(0, 0), (1, 0), (0, 1)]:
        samples = []
        for t in [0.0, 0.5, 1.0]:
            dr = (1 - t) * (p[:, 1] - p[:, 0]) + t * (p[:, 4] - p[:, 3])
            ds = (1 - t) * (p[:, 2] - p[:, 0]) + t * (p[:, 5] - p[:, 3])
            dt = (
                (1 - r - s) * (p[:, 3] - p[:, 0])
                + r * (p[:, 4] - p[:, 1])
                + s * (p[:, 5] - p[:, 2])
            )
            samples.append(np.einsum("ij,ij->i", np.cross(dr, ds), dt))
        y0, ym, y1 = samples
        a = 2 * (y0 + y1 - 2 * ym)
        b = y1 - y0 - a
        stationary = np.zeros_like(a)
        np.divide(-b, 2 * a, out=stationary, where=a > 0)
        interior = (a > 0) & (stationary > 0) & (stationary < 1)
        exact = np.minimum(y0, y1)
        exact[interior] = np.minimum(
            exact[interior], (a * stationary**2 + b * stationary + y0)[interior]
        )
        minimum = np.minimum(minimum, exact)
    return minimum


def require_positive_jacobians(values: np.ndarray) -> None:
    """Fail closed for a folded, zero-volume or nonfinite candidate."""
    if not np.all(np.isfinite(values) & (values > 0)):
        raise RuntimeError("LAYER_JACOBIAN_REJECTED")


def main() -> None:
    """Build exact-R3 trial using all incident face constraints and curvature-limited thickness."""
    start = time.monotonic()
    out = ROOT / "artifacts/constrained-exact-02"
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
    ):
        raise RuntimeError("R3_SHA_MISMATCH")
    mesh = trimesh.load_mesh(source, process=True)
    v, f = mesh.vertices, mesh.faces
    incident = [[] for _ in v]
    for face_id, row in enumerate(f):
        for i in row:
            incident[i].append(face_id)
    normals = constrained_directions(mesh.face_normals, [np.array(x) for x in incident])
    projections = np.einsum("ijk,ik->ij", normals[f], mesh.face_normals)
    heights = np.r_[0.0, np.cumsum(0.0005 * 1.2 ** np.arange(8))]
    edges = mesh.edges_unique
    length = np.linalg.norm(v[edges[:, 0]] - v[edges[:, 1]], axis=1)
    local = np.full(len(v), np.inf)
    np.minimum.at(local, edges[:, 0], length)
    np.minimum.at(local, edges[:, 1], length)
    # Start with moderate edge cap; finite Jacobian polynomial is checked before accepting any trial.
    scale = np.minimum(1.0, 0.05 * local / heights[-1])
    attempts = []
    for attempt in range(8):
        layers = np.array([v + h * scale[:, None] * normals for h in heights])
        n = len(v)
        cells = np.concatenate(
            [
                np.column_stack((f + k * n, f + (k + 1) * n))
                for k in range(len(heights) - 1)
            ]
        )
        jac = jacobian_minimum(layers.reshape(-1, 3), cells)
        bad = np.flatnonzero(~np.isfinite(jac) | (jac <= 0))
        attempts.append(
            {
                "attempt": attempt,
                "bad_prisms": len(bad),
                "min_jacobian_m3": float(jac.min()),
            }
        )
        if not len(bad):
            break
        if attempt < 7:
            affected = np.unique(cells[bad] % n)
            scale[affected] *= 0.25
    np.savez_compressed(
        out / ("layers.npz" if not len(bad) else "rejected-layers.npz"),
        vertices=layers.reshape(-1, 3),
        prisms=cells,
        wall_faces=f,
        directions=normals,
        scale=scale,
        heights=heights,
    )
    outer = trimesh.Trimesh(layers[-1], f, process=False)
    outer.export(out / "outer.stl")
    result = {
        "surface": "exact R3 indexed coordinates",
        "surface_vertices": len(v),
        "surface_triangles": len(f),
        "prism_cells": len(cells),
        "layer_count": 8,
        "min_normal_projection": float(projections.min()),
        "attempts": attempts,
        "nonpositive_prism_jacobian_minima": len(bad),
        "jacobian_method": "analytic minimum over reference wedge; float64, not interval arithmetic",
        "nominal_first_m": 0.0005,
        "achieved_first_min_m": float(scale.min() * 0.0005),
        "achieved_first_median_m": float(np.median(scale) * 0.0005),
        "achieved_stack_median_m": float(np.median(scale) * heights[-1]),
        "seconds": time.monotonic() - start,
        "gpu_compute": False,
        "solver_run": False,
        "status": "PRISM_JACOBIAN_PASS_ONLY" if not len(bad) else "FIX_FIRST",
    }
    (ROOT / "evidence/constrained-exact-02.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))
    require_positive_jacobians(jac)


if __name__ == "__main__":
    main()

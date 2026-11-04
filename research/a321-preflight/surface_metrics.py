#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# ─── How to run ───
# Imported from Blender or tested with: uv run --with pytest -m pytest test_surface_metrics.py
# Original CPU geometry measurements. No GPL source consulted or copied.
"""Measure indexed triangle topology without mutating coordinates."""

from __future__ import annotations

from typing import TypedDict

import numpy as np
from numpy.typing import NDArray


class SurfaceMetrics(TypedDict):
    topology_scope: str
    vertex_manifoldness: str
    vertices: int
    triangles: int
    boundary_edges: int
    nonmanifold_edges: int
    inconsistent_edges: int
    degenerate_triangles: int
    duplicate_triangles: int
    area_m2: float
    signed_volume_m3: float
    bounds_m: list[list[float]]
    closed_oriented: bool


def measure(vertices: NDArray[np.float64], faces: NDArray[np.int64]) -> SurfaceMetrics:
    """Return exact-index incidence, orientation and geometric integrals."""
    if not np.isfinite(vertices).all():
        raise RuntimeError("NONFINITE_VERTEX")
    triangles = vertices[faces]
    cross = np.cross(
        triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    )
    twice_area = np.linalg.norm(cross, axis=1)
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    ordered = np.sort(edges, axis=1)
    _, inverse, counts = np.unique(
        ordered, axis=0, return_inverse=True, return_counts=True
    )
    direction = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    balance = np.bincount(inverse, weights=direction)
    boundary = int(np.count_nonzero(counts == 1))
    nonmanifold = int(np.count_nonzero(counts > 2))
    inconsistent = int(np.count_nonzero((counts == 2) & (balance != 0)))
    degenerate = int(np.count_nonzero(twice_area <= 1e-12))
    duplicates = len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0))
    volume = (
        np.einsum(
            "ij,ij->i", triangles[:, 0], np.cross(triangles[:, 1], triangles[:, 2])
        ).sum()
        / 6
    )
    return {
        "topology_scope": "edge-incidence-only; closed_oriented is not a full manifold proof",
        "vertex_manifoldness": "UNMEASURED",
        "vertices": len(vertices),
        "triangles": len(faces),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "inconsistent_edges": inconsistent,
        "degenerate_triangles": degenerate,
        "duplicate_triangles": duplicates,
        "area_m2": float(twice_area.sum() / 2),
        "signed_volume_m3": float(volume),
        "bounds_m": [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
        "closed_oriented": boundary
        == nonmanifold
        == inconsistent
        == degenerate
        == duplicates
        == 0,
    }

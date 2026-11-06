#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh"]
# ///
# How to run: imported by audit_poly.py; test_wall_surface.py verifies split-edge preservation.
"""Triangulate general boundary polygons for visualization and proximity checks."""

from __future__ import annotations

import numpy as np
import trimesh
from numpy.typing import NDArray
from polygon_triangles import triangulate


def triangulate_wall(
    vertices: NDArray[np.float64], faces: NDArray[np.int64]
) -> trimesh.Trimesh:
    """Preserve every polygon boundary edge in a nondegenerate triangle fan."""
    count = (faces >= 0).sum(axis=1)
    centers = (vertices[np.maximum(faces, 0)] * (faces >= 0)[:, :, None]).sum(
        axis=1
    ) / count[:, None]
    extended = np.vstack((vertices, centers))
    triangles = []
    for i, row in enumerate(faces):
        row = row[row >= 0]
        points = vertices[row]
        cross = np.cross(points - centers[i], np.roll(points, -1, axis=0) - centers[i])
        normal = cross.sum(axis=0)
        scale = max(float(np.ptp(points, axis=0).max()), 1e-12)
        nonplanar = (
            np.max(np.abs((points - centers[i]) @ normal)) / np.linalg.norm(normal)
            > 1e-10 * scale
        )
        # A warped native face is the stated 3-D center fan; its planar projection may cross itself.
        if nonplanar or np.all(cross @ normal > 1e-14 * np.dot(normal, normal)):
            triangles.extend(
                [len(vertices) + i, int(row[j]), int(row[(j + 1) % len(row)])]
                for j in range(len(row))
            )
        else:
            triangles.extend(row[triangulate(points)].tolist())
    return trimesh.Trimesh(extended, np.array(triangles), process=False)


def raw_wall_closed(faces: NDArray[np.int64]) -> bool:
    """Check exact serialized IDs and signed edge incidence, without coordinate welding."""
    sizes = (faces >= 0).sum(axis=1)
    edges = []
    for j in range(faces.shape[1]):
        active = j < sizes
        edges.append(
            np.column_stack(
                (
                    faces[active, j],
                    faces[np.flatnonzero(active), (j + 1) % sizes[active]],
                )
            )
        )
    edge = np.vstack(edges)
    _, inverse, count = np.unique(
        np.sort(edge, axis=1), axis=0, return_inverse=True, return_counts=True
    )
    signs = np.where(edge[:, 0] < edge[:, 1], 1, -1)
    return bool(np.all(count == 2) and np.all(np.bincount(inverse, weights=signs) == 0))

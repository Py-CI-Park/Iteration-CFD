#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: imported by audit_poly.py; uv run --with numpy --with pytest -m pytest test_poly_geometry.py.
"""General polygon face moments and volume-weighted cell centroids from signed incidence."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

type Floats = NDArray[np.float64]
type Indices = NDArray[np.int64]


def face_geometry(vertices: Floats, faces: Indices) -> tuple[Floats, Floats]:
    """Integrate fan triangles around the vertex average for arbitrary padded polygons."""
    count = (faces >= 0).sum(axis=1)
    p = vertices[np.maximum(faces, 0)]
    center = (p * (faces >= 0)[:, :, None]).sum(axis=1) / count[:, None]
    sf = np.zeros_like(center)
    crosses = []
    centroids = []
    for j in range(faces.shape[1]):
        following = (j + 1) % count
        b = p[np.arange(len(p)), following]
        cross = 0.5 * np.cross(p[:, j] - center, b - center) * (j < count)[:, None]
        sf += cross
        crosses.append(cross)
        centroids.append((center + p[:, j] + b) / 3)
    magnitude = np.linalg.norm(sf, axis=1)
    if np.any(magnitude <= 0):
        raise RuntimeError("ZERO_VECTOR_AREA_FACE")
    normal = sf / magnitude[:, None]
    area = np.zeros(len(faces))
    moment = np.zeros_like(center)
    for cross, centroid in zip(crosses, centroids, strict=True):
        weight = np.einsum("ij,ij->i", cross, normal)
        moment += centroid * weight[:, None]
        area += weight
    if np.any(area <= 0):
        raise RuntimeError("ZERO_AREA_FACE")
    return sf, moment / area[:, None]


def cell_geometry(
    vertices: Floats, faces: Indices, owner: Indices, neighbour: Indices
) -> tuple[Floats, Floats, Floats, Floats, Floats]:
    """Compute centers with signed face-pyramid moments, never vertex means of a skew cell."""
    nf = len(neighbour)
    if (
        len(owner) != len(faces)
        or np.any(owner < 0)
        or np.any(neighbour < 0)
        or max(owner.max(), neighbour.max(initial=0)) >= len(faces)
    ):
        raise RuntimeError("INVALID_CELL_LABEL")
    if faces.max() >= len(vertices) or np.any(faces < -1):
        raise RuntimeError("INVALID_VERTEX_LABEL")
    nc = int(max(owner.max(), neighbour.max(initial=0))) + 1
    sf, cf = face_geometry(vertices, faces)
    initial = np.zeros((nc, 3))
    count = np.zeros(nc)
    np.add.at(initial, owner, cf)
    np.add.at(count, owner, 1)
    np.add.at(initial, neighbour, cf[:nf])
    np.add.at(count, neighbour, 1)
    if np.any(count == 0):
        raise RuntimeError("UNREFERENCED_CELL_LABEL")
    initial /= count[:, None]
    volume = np.zeros(nc)
    moment = np.zeros((nc, 3))
    closure = np.zeros((nc, 3))
    sizes = (faces >= 0).sum(axis=1)
    p = vertices[np.maximum(faces, 0)]
    base = (p * (faces >= 0)[:, :, None]).sum(axis=1) / sizes[:, None]
    np.add.at(closure, owner, sf)
    np.add.at(closure, neighbour, -sf[:nf])
    for j in range(faces.shape[1]):
        b = p[np.arange(len(p)), (j + 1) % sizes]
        area = 0.5 * np.cross(p[:, j] - base, b - base) * (j < sizes)[:, None]
        for ids, tri_area, a, q, r in [
            (owner, area, base, p[:, j], b),
            (neighbour, -area[:nf], base[:nf], p[:nf, j], b[:nf]),
        ]:
            tetra = np.einsum("ij,ij->i", tri_area, a - initial[ids]) / 3
            np.add.at(volume, ids, tetra)
            np.add.at(moment, ids, tetra[:, None] * (initial[ids] + a + q + r) / 4)
    if np.any(~np.isfinite(volume) | (volume <= 0)):
        raise RuntimeError("NONPOSITIVE_CELL_VOLUME")
    return sf, cf, moment / volume[:, None], volume, closure

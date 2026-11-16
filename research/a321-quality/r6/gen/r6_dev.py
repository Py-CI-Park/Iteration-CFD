# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Distance from points to a triangle surface (the R3 component STL): candidate triangles by centroid KD-tree, exact point-triangle distance.

The nearest triangle is searched among the `k` triangles with the closest centroids; for the structured R3 grids
(triangles of similar size) this reproduces the exact nearest distance except in rare long-sliver cases, where the
result is an upper bound of the true distance (it can only over-estimate).
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

FloatArray = NDArray[np.float64]


def point_triangle_distance(p: FloatArray, a: FloatArray, b: FloatArray, c: FloatArray) -> FloatArray:
    """Vectorised closest-point distance (Ericson, Real-Time Collision Detection 5.1.5); all arrays (n, 3)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4
    closest = np.empty_like(p)
    done = np.zeros(len(p), bool)

    def put(mask: NDArray, point: FloatArray) -> None:
        nonlocal done
        sel = mask & ~done
        closest[sel] = point[sel]
        done |= sel

    put((d1 <= 0) & (d2 <= 0), a)
    put((d3 >= 0) & (d4 <= d3), b)
    put((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + ab * (d1 / np.where(d1 - d3 == 0, 1, d1 - d3))[:, None])
    put((d6 >= 0) & (d5 <= d6), c)
    put((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + ac * (d2 / np.where(d2 - d6 == 0, 1, d2 - d6))[:, None])
    put((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), b + (c - b) * ((d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1, (d4 - d3) + (d5 - d6)))[:, None])
    denom = va + vb + vc
    denom = np.where(denom == 0, 1, denom)
    inside = a + ab * (vb / denom)[:, None] + ac * (vc / denom)[:, None]
    put(np.ones(len(p), bool), inside)
    return np.linalg.norm(p - closest, axis=1)


class TriangleSurface:
    """Nearest-distance queries against a triangle soup (n, 3, 3)."""

    def __init__(self, triangles: FloatArray, k: int = 24) -> None:
        self.tri = np.asarray(triangles, dtype=np.float64)
        self.tree = cKDTree(self.tri.mean(axis=1))
        self.k = k

    def distance(self, points: FloatArray, chunk: int = 20000) -> FloatArray:
        out = np.empty(len(points))
        for s in range(0, len(points), chunk):
            p = points[s:s + chunk]
            _, idx = self.tree.query(p, k=self.k)
            best = np.full(len(p), np.inf)
            for j in range(self.k):
                t = self.tri[idx[:, j]]
                best = np.minimum(best, point_triangle_distance(p, t[:, 0], t[:, 1], t[:, 2]))
            out[s:s + chunk] = best
        return out

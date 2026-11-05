#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: imported by reconstruct.py; analytic tests in test_profiles.py.
"""Closed loft geometry from reference-plane convex outer sections, CPU only."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import ConvexHull

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def section_points(
    vertices: FloatArray, faces: IntArray, axis: int, value: float
) -> FloatArray:
    """Return triangle-plane crossing points in the other two coordinates."""
    tri = vertices[faces]
    chosen = tri[
        (tri[:, :, axis].min(axis=1) <= value) & (tri[:, :, axis].max(axis=1) >= value)
    ]
    points = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = chosen[:, i], chosen[:, j]
        mask = ((a[:, axis] <= value) & (b[:, axis] > value)) | (
            (b[:, axis] <= value) & (a[:, axis] > value)
        )
        aa, bb = a[mask], b[mask]
        points.append(
            aa
            + (bb - aa) * ((value - aa[:, axis]) / (bb[:, axis] - aa[:, axis]))[:, None]
        )
    merged = np.concatenate(points)
    return np.unique(np.delete(merged, axis, axis=1), axis=0)


def radial_hull(points: FloatArray, count: int) -> FloatArray:
    """Sample convex section boundary by uniform rays around its vertex mean."""
    hull = ConvexHull(points)
    center = points[hull.vertices].mean(axis=0)
    angles = np.arange(count) * (2 * np.pi / count)
    rays = np.column_stack((np.cos(angles), np.sin(angles)))
    normals, offsets = hull.equations[:, :2], hull.equations[:, 2]
    denominator = rays @ normals.T
    numerator = -(normals @ center + offsets)
    ratios = np.full_like(denominator, np.inf)
    np.divide(numerator[None, :], denominator, out=ratios, where=denominator > 1e-12)
    radius = ratios.min(axis=1)
    return center + rays * radius[:, None]


def chord_hull(points: FloatArray, count: int) -> FloatArray:
    """Cosine chord sampling of a convex airfoil envelope, retaining exact x extrema."""
    hull = points[ConvexHull(points).vertices]
    lo, hi = float(hull[:, 0].min()), float(hull[:, 0].max())
    n = count // 2
    xs = lo + (hi - lo) * (1 - np.cos(np.linspace(0, np.pi, n + 1))) / 2
    lower, upper = [], []
    for x in xs:
        intersections = []
        for a, b in zip(hull, np.roll(hull, -1, axis=0)):
            if min(a[0], b[0]) - 1e-10 <= x <= max(a[0], b[0]) + 1e-10:
                if abs(b[0] - a[0]) > 1e-12:
                    t = np.clip((x - a[0]) / (b[0] - a[0]), 0, 1)
                    intersections.append(float(a[1] + t * (b[1] - a[1])))
                else:
                    intersections.extend([float(a[1]), float(b[1])])
        lower.append(min(intersections))
        upper.append(max(intersections))
    return np.concatenate(
        (np.column_stack((xs, upper)), np.column_stack((xs[-2:0:-1], lower[-2:0:-1])))
    )


def loft(
    stations: FloatArray, rings: FloatArray, axis: int
) -> tuple[FloatArray, IntArray]:
    """Triangulate successive consistently sampled convex rings and planar end caps."""
    n, k, _ = rings.shape
    vertices = np.zeros((n * k + 2, 3), dtype=np.float64)
    other = [i for i in range(3) if i != axis]
    vertices[: n * k, axis] = np.repeat(stations, k)
    vertices[: n * k, other[0]] = rings[:, :, 0].ravel()
    vertices[: n * k, other[1]] = rings[:, :, 1].ravel()
    vertices[-2] = vertices[:k].mean(axis=0)
    vertices[-1] = vertices[(n - 1) * k : n * k].mean(axis=0)
    faces = []
    for s in range(n - 1):
        for j in range(k):
            a, b, c, d = (
                s * k + j,
                s * k + (j + 1) % k,
                (s + 1) * k + (j + 1) % k,
                (s + 1) * k + j,
            )
            faces.extend(((a, b, c), (a, c, d)))
    for j in range(k):
        faces.extend(
            (
                (n * k, (j + 1) % k, j),
                (n * k + 1, (n - 1) * k + j, (n - 1) * k + (j + 1) % k),
            )
        )
    triangles = np.array(faces, dtype=np.int64)
    tri = vertices[triangles]
    volume = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    if volume < 0:
        triangles = triangles[:, ::-1].copy()
    return vertices, triangles

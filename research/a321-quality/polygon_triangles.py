#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: imported by wall_surface.py; deterministic projected ear clipping for simple polygons.
"""Preserve all boundary vertices while triangulating a non-star-shaped face."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def triangulate(points: NDArray[np.float64]) -> NDArray[np.int64]:
    """Clip convex ears with an inclusive point test so collinear boundary vertices survive."""
    edges = np.roll(points, -1, axis=0) - points
    normal = np.cross(points - points[0], np.roll(points, -1, axis=0) - points[0]).sum(
        axis=0
    )
    normal /= np.linalg.norm(normal)
    u = edges[np.argmax(np.linalg.norm(edges, axis=1))]
    u = u / np.linalg.norm(u)
    v = np.cross(normal, u)
    p = np.column_stack(((points - points[0]) @ u, (points - points[0]) @ v))
    eps = 1e-13 * max(float(np.ptp(p, axis=0).max()) ** 2, 1e-12)
    remaining = list(range(len(p)))
    output = []

    def cross(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
        return float(a[0] * b[1] - a[1] * b[0])

    while len(remaining) > 3:
        clipped = False
        for j, current in enumerate(remaining):
            a, b, c = remaining[j - 1], current, remaining[(j + 1) % len(remaining)]
            if cross(p[b] - p[a], p[c] - p[b]) <= eps:
                continue
            blocked = False
            for q in remaining:
                if q in (a, b, c):
                    continue
                if (
                    min(
                        cross(p[b] - p[a], p[q] - p[a]),
                        cross(p[c] - p[b], p[q] - p[b]),
                        cross(p[a] - p[c], p[q] - p[c]),
                    )
                    >= -eps
                ):
                    blocked = True
                    break
            if not blocked:
                output.append([a, b, c])
                remaining.pop(j)
                clipped = True
                break
        if not clipped:
            raise RuntimeError("NON_SIMPLE_OR_DEGENERATE_POLYGON")
    if (
        cross(p[remaining[1]] - p[remaining[0]], p[remaining[2]] - p[remaining[1]])
        <= eps
    ):
        raise RuntimeError("DEGENERATE_LAST_EAR")
    output.append(remaining)
    return np.array(output, dtype=np.int64)

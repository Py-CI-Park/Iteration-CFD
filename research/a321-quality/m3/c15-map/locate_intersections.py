#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree"]
# ///
# How to run: install uv, then uv run locate_intersections.py --help
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from rtree import index
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

FloatArray = NDArray[np.float64]
EPS = 1e-12  # metres; fixed before the first independent scan, never fitted to 15.


class DiagnosticError(RuntimeError):
    """A malformed input or failed custody/evidence contract."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)


def plane_cut(triangle: FloatArray, distances: FloatArray) -> FloatArray:
    """Intersect the three edges with a plane using signed metric distances."""
    points = [triangle[i] for i in range(3) if abs(distances[i]) <= EPS]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        if distances[i] * distances[j] < 0:
            points.append(triangle[i] + distances[i] / (distances[i] - distances[j]) * (triangle[j] - triangle[i]))
    return np.array(points, dtype=np.float64).reshape(-1, 3)


def coplanar_cut(a: FloatArray, b: FloatArray, normal: FloatArray) -> FloatArray:
    """Clip a convex triangle polygon in its best-conditioned 2D projection."""
    axes = np.delete(np.arange(3), np.argmax(np.abs(normal)))
    polygon = list(a)
    projected = b[:, axes]
    edge1, edge2 = projected[1] - projected[0], projected[2] - projected[0]
    orientation = np.sign(edge1[0] * edge2[1] - edge1[1] * edge2[0])
    for i, j in ((0, 1), (1, 2), (2, 0)):
        edge = projected[j] - projected[i]
        result = []
        for k in range(len(polygon)):
            p, q = polygon[k - 1], polygon[k]
            dp, dq = p[axes] - projected[i], q[axes] - projected[i]
            sp = orientation * (edge[0] * dp[1] - edge[1] * dp[0])
            sq = orientation * (edge[0] * dq[1] - edge[1] * dq[0])
            if (sp >= 0) != (sq >= 0):
                result.append(p + sp / (sp - sq) * (q - p))
            if sq >= 0:
                result.append(q)
        polygon = result
    return np.array(polygon, dtype=np.float64).reshape(-1, 3)


def intersection_points(a: FloatArray, b: FloatArray) -> FloatArray:
    """Return intersection geometry, excluding any shared exact vertex."""
    if np.any(np.all(a[:, None, :] == b[None, :, :], axis=2)):
        return np.empty((0, 3))
    na = np.cross(a[1] - a[0], a[2] - a[0])
    nb = np.cross(b[1] - b[0], b[2] - b[0])
    la, lb = np.linalg.norm(na), np.linalg.norm(nb)
    if la == 0 or lb == 0:
        return np.empty((0, 3))
    na, nb = na / la, nb / lb
    da, db = (a - b[0]) @ nb, (b - a[0]) @ na
    if da.min() > EPS or da.max() < -EPS or db.min() > EPS or db.max() < -EPS:
        return np.empty((0, 3))
    direction = np.cross(na, nb)
    length = np.linalg.norm(direction)
    if length <= 32 * np.finfo(float).eps:
        if max(np.abs(da).max(), np.abs(db).max()) <= EPS:
            return coplanar_cut(a, b, na)
        return np.empty((0, 3))
    ca, cb = plane_cut(a, da), plane_cut(b, db)
    if not len(ca) or not len(cb):
        return np.empty((0, 3))
    direction /= length
    # Relative origin avoids cancellation from world coordinates at 10-40 m.
    pa, pb = (ca - ca[0]) @ direction, (cb - ca[0]) @ direction
    low, high = max(pa.min(), pb.min()), min(pa.max(), pb.max())
    if high < low - EPS:
        return np.empty((0, 3))
    return np.array([ca[0] + low * direction, ca[0] + high * direction])


def load_stl(path: Path) -> FloatArray:
    """Parse binary STL in original facet order, without welding/reordering."""
    raw = path.read_bytes()
    count = int.from_bytes(raw[80:84], "little")
    if len(raw) != 84 + count * 50:
        raise DiagnosticError(f"Not a size-consistent binary STL: {path}")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].astype(np.float64)
    if not np.isfinite(triangles).all():
        raise DiagnosticError(f"Non-finite STL coordinates: {path}")
    return triangles


def scan(triangles: FloatArray) -> tuple[list[tuple[int, int]], list[FloatArray], int]:
    """Rtree broad phase over every facet; plane/interval narrow phase."""
    bounds = np.column_stack((triangles.min(axis=1), triangles.max(axis=1)))
    properties = index.Property(dimension=3)
    tree = index.Index(((i, box, None) for i, box in enumerate(bounds)), properties=properties)
    pairs: list[tuple[int, int]] = []
    geometries: list[FloatArray] = []
    tested = 0
    for i, box in enumerate(bounds):
        candidates = np.array([j for j in tree.intersection(box) if j > i], dtype=np.int64)
        if len(candidates):
            others = triangles[candidates]
            shared = np.any(np.all(triangles[i, None, :, None, :] == others[:, None, :, :], axis=-1), axis=(1, 2))
            for j in candidates[~shared]:
                tested += 1
                points = intersection_points(triangles[i], triangles[j])
                if len(points):
                    pairs.append((i, int(j)))
                    geometries.append(points)
        if i % 25000 == 0:
            print(f"facet={i}/{len(triangles)} narrow={tested} hits={len(pairs)}", flush=True)
    return pairs, geometries, tested


def cluster(pairs: list[tuple[int, int]], geometries: list[FloatArray]) -> list[list[int]]:
    """Connected components of intersecting pairs that share an STL facet."""
    if not pairs:
        return []
    links: list[tuple[int, int]] = []
    owner: dict[int, int] = {}
    for i, pair in enumerate(pairs):
        for face in pair:
            if face in owner:
                links.extend(((i, owner[face]), (owner[face], i)))
            owner[face] = i
    rows, cols = zip(*links) if links else ([], [])
    graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(pairs), len(pairs))).tocsr()
    count, labels = connected_components(graph, directed=False)
    return [np.flatnonzero(labels == group).tolist() for group in range(count)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    before = hashlib.sha256(args.input.read_bytes()).hexdigest()
    triangles = load_stl(args.input)
    pairs, geometries, tested = scan(triangles)
    groups = cluster(pairs, geometries)
    after = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if before != after:
        raise DiagnosticError("Input SHA changed")
    result = {
        "input": str(args.input), "sha256_before": before, "sha256_after": after,
        "triangle_count": len(triangles), "indexing": "zero-based original binary STL facet order",
        "method": "3D rtree AABB; plane cuts and line interval overlap; 2D convex clipping for coplanar triangles; exact-coordinate shared vertex exclusion",
        "epsilon_m": EPS, "cluster_method": "connected components through shared intersecting facets; no distance tuning",
        "versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "trimesh", "rtree")},
        "python": platform.python_version(), "float_mantissa_bits": int(np.finfo(float).nmant),
        "narrow_phase_pairs": tested, "pair_count": len(pairs), "cluster_count": len(groups),
        "pairs": [{"triangles": pair, "points_m": points.tolist()} for pair, points in zip(pairs, geometries)],
        "clusters": [{"id": i + 1, "pair_indices": group, "centroid_m": np.concatenate([geometries[j] for j in group]).mean(axis=0).tolist()} for i, group in enumerate(groups)],
        "wall_seconds": time.perf_counter() - started,
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({k: result[k] for k in ("pair_count", "cluster_count", "wall_seconds")}))


if __name__ == "__main__":
    main()

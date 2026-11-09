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
# How to run: uv run inspect_locations.py INPUT_STL POINTS_OBJ OUTPUT_JSON
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import trimesh
from locate_intersections import FloatArray, load_stl

MATCH_RADIUS_M = 1e-4  # OBJ has six significant digits, at most 50 um x-roundoff.


@dataclass(frozen=True, slots=True)
class TriangleMetrics:
    index: int
    vertices_m: list[list[float]]
    edge_lengths_m: list[float]
    equilateral_quality: float
    radius_ratio_quality: float
    area_m2: float
    normal: list[float]
    point_distance_m: float


def metrics(triangle: FloatArray, face: int, point: FloatArray) -> TriangleMetrics:
    edges = np.roll(triangle, -1, axis=0) - triangle
    lengths = np.linalg.norm(edges, axis=1)
    cross = np.cross(edges[0], -edges[2])
    area = float(np.linalg.norm(cross) / 2)
    perimeter = lengths.sum()
    # 4 sqrt(3) A / sum(e^2) and 2r/R = 16 A^2/(p*a*b*c).
    equilateral = float(4 * np.sqrt(3) * area / (lengths @ lengths))
    shape = float(16 * area**2 / (perimeter * lengths.prod()))
    nearest = trimesh.triangles.closest_point(triangle[None], point[None])[0]
    return TriangleMetrics(face, triangle.tolist(), lengths.tolist(), equilateral, shape,
                           area, (cross / (2 * area)).tolist(), float(np.linalg.norm(nearest - point)))


def ray_hits(a: FloatArray, b: FloatArray) -> list[dict[str, float | int | list[float]]]:
    """Segment/plane plus barycentric test; retains shared topology for diagnosis.

    Strict barycentric bounds; no epsilon inflation. Endpoints are retained and
    explicitly tagged by the segment parameter rather than silently discarded.
    """
    normal = np.cross(b[1] - b[0], b[2] - b[0])
    axes = np.delete(np.arange(3), np.argmax(np.abs(normal)))
    u, v = (b[1] - b[0])[axes], (b[2] - b[0])[axes]
    determinant = u[0] * v[1] - u[1] * v[0]
    hits: list[dict[str, float | int | list[float]]] = []
    if determinant == 0:
        return hits
    for i in range(3):
        start, end = a[i], a[(i + 1) % 3]
        d0, d1 = float((start - b[0]) @ normal), float((end - b[0]) @ normal)
        if d0 == d1:
            continue
        fraction = d0 / (d0 - d1)
        if not 0 <= fraction <= 1:
            continue
        point = start + fraction * (end - start)
        w = (point - b[0])[axes]
        s = float((w[0] * v[1] - w[1] * v[0]) / determinant)
        t = float((u[0] * w[1] - u[1] * w[0]) / determinant)
        if min(s, t, 1 - s - t) >= 0:
            hits.append({"edge": i, "fraction": fraction, "point_m": point.tolist(), "barycentric": [1 - s - t, s, t]})
    return hits


def main() -> None:
    started = time.perf_counter()
    input_path, obj_path, output_path = map(Path, sys.argv[1:])
    triangles = load_stl(input_path)
    points = np.array([[float(s) for s in line.split()[1:]] for line in obj_path.read_text().splitlines() if line.startswith("v ")])
    low, high = triangles.min(axis=1), triangles.max(axis=1)
    locations = []
    for number, point in enumerate(points, 1):
        ids = np.flatnonzero(np.all(low <= point + MATCH_RADIUS_M, axis=1) & np.all(high >= point - MATCH_RADIUS_M, axis=1))
        local_metrics = [metrics(triangles[i], int(i), point) for i in ids]
        hits = []
        for pos, i in enumerate(ids):
            for j in ids[pos + 1:]:
                shared = int(np.any(np.all(triangles[i, :, None] == triangles[j, None, :], axis=2), axis=1).sum())
                intersections = ray_hits(triangles[i], triangles[j]) + ray_hits(triangles[j], triangles[i])
                close = [hit for hit in intersections if np.linalg.norm(np.array(hit["point_m"]) - point) <= MATCH_RADIUS_M]
                if close:
                    hits.append({"triangles": [int(i), int(j)], "shared_vertices": shared, "hits": close})
        locations.append({"id": number, "world_m": point.tolist(), "triangles": [asdict(m) for m in local_metrics], "ray_pairs": hits})
        print(f"point={number} local_triangles={len(ids)} ray_pairs={len(hits)}", flush=True)
    result = {"match_radius_m": MATCH_RADIUS_M, "source_obj": str(obj_path), "wall_seconds": time.perf_counter() - started, "locations": locations}
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()

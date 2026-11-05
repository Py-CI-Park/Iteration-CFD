#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "rtree"]
# ///
# How to run: uv run audit_shell.py
"""Independently verify stored shell topology, vertex links, and section measurements."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from profiles import section_points
from surface_metrics import measure


def vertex_links(faces: np.ndarray, count: int) -> list[int]:
    """Require each closed vertex link to be a single cycle, not touching shells."""
    links = defaultdict(list)
    for a, b, c in faces:
        links[int(a)].append((int(b), int(c)))
        links[int(b)].append((int(c), int(a)))
        links[int(c)].append((int(a), int(b)))
    bad = []
    for vertex in range(count):
        adjacency = defaultdict(set)
        for a, b in links[vertex]:
            adjacency[a].add(b)
            adjacency[b].add(a)
        if not adjacency or any(len(n) != 2 for n in adjacency.values()):
            bad.append(vertex)
            continue
        visited = set()
        stack = [next(iter(adjacency))]
        while stack:
            item = stack.pop()
            if item not in visited:
                visited.add(item)
                stack.extend(adjacency[item] - visited)
        if len(visited) != len(adjacency):
            bad.append(vertex)
    return bad


def main() -> None:
    """Measure exact STL-coordinate weld, manifold kernel and reference section deltas."""
    path = ROOT / "artifacts/shell-r2/A321_AIRFRAME_SHELL_R2.stl"
    mesh = trimesh.load_mesh(path, process=True)
    v, f = np.array(mesh.vertices), np.array(mesh.faces)
    metrics = measure(v, f)
    bad = vertex_links(f, len(v))
    solid = mf.Manifold(mf.Mesh(v.astype(np.float32), f.astype(np.uint32)))
    sections = []
    for group, axis, stations in [
        ("fuselage", 0, [2, 5, 10, 20, 30, 40, 43]),
        ("wing", 1, [2, 5, 10, 15]),
        ("horizontal", 1, [1, 3, 5]),
        ("vertical", 2, [6, 8, 10, 11]),
    ]:
        with np.load(ROOT / f"artifacts/reference/{group}.npz") as data:
            rv, rf = data["vertices"], data["faces"]
        part = trimesh.load_mesh(ROOT / f"artifacts/shell-r2/{group}.stl", process=True)
        for station in stations:
            original = section_points(rv, rf, axis, station)
            candidate = section_points(part.vertices, part.faces, axis, station)
            bounds_delta = np.vstack(
                (
                    candidate.min(axis=0) - original.min(axis=0),
                    candidate.max(axis=0) - original.max(axis=0),
                )
            )
            sections.append(
                {
                    "part": group,
                    "station_m": station,
                    "axis": axis,
                    "bounds_max_delta_m": float(np.max(np.abs(bounds_delta))),
                    "reference_hull_area_m2": float(ConvexHull(original).volume),
                    "shell_hull_area_m2": float(ConvexHull(candidate).volume),
                }
            )
    rec = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "surface": metrics,
        "vertex_link_failures": len(bad),
        "kernel_status": str(solid.status()),
        "kernel_components": len(solid.decompose()),
        "euler_number": int(mesh.euler_number),
        "is_volume": bool(mesh.is_volume),
        "sections": sections,
        "max_section_bounds_delta_m": max(s["bounds_max_delta_m"] for s in sections),
        "self_intersections": "kernel Boolean construction validity; independent exhaustive triangle-pair proof NOT_RUN",
        "engineering_status": "NOT_VALIDATED",
        "gpu_compute": False,
    }
    (ROOT / "evidence/shell-audit-r2.json").write_text(
        json.dumps(rec, indent=2), encoding="utf8"
    )
    print(json.dumps({k: v for k, v in rec.items() if k != "sections"}))


if __name__ == "__main__":
    main()

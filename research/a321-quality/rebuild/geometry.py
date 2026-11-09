#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Independent deterministic loft triangulation and CPU topology measurements."""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import trimesh
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Topology:
    closed: bool
    winding: bool
    positive_volume: bool
    components: int
    degenerate_faces: int
    duplicate_faces: int
    vertex_link_failures: int


def loft(
    stations: NDArray[np.float64], rings: NDArray[np.float64], axis: int
) -> trimesh.Trimesh:
    """Construct capped ring lofts; paired triangles retain feature vertices."""
    n, k, _ = rings.shape
    v = np.zeros((n * k + 2, 3))
    other = [i for i in range(3) if i != axis]
    v[: n * k, axis] = np.repeat(stations, k)
    v[: n * k, other[0]] = rings[:, :, 0].ravel()
    v[: n * k, other[1]] = rings[:, :, 1].ravel()
    v[-2] = v[:k].mean(axis=0)
    v[-1] = v[(n - 1) * k : n * k].mean(axis=0)
    f = []
    for i in range(n - 1):
        for j in range(k):
            a, b = i * k + j, i * k + (j + 1) % k
            c, d = (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            f.extend(((a, b, c), (a, c, d)))
    for j in range(k):
        f.extend(
            (
                (n * k, (j + 1) % k, j),
                (n * k + 1, (n - 1) * k + j, (n - 1) * k + (j + 1) % k),
            )
        )
    mesh = trimesh.Trimesh(v, np.array(f), process=False)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


def topology(mesh: trimesh.Trimesh) -> Topology:
    """Check cyclic vertex links independently of volume-kernel status."""
    links: list[list[tuple[int, int]]] = [[] for _ in mesh.vertices]
    for a, b, c in mesh.faces:
        links[a].append((int(b), int(c)))
        links[b].append((int(c), int(a)))
        links[c].append((int(a), int(b)))
    failures = 0
    for edges in links:
        adj: dict[int, list[int]] = {}
        for a, b in edges:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        if not adj or any(len(v) != 2 for v in adj.values()):
            failures += 1
            continue
        remaining = set(adj)
        stack = [next(iter(remaining))]
        while stack:
            node = stack.pop()
            if node in remaining:
                remaining.remove(node)
                stack.extend(adj[node])
        failures += bool(remaining)
    sorted_faces = np.sort(mesh.faces, axis=1)
    duplicates = len(sorted_faces) - len(np.unique(sorted_faces, axis=0))
    return Topology(
        bool(mesh.is_watertight),
        bool(mesh.is_winding_consistent),
        bool(mesh.volume > 0),
        len(mesh.split(only_watertight=False)),
        int(np.count_nonzero(mesh.area_faces <= 1e-16)),
        duplicates,
        failures,
    )

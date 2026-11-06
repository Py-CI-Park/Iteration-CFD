#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh"]
# ///
# How to run: uv run convert_oriented.py; saved hybrid only, no CFD solve.
"""Topology-oriented hybrid conversion; keep signed face incidence instead of per-face centroid flips."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from build_layers import jacobian_minimum, require_positive_jacobians
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from topology_guards import require_opposite_winding, require_same_triangles

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "tools/mesh"))
from polymesh_write import read_polymesh, write_polymesh


def geometry(v: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute vector area and area-weighted fan center for padded tri/quad rows."""
    counts = (faces >= 0).sum(axis=1)
    p = v[np.maximum(faces, 0)]
    center = (p * (faces >= 0)[:, :, None]).sum(axis=1) / counts[:, None]
    sf = np.zeros_like(center)
    moment = np.zeros_like(center)
    area = np.zeros(len(faces))
    for i in range(4):
        active = i < counts
        a = p[:, i] - center
        nxt = (i + 1) % counts
        b = p[np.arange(len(p)), nxt] - center
        cross = np.cross(a, b) * 0.5 * active[:, None]
        weight = np.linalg.norm(cross, axis=1)
        sf += cross
        moment += (center + p[:, i] + p[np.arange(len(p)), nxt]) / 3 * weight[:, None]
        area += weight
    return sf, moment / area[:, None]


def main() -> None:
    """Read hybrid cells, orient/group faces, write five polyMesh files then re-read."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    quality = args.quality
    root = ROOT / (
        "artifacts/quality-exterior-03" if quality else "artifacts/constrained-exact-02"
    )
    with np.load(root / "hybrid.npz") as d:
        v, tets, prisms = d["vertices"], d["tets"], d["prisms"]
        wall = d["wall_faces"]
        level_count = len(d["heights"])
        wall_count = int(wall.max() + 1)
    require_positive_jacobians(jacobian_minimum(v, prisms))
    p = v[tets]
    negative = (
        np.einsum(
            "ij,ij->i",
            np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]),
            p[:, 3] - p[:, 0],
        )
        < 0
    )
    tets[negative] = tets[negative][:, [0, 2, 1, 3]]
    centers = np.vstack((v[tets].mean(axis=1), v[prisms].mean(axis=1)))
    chunks = []
    own = []
    for pattern in ([0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]):
        chunks.append(np.column_stack((tets[:, pattern], np.full(len(tets), -1))))
        own.append(np.arange(len(tets)))
    for pattern in ([0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]):
        face = prisms[:, pattern]
        if len(pattern) == 3:
            face = np.column_stack((face, np.full(len(face), -1)))
        chunks.append(face)
        own.append(np.arange(len(prisms)) + len(tets))
    faces = np.concatenate(chunks)
    owners = np.concatenate(own)
    _, idx, inv, cnt = np.unique(
        np.sort(faces, axis=1),
        axis=0,
        return_index=True,
        return_inverse=True,
        return_counts=True,
    )
    if np.any(cnt > 2):
        raise RuntimeError("MULTIPLE_CELL_FACE_OWNERS")
    order = np.argsort(inv, kind="stable")
    offset = np.r_[0, np.cumsum(cnt)]
    internal = np.flatnonzero(cnt == 2)
    boundary = np.flatnonzero(cnt == 1)
    first = order[offset[internal]]
    second = order[offset[internal] + 1]
    require_opposite_winding(faces[first], faces[second])
    oo, nn = owners[first], owners[second]
    interface = ((oo < len(tets)) & (nn >= len(tets))) | (
        (nn < len(tets)) & (oo >= len(tets))
    )
    require_same_triangles(
        faces[first[interface], :3], wall + (level_count - 1) * wall_count
    )
    first = np.where(oo < nn, first, second)
    o = np.minimum(oo, nn)
    n = np.maximum(oo, nn)
    sorting = np.lexsort((n, o))
    first, o, n = first[sorting], o[sorting], n[sorting]
    bf = idx[boundary]
    patch = np.full(len(bf), 6, dtype=int)
    points = v[np.maximum(faces[bf], 0)]
    for i, (axis, value) in enumerate(
        [(0, -45), (0, 135), (1, -65), (1, 65), (2, -45), (2, 55)]
    ):
        patch[
            np.all(
                (np.abs(points[:, :, axis] - value) < 1e-7) | (faces[bf] < 0), axis=1
            )
        ] = i
    sort = np.argsort(patch, kind="stable")
    bf, patch = bf[sort], patch[sort]
    require_same_triangles(faces[bf[patch == 6], :3], wall)
    if args.verify_only:
        print(
            json.dumps(
                {
                    "candidate": str(root),
                    "positive_finite_jacobians": True,
                    "opposite_internal_winding": True,
                    "interface_membership_exact": True,
                    "wall_membership_exact": True,
                    "quality": "FIX_FIRST",
                    "solver_run": False,
                }
            )
        )
        return
    chosen = np.r_[first, bf]
    outfaces = faces[chosen]
    owner = np.r_[o, owners[bf]]
    names = ["inlet", "outlet", "yMin", "yMax", "zMin", "zMax", "wall_aircraft"]
    patches = [
        (name, "wall" if i == 6 else "patch", int(np.count_nonzero(patch == i)))
        for i, name in enumerate(names)
    ]
    path = root / "case/constant/polyMesh"
    if path.exists():
        raise RuntimeError("POLYMESH_ALREADY_EXISTS")
    print("WRITE_POLYMESH", len(centers), len(outfaces), flush=True)
    info = write_polymesh(
        str(path), v, [row[row >= 0].tolist() for row in outfaces], owner, n, patches
    )
    info = {key: int(value) for key, value in info.items()}
    pm = read_polymesh(str(path))
    exact = (
        np.array_equal(pm["points"], v)
        and np.array_equal(pm["owner"], owner)
        and np.array_equal(pm["neighbour"], n)
        and pm["faces"] == [row[row >= 0].tolist() for row in outfaces]
        and [(p["name"], p["type"], p["nFaces"]) for p in pm["patches"]] == patches
    )
    if not exact:
        raise RuntimeError("POLYMESH_READBACK_FAILED")
    sf, cf = geometry(v, outfaces)
    volume = np.zeros(len(centers))
    closure = np.zeros_like(centers)
    np.add.at(volume, owner, np.einsum("ij,ij->i", sf, cf - centers[owner]) / 3)
    np.add.at(closure, owner, sf)
    np.add.at(
        volume, n, -np.einsum("ij,ij->i", sf[: len(n)], cf[: len(n)] - centers[n]) / 3
    )
    np.add.at(closure, n, -sf[: len(n)])
    delta = centers[n] - centers[o]
    cos = np.einsum("ij,ij->i", sf[: len(n)], delta) / (
        np.linalg.norm(sf[: len(n)], axis=1) * np.linalg.norm(delta, axis=1)
    )
    angle = np.degrees(np.arccos(np.clip(cos, -1, 1)))
    closure_error = np.linalg.norm(closure, axis=1) / np.maximum(
        np.abs(volume), 1e-100
    ) ** (2 / 3)
    graph = coo_matrix((np.ones(len(n)), (o, n)), shape=(len(centers), len(centers)))
    components, _ = connected_components(graph, directed=False)
    record = {
        **info,
        "orientation": "cell topology; tetrahedra made positive before face generation",
        "prisms": len(prisms),
        "tets": len(tets),
        "readback_exact": exact,
        "patches": patches,
        "min_volume_m3": float(volume.min()),
        "nonpositive_cells": int(np.count_nonzero(volume <= 0)),
        "max_nonorth_deg": float(angle.max()),
        "faces_nonorth_gt70": int(np.count_nonzero(angle > 70)),
        "max_relative_closure": float(closure_error.max()),
        "fluid_components": components,
        "total_volume_m3": float(volume.sum()),
        "status": "PASS_SCOPED_CPU_GATE"
        if np.all(volume > 0)
        and angle.max() <= 70
        and closure_error.max() <= 1e-10
        and components == 1
        else "FIX_FIRST",
        "ofgpu_gate": "NOT_RUN",
        "solver_executed": False,
        "gpu_compute": False,
    }
    np.savez_compressed(
        root / "face-data.npz",
        sf=sf,
        cf=cf,
        owner=owner,
        neighbour=n,
        volume=volume,
        centers=centers,
        nonorth=angle,
    )
    name = "polyMesh-quality-exterior.json" if quality else "polyMesh-quality.json"
    (ROOT / "evidence" / name).write_text(json.dumps(record, indent=2), encoding="utf8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()

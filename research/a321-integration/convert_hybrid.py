#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run convert_hybrid.py; fixed study output only.
"""Convert saved hybrid cells to polyMesh and measure face-based quality independently."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "tools/mesh"))
from polymesh_write import read_polymesh, write_polymesh


def main() -> None:
    """Orient each face out of owner, sort patches, save and independently re-read."""
    folder = ROOT / "artifacts/hybrid-r4"
    convert(folder, "polyMesh-quality.json")


def convert(folder: Path, receipt: str) -> None:
    """Convert one explicit saved mesh directory and name its quality receipt."""
    with np.load(folder / "hybrid.npz") as data:
        v, tets, prisms = data["vertices"], data["tets"], data["prisms"]
    cells = [*list(tets), *list(prisms)]
    centers = np.array([v[c].mean(axis=0) for c in cells])
    all_faces = []
    all_owners = []
    for cell_id, cell in enumerate(cells):
        if len(cell) == 4:
            local = [cell[[0, 2, 1]], cell[[0, 1, 3]], cell[[1, 2, 3]], cell[[2, 0, 3]]]
        else:
            local = [
                cell[[0, 2, 1]],
                cell[[3, 4, 5]],
                cell[[0, 1, 4, 3]],
                cell[[1, 2, 5, 4]],
                cell[[2, 0, 3, 5]],
            ]
        for face in local:
            points = v[face]
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            if np.dot(normal, points.mean(axis=0) - centers[cell_id]) < 0:
                face = face[::-1]
            padded = np.full(4, -1, dtype=np.int64)
            padded[: len(face)] = face
            all_faces.append(padded)
            all_owners.append(cell_id)
    faces = np.array(all_faces)
    owners = np.array(all_owners)
    _, idx, inv, count = np.unique(
        np.sort(faces, axis=1),
        axis=0,
        return_index=True,
        return_inverse=True,
        return_counts=True,
    )
    if np.any(count > 2):
        raise RuntimeError("NONMANIFOLD_CELL_INTERFACE")
    order = np.argsort(inv, kind="stable")
    offsets = np.r_[0, np.cumsum(count)]
    internal = np.flatnonzero(count == 2)
    boundary = np.flatnonzero(count == 1)
    first = order[offsets[internal]]
    second = order[offsets[internal] + 1]
    o = owners[first]
    n = owners[second]
    swap = o > n
    first = np.where(swap, second, first)
    o, n = np.minimum(o, n), np.maximum(o, n)
    sort = np.lexsort((n, o))
    first, o, n = first[sort], o[sort], n[sort]
    bf = idx[boundary]
    patch = np.full(len(bf), 6, dtype=int)
    for i, (axis, val) in enumerate(
        [(0, -45), (0, 135), (1, -65), (1, 65), (2, -45), (2, 55)]
    ):
        chosen = faces[bf]
        points = v[np.maximum(chosen, 0)]
        mask = np.all((np.abs(points[:, :, axis] - val) < 1e-7) | (chosen < 0), axis=1)
        patch[mask] = i
    bs = np.argsort(patch, kind="stable")
    bf = bf[bs]
    patch = patch[bs]
    chosen = np.r_[first, bf]
    face_list = [row[row >= 0].tolist() for row in faces[chosen]]
    owner = np.r_[o, owners[bf]]
    names = ["inlet", "outlet", "yMin", "yMax", "zMin", "zMax", "wall_aircraft"]
    patches = [
        (name, "wall" if i == 6 else "patch", int(np.count_nonzero(patch == i)))
        for i, name in enumerate(names)
    ]
    case = folder / "case/constant/polyMesh"
    if case.exists():
        raise RuntimeError("POLYMESH_ALREADY_EXISTS")
    info = write_polymesh(str(case), v, face_list, owner, n, patches)
    pm = read_polymesh(str(case))
    if not np.array_equal(pm["points"], v) or not np.array_equal(pm["owner"], owner):
        raise RuntimeError("POLYMESH_READBACK_MISMATCH")
    # vectorized fan area/volume: same oriented face convention as repository mesh geometry.
    sf = []
    cf = []
    for face in face_list:
        p = v[face]
        center = p.mean(axis=0)
        s = np.zeros(3)
        for j in range(len(face)):
            s += np.cross(p[j] - center, p[(j + 1) % len(face)] - center) / 2
        sf.append(s)
        cf.append(center)
    sf, cf = np.array(sf), np.array(cf)
    volume = np.zeros(len(cells))
    closure = np.zeros((len(cells), 3))
    np.add.at(volume, owner, np.einsum("ij,ij->i", sf, cf - centers[owner]) / 3)
    np.add.at(closure, owner, sf)
    np.add.at(
        volume, n, -np.einsum("ij,ij->i", sf[: len(n)], cf[: len(n)] - centers[n]) / 3
    )
    np.add.at(closure, n, -sf[: len(n)])
    direction = centers[n] - centers[o]
    cosine = np.einsum("ij,ij->i", sf[: len(n)], direction) / (
        np.linalg.norm(sf[: len(n)], axis=1) * np.linalg.norm(direction, axis=1)
    )
    theta = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
    relative_closure = np.linalg.norm(closure, axis=1) / np.maximum(
        np.abs(volume), 1e-100
    ) ** (2 / 3)
    graph = coo_matrix((np.ones(len(n)), (o, n)), shape=(len(cells), len(cells)))
    components, _ = connected_components(graph, directed=False)
    report = {
        "polyMesh": str(case),
        "readback_exact": True,
        **info,
        "prisms": len(prisms),
        "tets": len(tets),
        "min_volume_m3": float(volume.min()),
        "nonpositive_cells": int(np.count_nonzero(volume <= 0)),
        "max_nonorth_deg": float(theta.max()),
        "faces_nonorth_gt70": int(np.count_nonzero(theta > 70)),
        "max_relative_closure": float(relative_closure.max()),
        "fluid_components": components,
        "total_volume_m3": float(volume.sum()),
        "patches": patches,
        "solver_gate": "NOT_RUN",
        "gpu_solver": False,
        "status": "PASS_SCOPED_CPU_GATE"
        if np.all(volume > 0)
        and theta.max() <= 70
        and relative_closure.max() <= 1e-10
        and components == 1
        else "FIX_FIRST",
    }
    (ROOT / "evidence" / receipt).write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()

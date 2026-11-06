#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run audit_readback_contract.py; independent saved connectivity/boundary acceptance.
"""Compare serialized faces/owners to exact saved hybrid topology and patch ranges."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-integration"))
from audit_polymesh import read_rows


def main() -> None:
    """Require every cell face and boundary assignment to match the saved hybrid input."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", action="store_true")
    quality = parser.parse_args().quality
    root = ROOT / (
        "artifacts/quality-exterior-03" if quality else "artifacts/constrained-exact-02"
    )
    pm = root / "case/constant/polyMesh"
    faces = read_rows(pm / "faces", 4)
    o = read_rows(pm / "owner", 1).ravel()
    n = read_rows(pm / "neighbour", 1).ravel()
    points = read_rows(pm / "points", 3, True)
    with np.load(root / "hybrid.npz") as d:
        tets, prisms = d["tets"], d["prisms"]
    chunks = []
    owners = []
    for pattern in ([0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]):
        chunks.append(np.column_stack((tets[:, pattern], np.full(len(tets), -1))))
        owners.append(np.arange(len(tets)))
    for pattern in ([0, 2, 1], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]):
        row = prisms[:, pattern]
        if len(pattern) == 3:
            row = np.column_stack((row, np.full(len(row), -1)))
        chunks.append(row)
        owners.append(np.arange(len(prisms)) + len(tets))
    expected = np.concatenate(chunks)
    eo = np.concatenate(owners)
    # A face-cell incidence pair is invariant to winding and serialized internal ordering.
    expected = np.column_stack((np.sort(expected, axis=1), eo))
    actual = np.vstack(
        (
            np.column_stack((np.sort(faces, axis=1), o)),
            np.column_stack((np.sort(faces[: len(n)], axis=1), n)),
        )
    )
    a = np.lexsort(actual[:, ::-1].T)
    e = np.lexsort(expected[:, ::-1].T)
    if not np.array_equal(actual[a], expected[e]):
        raise RuntimeError("FACE_CELL_INCIDENCE_MISMATCH")
    text = (pm / "boundary").read_text()
    entries = re.findall(
        r"\n\s*(\w+)\s*\{\s*type\s+(\w+);\s*nFaces\s+(\d+);\s*startFace\s+(\d+);", text
    )
    names = ["inlet", "outlet", "yMin", "yMax", "zMin", "zMax", "wall_aircraft"]
    expected_counts = [128] * 6 + [129522]
    with np.load(root / "hybrid.npz") as data:
        wall_keys = np.sort(data["wall_faces"], axis=1)
    start = len(n)
    rows = []
    for i, (name, kind, count, begin) in enumerate(entries):
        count, begin = int(count), int(begin)
        if count != expected_counts[i]:
            raise RuntimeError("BOUNDARY_COUNT_MISMATCH")
        if (
            name != names[i]
            or kind != ("wall" if i == 6 else "patch")
            or begin != start
        ):
            raise RuntimeError("BOUNDARY_METADATA_MISMATCH")
        chosen = faces[begin : begin + count]
        xyz = points[np.maximum(chosen, 0)]
        if i < 6:
            axis, value = [(0, -45), (0, 135), (1, -65), (1, 65), (2, -45), (2, 55)][i]
            if not np.all((np.abs(xyz[:, :, axis] - value) < 1e-7) | (chosen < 0)):
                raise RuntimeError("BOUNDARY_PLANE_MISMATCH")
        else:
            actual_wall = np.sort(chosen[:, :3], axis=1)
            aa = np.lexsort(actual_wall[:, ::-1].T)
            ww = np.lexsort(wall_keys[:, ::-1].T)
            if not np.array_equal(actual_wall[aa], wall_keys[ww]):
                raise RuntimeError("AIRCRAFT_WALL_MEMBERSHIP_MISMATCH")
        rows.append({"name": name, "type": kind, "count": count, "start": begin})
        start += count
    if len(rows) != 7 or start != len(faces):
        raise RuntimeError("BOUNDARY_COVERAGE_MISMATCH")
    result = {
        "candidate": str(root),
        "all_face_cell_incidence_exact": True,
        "boundary_names_types_ranges_checked": True,
        "boundary_contiguous_complete": True,
        "outer_patch_coordinate_planes_checked": True,
        "aircraft_wall_face_membership_exact": True,
        "expected_patch_counts_checked": True,
        "patches": rows,
        "mesh_quality_status": "FIX_FIRST",
        "solver_run": False,
    }
    name = (
        "polyMesh-readback-quality.json"
        if quality
        else "polyMesh-readback-contract.json"
    )
    (ROOT / "evidence" / name).write_text(json.dumps(result, indent=2), encoding="utf8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

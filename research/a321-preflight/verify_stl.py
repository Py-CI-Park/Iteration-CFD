#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# ─── How to run ───
# uv run verify_stl.py INPUT.stl OUTPUT.json
# Original independent binary-STL reader; CPU-only. No Blender import required.
"""Independently read STL bytes and measure topology and connected components."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
from custody import output_file
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from surface_metrics import measure


def main() -> None:
    """Read packed STL, weld exact stored coordinates, and report gates."""
    source, destination = Path(sys.argv[1]), Path(sys.argv[2])
    destination = output_file(destination)
    raw = source.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise RuntimeError("STL_LENGTH_MISMATCH")
    dtype = np.dtype(
        [("normal", "<f4", (3,)), ("points", "<f4", (3, 3)), ("attr", "<u2")]
    )
    records = np.frombuffer(raw, dtype=dtype, offset=84, count=count)
    vertices, inverse = np.unique(
        records["points"].reshape(-1, 3), axis=0, return_inverse=True
    )
    faces = inverse.reshape(-1, 3)
    metrics = measure(vertices.astype(np.float64), faces)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    graph = coo_matrix(
        (np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
        shape=(len(vertices), len(vertices)),
    )
    components, labels = connected_components(graph, directed=False)
    component_rows = []
    for label in range(components):
        chosen = faces[labels[faces[:, 0]] == label]
        points = vertices[np.unique(chosen)]
        tri = vertices[chosen].astype(np.float64)
        volume = (
            np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
        )
        component_rows.append(
            {
                "triangles": len(chosen),
                "signed_volume_m3": float(volume),
                "bounds_m": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
            }
        )
    triangles = vertices[faces].astype(np.float64)
    normal = np.cross(
        triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    )
    header_dot = (normal * records["normal"]).sum(axis=1)
    report = {
        "file": str(source.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "reader": "independent-struct-numpy-scipy",
        "surface": metrics,
        "components": components,
        "component_rows": sorted(
            component_rows, key=lambda x: x["triangles"], reverse=True
        ),
        "header_normals_opposed": int(np.count_nonzero(header_dot < 0)),
        "self_intersections": "UNMEASURED",
        "gpu_compute_used": False,
    }
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps({"file": source.name, "surface": metrics, "components": components})
    )


if __name__ == "__main__":
    main()

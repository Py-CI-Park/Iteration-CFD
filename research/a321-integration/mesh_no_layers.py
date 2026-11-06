#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "meshpy", "manifold3d", "networkx"]
# ///
# How to run: uv run mesh_no_layers.py
"""Control PLC test on remeshed skin without extruded layer; isolate offset failure."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import trimesh
from meshpy import tet

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Build a separate CPU control mesh without altering failed layer inputs."""
    out = ROOT / "artifacts/control-tets"
    out.mkdir(parents=True, exist_ok=False)
    os.chdir(out)
    with np.load(ROOT / "artifacts/hybrid-r4/surface.npz") as d:
        v, f = d["vertices"], d["faces"]
    boundary = trimesh.creation.box(extents=[180, 130, 100])
    boundary.apply_translation([45, 0, 5])
    boundary = boundary.subdivide().subdivide().subdivide()
    info = tet.MeshInfo()
    info.set_points(np.vstack((v, boundary.vertices)).tolist())
    info.set_facets(np.vstack((f, boundary.faces + len(v))).tolist())
    info.set_holes([[22, 0, 4]])
    result = tet.build(info, options=tet.Options("pq1.4a100YQ"), verbose=False)
    np.savez_compressed(
        out / "hybrid.npz",
        vertices=np.array(result.points),
        tets=np.array(result.elements),
        prisms=np.empty((0, 6), dtype=np.int64),
    )
    (ROOT / "evidence/control-tets.json").write_text(
        json.dumps(
            {
                "points": len(result.points),
                "tets": len(result.elements),
                "prisms": 0,
                "gpu_compute": False,
            }
        ),
        encoding="utf8",
    )
    print("CONTROL_SUCCESS", len(result.elements))


if __name__ == "__main__":
    main()

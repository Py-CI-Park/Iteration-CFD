#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "trimesh", "networkx", "manifold3d"]
# ///
# How to run: uv run repair_remesh.py; bounded small remesh-hole repair trial.
"""Fill only triangle/quad remesher holes and record topology before accepting any mesh trial."""

from __future__ import annotations

import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Record explicit local caps rather than silently calling an invalid remesh usable."""
    out = ROOT / "artifacts/remesh-30k-repair"
    out.mkdir(exist_ok=False)
    source = trimesh.load_mesh(ROOT / "artifacts/remesh-30k/surface.stl", process=True)
    before = len(source.faces)
    trimesh.repair.fill_holes(source)
    trimesh.repair.fix_normals(source)
    solid = mf.Manifold(
        mf.Mesh(source.vertices.astype(np.float32), source.faces.astype(np.uint32))
    )
    source.export(out / "surface.stl")
    np.savez_compressed(
        out / "surface.npz", vertices=source.vertices, faces=source.faces
    )
    result = {
        "before_triangles": before,
        "after_triangles": len(source.faces),
        "added_caps": len(source.faces) - before,
        "watertight": bool(source.is_watertight),
        "kernel_status": str(solid.status()),
        "status": "TRIAL_ONLY_FIDELITY_PENDING"
        if source.is_watertight and solid.status() == mf.Error.NoError
        else "REJECTED",
        "gpu_compute": False,
    }
    (ROOT / "evidence/remesh-repair.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "netgen-mesher", "trimesh", "manifold3d"]
# ///
# How to run: install uv, then uv run netgen_clean.py; fresh CPU surface trial.
"""Test a separately simplified computational surface against Netgen's close-point welding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

import manifold3d as mf
import numpy as np
import trimesh
from netgen.meshing import MeshingParameters, MeshingStep
from netgen.stl import STLGeometry

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Preserve R3, simplify a derivative by 0.5mm and write intermediate topology before meshing."""
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    if (
        hashlib.sha256(source.read_bytes()).hexdigest()
        != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
    ):
        raise RuntimeError("R3_SHA_MISMATCH")
    root = ROOT / "artifacts/netgen-surface-04"
    root.mkdir(parents=True, exist_ok=False)
    mesh = trimesh.load_mesh(source, process=True)
    solid = mf.Manifold(
        mf.Mesh(
            np.array(mesh.vertices, dtype=np.float32),
            np.array(mesh.faces, dtype=np.uint32),
        )
    ).simplify(0.0005)
    data = solid.to_mesh()
    v = np.array(data.vert_properties[:, :3])
    f = np.array(data.tri_verts, dtype=np.int64)
    surface = trimesh.Trimesh(v, f, process=True)
    surface.export(root / "simplified.stl")
    (root / "simplified-ascii.stl").write_text(
        surface.export(file_type="stl_ascii"), encoding="ascii", newline="\n"
    )
    (ROOT / "evidence/netgen-surface-04-input.json").write_text(
        json.dumps(
            {
                "kernel": str(solid.status()),
                "vertices": len(surface.vertices),
                "triangles": len(surface.faces),
                "closed": bool(surface.is_watertight),
                "winding": bool(surface.is_winding_consistent),
                "min_edge_m": float(surface.edges_unique_length.min()),
                "operation_tolerance_m": 0.0005,
                "geometry_fidelity": "NOT_YET_MEASURED",
                "gpu_compute": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    print("SIMPLIFIED_INPUT", len(v), len(f), flush=True)
    ng = STLGeometry(str(root / "simplified-ascii.stl")).GenerateMesh(
        mp=MeshingParameters(
            maxh=0.2,
            grading=0.3,
            perfstepsend=MeshingStep.MESHSURFACE,
            minedgelen=0.005,
            closeedgefac=0.3,
        )
    )
    ng.Save(str(root / "surface.vol"))
    vertices = np.array([tuple(p.p) for p in ng.Points()])
    faces = np.array(
        [[i.nr - 1 for i in e.vertices] for e in ng.Elements2D()], dtype=np.int64
    )
    if len(faces) == 0:
        raise RuntimeError("EMPTY_SURFACE")
    np.savez_compressed(root / "surface.npz", vertices=vertices, faces=faces)
    trimesh.Trimesh(vertices, faces, process=False).export(root / "surface.stl")
    print("SURFACE_BUILT", len(vertices), len(faces), flush=True)


if __name__ == "__main__":
    main()

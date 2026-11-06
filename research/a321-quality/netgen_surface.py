#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "netgen-mesher", "trimesh", "scipy", "rtree"]
# ///
# How to run: install uv, then uv run netgen_surface.py. CPU surface generation only.
"""Run Netgen's public STL surface API on the preserved R3 reference."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Final

import numpy as np
import trimesh
from netgen.meshing import MeshingParameters, MeshingStep
from netgen.stl import STLGeometry
from surface_input import ascii_copy

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Write a fresh surface trial with explicit reference and topology receipts."""
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745":
        raise RuntimeError("R3_SHA_MISMATCH")
    root = ROOT / "artifacts/netgen-surface-02"
    root.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    print("NETGEN_SURFACE_START", flush=True)
    params = MeshingParameters(
        maxh=0.25,
        grading=0.3,
        perfstepsend=MeshingStep.MESHSURFACE,
        yangle=30,
        contyangle=20,
        closeedgefac=0.3,
        minedgelen=0.005,
        optsteps2d=5,
    )
    ascii_copy(source, root / "reference-ascii.stl")
    mesh = STLGeometry(str(root / "reference-ascii.stl")).GenerateMesh(mp=params)
    mesh.Save(str(root / "surface.vol"))
    vertices = np.array([tuple(p.p) for p in mesh.Points()])
    faces = np.array(
        [[i.nr - 1 for i in e.vertices] for e in mesh.Elements2D()], dtype=np.int64
    )
    if len(vertices) == 0 or len(faces) == 0:
        raise RuntimeError("EMPTY_NETGEN_SURFACE")
    surface = trimesh.Trimesh(vertices, faces, process=True)
    surface.export(root / "surface.stl")
    np.savez_compressed(
        root / "surface.npz", vertices=surface.vertices, faces=surface.faces
    )
    reference = trimesh.load_mesh(source, process=True)
    distances = []
    for a, b, label in [
        (reference, surface, "reference_to_candidate"),
        (surface, reference, "candidate_to_reference"),
    ]:
        samples = a.sample(12000, seed=20261106)
        _, d, _ = trimesh.proximity.closest_point(b, samples)
        distances.append(
            {
                "direction": label,
                "samples": len(d),
                "max_m": float(d.max()),
                "p95_m": float(np.quantile(d, 0.95)),
            }
        )
    record = {
        "source_sha256": digest,
        "vertices": len(surface.vertices),
        "triangles": len(surface.faces),
        "watertight": bool(surface.is_watertight),
        "winding": bool(surface.is_winding_consistent),
        "min_edge_m": float(surface.edges_unique_length.min()),
        "sampled_surface_distance": distances,
        "seconds": time.monotonic() - start,
        "gpu_compute": False,
        "solver_run": False,
        "status": "SURFACE_TRIAL_ONLY",
    }
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/netgen-surface-02.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()

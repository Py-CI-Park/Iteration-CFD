#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "manifold3d", "trimesh"]
# ///
# How to run: uv run reconstruct.py (after Blender export_reference.py).
"""Reconstruct documented symmetric aerodynamic loft solids from frozen native sections."""

from __future__ import annotations

import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh
from profiles import chord_hull, loft, radial_hull, section_points

ROOT = Path(__file__).resolve().parent


def build_part(
    name: str, axis: int, count: int, ring_count: int
) -> tuple[trimesh.Trimesh, dict]:
    """Use convex section envelopes, recording all stations and resulting section rings."""
    with np.load(ROOT / f"artifacts/reference/{name}.npz") as data:
        v, f = data["vertices"], data["faces"]
    lo, hi = float(v[:, axis].min()), float(v[:, axis].max())
    # End-section offsets avoid zero-area endpoint triangles. Actual end planes are retained.
    stations = np.linspace(lo + 0.001, hi - 0.001, count)
    if name != "fuselage":
        important = {
            "wing": [2, 5, 10, 15],
            "horizontal": [1, 3, 5],
            "vertical": [6, 8, 10, 11],
        }[name]
        stations = np.unique(np.concatenate((stations, important)))
    sampler = radial_hull if name == "fuselage" else chord_hull
    rings = np.array(
        [sampler(section_points(v, f, axis, float(s)), ring_count) for s in stations]
    )
    if name == "fuselage":
        # Suppress reference left/right asymmetry by envelope around the native centerplane.
        for i, ring in enumerate(rings):
            mirrored = ring * np.array([-1, 1])
            rings[i] = radial_hull(np.concatenate((ring, mirrored)), ring_count)
        nose = rings[0].mean(axis=0)
        tail = rings[-1].mean(axis=0)
        rings = np.concatenate(
            (
                (nose + (rings[0] - nose) * 0.03)[None],
                rings,
                (tail + (rings[-1] - tail) * 0.03)[None],
            )
        )
        stations = np.concatenate(([lo], stations, [hi]))
    else:
        stations[0], stations[-1] = lo, hi
    vertices, faces = loft(stations, rings, axis)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    record = {
        "name": name,
        "axis": axis,
        "stations_m": stations.tolist(),
        "rings_2d_m": rings.tolist(),
        "method": "convex triangle-plane envelope; fuselage radial / lifting surfaces cosine-chord sampling; straight loft between stations",
        "reference_bounds_m": [v.min(axis=0).tolist(), v.max(axis=0).tolist()],
        "bounds_m": mesh.bounds.tolist(),
        "triangles": len(faces),
        "volume_m3": float(mesh.volume),
    }
    return mesh, record


def main() -> None:
    """Create closed manifold Boolean-union output and measured derivation receipts."""
    out = ROOT / "artifacts/shell-r2"
    out.mkdir(parents=True, exist_ok=False)
    parts, records = [], []
    for name, axis, count, k in [
        ("fuselage", 0, 180, 128),
        ("wing", 1, 96, 128),
        ("horizontal", 1, 64, 96),
        ("vertical", 2, 72, 96),
    ]:
        mesh, record = build_part(name, axis, count, k)
        mesh.export(out / f"{name}.stl")
        parts.append(mesh)
        records.append(record)
        if name in ("wing", "horizontal"):
            mirror = mesh.copy()
            mirror.apply_transform(np.diag([1, -1, 1, 1]))
            mirror.export(out / f"{name}-port.stl")
            parts.append(mirror)
    solids = []
    for mesh in parts:
        solid = mf.Manifold(
            mf.Mesh(
                np.array(mesh.vertices, dtype=np.float32),
                np.array(mesh.faces, dtype=np.uint32),
            )
        )
        if solid.status() != mf.Error.NoError:
            raise RuntimeError(f"BOOLEAN_INPUT_INVALID:{solid.status()}")
        solids.append(solid)
    result = solids[0]
    for solid in solids[1:]:
        result = result + solid
    if result.status() != mf.Error.NoError:
        raise RuntimeError(f"BOOLEAN_UNION_FAILED:{result.status()}")
    output = result.to_mesh()
    final = trimesh.Trimesh(
        vertices=output.vert_properties[:, :3], faces=output.tri_verts, process=False
    )
    final.export(out / "A321_AIRFRAME_SHELL_R2.stl")
    np.savez_compressed(out / "shell.npz", vertices=final.vertices, faces=final.faces)
    report = {
        "model": "A321-derived symmetric airframe shell R2",
        "not_oem": True,
        "omitted": [
            "engines/pylons",
            "gear",
            "sharklets",
            "flap/slat gaps",
            "windows/doors",
            "interior",
        ],
        "symmetry": "port wing and horizontal tail mirrored from starboard; fuselage symmetric envelope",
        "parts": records,
        "union_status": str(result.status()),
        "union_components": len(result.decompose()),
        "triangles": len(final.faces),
        "bounds_m": final.bounds.tolist(),
        "area_m2": float(final.area),
        "volume_m3": float(final.volume),
        "watertight": bool(final.is_watertight),
        "winding_consistent": bool(final.is_winding_consistent),
        "gpu_compute": False,
    }
    (ROOT / "evidence/reconstruction-r2.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "parts"}))


if __name__ == "__main__":
    main()

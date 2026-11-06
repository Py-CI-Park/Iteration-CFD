#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d"]
# ///
# How to run: uv run reconstruct_r3.py; R2 and original native remain untouched.
"""Repair measured span notches with local profile interpolation, then CPU-union a new candidate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-shell"))
from profiles import loft


def main() -> None:
    """Bridge identified device gaps only; document every changed section and its displacement."""
    record = json.loads(
        (ROOT.parent / "a321-shell/evidence/reconstruction-r2.json").read_text()
    )
    out = ROOT / "artifacts/shell-r3"
    out.mkdir(parents=True, exist_ok=False)
    changes = []
    solids = []
    for part in record["parts"]:
        y = np.array(part["stations_m"])
        rings = np.array(part["rings_2d_m"])
        if part["name"] == "wing":
            # A 20mm flap seam in the reference removes the entire trailing slab at this station.
            # Patch only the measured gap band and root slat-onset step, not the entire wing.
            for lo, hi, reason in [
                (6.10, 6.60, "R2 trailing-edge flap seam notch"),
                (0.0, 2.35, "R2 root leading-edge slat onset step"),
            ]:
                previous_step = rings.copy()
                if lo == 0:
                    valid = (y >= hi) & (y <= 3.8)
                    for j in range(rings.shape[1]):
                        for k in range(2):
                            fit = np.polyfit(y[valid], rings[valid, j, k], 1)
                            rings[y < hi, j, k] = np.polyval(fit, y[y < hi])
                else:
                    left = np.flatnonzero(y < lo)[-1]
                    right = np.flatnonzero(y > hi)[0]
                    mask = (y >= lo) & (y <= hi)
                    weight = (y[mask] - y[left]) / (y[right] - y[left])
                    rings[mask] = (
                        rings[left][None] * (1 - weight[:, None, None])
                        + rings[right][None] * weight[:, None, None]
                    )
                mask = np.max(np.abs(rings - previous_step), axis=(1, 2)) > 1e-10
                changes.append(
                    {
                        "reason": reason,
                        "band_m": [lo, hi],
                        "changed_stations": y[mask].tolist(),
                        "max_ring_displacement_m": float(
                            np.linalg.norm(rings - previous_step, axis=2).max()
                        ),
                    }
                )
            part["rings_2d_m"] = rings.tolist()
        vertices, faces = loft(y, rings, part["axis"])
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.export(out / f"{part['name']}.stl")
        for mirror in (
            [False, True] if part["name"] in ("wing", "horizontal") else [False]
        ):
            m = mesh.copy()
            if mirror:
                m.apply_transform(np.diag([1, -1, 1, 1]))
            solid = mf.Manifold(
                mf.Mesh(m.vertices.astype(np.float32), m.faces.astype(np.uint32))
            )
            if solid.status() != mf.Error.NoError:
                raise RuntimeError(str(solid.status()))
            solids.append(solid)
    result = solids[0]
    for solid in solids[1:]:
        result = result + solid
    packed = result.to_mesh()
    mesh = trimesh.Trimesh(
        packed.vert_properties[:, :3], packed.tri_verts, process=False
    )
    mesh.export(out / "A321_AIRFRAME_SHELL_R3.stl")
    np.savez_compressed(out / "shell.npz", vertices=mesh.vertices, faces=mesh.faces)
    record.update(
        {
            "model": "A321-derived aerodynamic shell R3 local gap repair",
            "changes": changes,
            "triangles": len(mesh.faces),
            "volume_m3": float(mesh.volume),
            "area_m2": float(mesh.area),
            "bounds_m": mesh.bounds.tolist(),
            "kernel_status": str(result.status()),
            "kernel_components": len(result.decompose()),
            "gpu_compute": False,
            "fidelity_status": "HOLD; interpolation/extrapolation changes physical wing at root and device seam",
        }
    )
    (ROOT / "evidence/reconstruction-r3.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {
                k: record[k]
                for k in ["changes", "triangles", "kernel_components", "volume_m3"]
            }
        )
    )


if __name__ == "__main__":
    main()

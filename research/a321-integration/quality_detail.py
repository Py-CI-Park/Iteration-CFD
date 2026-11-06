#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d"]
# ///
# How to run: uv run quality_detail.py
"""Measure achieved layer capture and local groove-repair topology without solving flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-shell"))
from audit_shell import vertex_links


def main() -> None:
    """Audit actual stored vertices, layer scales and preserved face geometry."""
    root = ROOT / "artifacts/hybrid-r5"
    shell = trimesh.load_mesh(ROOT / "models/A321_AIRFRAME_SHELL_R3.stl", process=True)
    solid = mf.Manifold(
        mf.Mesh(shell.vertices.astype(np.float32), shell.faces.astype(np.uint32))
    )
    with np.load(root / "hybrid.npz") as d:
        scale = d["layer_scale"]
        heights = d["heights"]
        v = d["vertices"]
        faces = d["wall_faces"]
        tets = d["tets"]
    with np.load(root / "face-data.npz") as d:
        sf, owner, neighbour = d["sf"], d["owner"], d["neighbour"]
        vol = d["volume"]
        center = d["centers"]
        nonorth = d["nonorth"]
    closure = np.zeros_like(center)
    np.add.at(closure, owner, sf)
    np.add.at(closure, neighbour, -sf[: len(neighbour)])
    tri = v[faces]
    area = (
        np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        / 2
    )
    first = scale[faces].mean(axis=1) * heights[1]
    utau = 1.1742530824190927
    nu = 1.46e-5
    yplus_est = first * 0.5 * utau / nu
    # The 8-layer metric is zero for a 5-layer trial, irrespective of thin first cells.
    receipt = {
        "r3_surface": {
            "vertices": len(shell.vertices),
            "triangles": len(shell.faces),
            "watertight": bool(shell.is_watertight),
            "vertex_link_failures": len(vertex_links(shell.faces, len(shell.vertices))),
            "kernel_status": str(solid.status()),
            "components": len(solid.decompose()),
            "volume_m3": float(shell.volume),
        },
        "layer_capture": {
            "requested_layers": 5,
            "minimum_8_layer_coverage": 0.0,
            "nominal_first_m": float(heights[1]),
            "achieved_scale_min": float(scale.min()),
            "achieved_scale_median": float(np.median(scale)),
            "full_nominal_area_fraction": float(
                area[np.all(scale[faces] >= 0.999, axis=1)].sum() / area.sum()
            ),
            "area_fraction_apriori_yplus_le1": float(
                area[yplus_est <= 1].sum() / area.sum()
            ),
            "note": "a priori only; collapsed nanometre layers are failure, not high resolution success",
        },
        "max_absolute_closure_m2": float(np.linalg.norm(closure, axis=1).max()),
        "tet_min_volume_m3": float(vol[: len(tets)].min()),
        "prism_min_volume_m3": float(vol[len(tets) :].min()),
        "faces_nonorth_quantiles_deg": np.quantile(nonorth, [0.5, 0.9, 0.99]).tolist(),
        "status": "FIX_FIRST",
        "ofgpu_gate": "NOT_RUN",
        "solver_run": False,
    }
    (ROOT / "evidence/quality-detail.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: uv run diagnose_previous.py
"""Locate old layer inversion and separate face-shape from normal-direction limitations."""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Measure old prism Jacobian minima and corner displacement angles."""
    with np.load(ROOT.parent / "a321-integration/artifacts/hybrid-r5/hybrid.npz") as d:
        v, c, faces = d["vertices"], d["prisms"], d["wall_faces"]
    p = v[c]
    dr = (p[:, 1] - p[:, 0] + p[:, 4] - p[:, 3]) * 0.5
    ds = (p[:, 2] - p[:, 0] + p[:, 5] - p[:, 3]) * 0.5
    dt = (p[:, 3:6] - p[:, :3]).mean(axis=1)
    jac = np.einsum("ij,ij->i", np.cross(dr, ds), dt)
    tri = v[faces]
    a = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    a /= np.linalg.norm(a, axis=1)[:, None]
    n = len(np.unique(faces))
    delta = v[n : 2 * n] - v[:n]
    dot = (delta[faces] * a[:, None]).sum(axis=2) / np.linalg.norm(delta[faces], axis=2)
    worst = np.argsort(dot.min(axis=1))[:20]
    result = {
        "old_prisms": len(c),
        "midpoint_jac_nonpositive": int(np.count_nonzero(jac <= 0)),
        "min_corner_displacement_cos_face_normal": float(dot.min()),
        "worst_triangles": [
            {
                "id": int(i),
                "center_m": tri[i].mean(axis=0).tolist(),
                "minimum_cos": float(dot[i].min()),
            }
            for i in worst
        ],
        "gpu_compute": False,
        "solver_run": False,
    }
    (ROOT / "evidence/previous-normal-diagnosis.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result)[:3000])


if __name__ == "__main__":
    main()

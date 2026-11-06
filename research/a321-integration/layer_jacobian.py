#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: uv run layer_jacobian.py; sample actual prism isoparametric Jacobians.
"""Reject folded or vanishing prism layers instead of relying on total cell volume."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Sample 3 triangle coordinates and 2 layer coordinates on every stored prism."""
    with np.load(ROOT / "artifacts/hybrid-r5/hybrid.npz") as d:
        v, c = d["vertices"], d["prisms"]
    p = v[c]
    minimum = np.full(len(c), np.inf)
    maximum = np.full(len(c), -np.inf)
    for r, s in [(1 / 6, 1 / 6), (2 / 3, 1 / 6), (1 / 6, 2 / 3)]:
        for t in [0.2113248654, 0.7886751346]:
            dr = (1 - t) * (p[:, 1] - p[:, 0]) + t * (p[:, 4] - p[:, 3])
            ds = (1 - t) * (p[:, 2] - p[:, 0]) + t * (p[:, 5] - p[:, 3])
            dt = (
                (1 - r - s) * (p[:, 3] - p[:, 0])
                + r * (p[:, 4] - p[:, 1])
                + s * (p[:, 5] - p[:, 2])
            )
            jac = np.einsum("ij,ij->i", np.cross(dr, ds), dt)
            minimum = np.minimum(minimum, jac)
            maximum = np.maximum(maximum, jac)
    record = {
        "prisms": len(c),
        "quadrature_samples_each": 6,
        "minimum_jacobian_m3": float(minimum.min()),
        "nonpositive_sample_prisms": int(np.count_nonzero(minimum <= 0)),
        "samples_with_sign_change_prisms": int(
            np.count_nonzero((minimum <= 0) & (maximum > 0))
        ),
        "scope": "6 samples per prism, not continuous Jacobian proof",
        "status": "FIX_FIRST",
        "solver_run": False,
    }
    (ROOT / "evidence/prism-jacobian.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with numpy --with scipy --with pytest -m pytest test_orientation.py
"""A measured wing-root prism demonstrates why centroid-based per-face flipping breaks closure."""

import json
from pathlib import Path

import numpy as np
from convert_oriented import geometry


def test_warped_prism_preserves_topological_face_orientation():
    # Given: original failed trial, prism 55459. This locks the orientation defect independently of Jacobian.
    data = json.loads(
        (Path(__file__).parent / "evidence/warped-prism-regression.json").read_text()
    )
    v = np.array(data["vertices"])
    f = np.array(
        [[0, 2, 1, -1], [3, 4, 5, -1], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]]
    )
    sf, cf = geometry(v, f)
    # When: the old rule independently reverses a face.
    reverse = np.einsum("ij,ij->i", sf, cf - v.mean(axis=0)) < 0
    flipped = sf.copy()
    flipped[reverse] *= -1
    # Then: topological closure remains small, whereas the old flip creates a false leak.
    assert np.flatnonzero(reverse).tolist() == [2]
    assert np.linalg.norm(sf.sum(axis=0)) < 1e-18
    assert np.linalg.norm(flipped.sum(axis=0)) > 1e-8

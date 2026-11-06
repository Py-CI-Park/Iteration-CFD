#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_layers.py
"""Saved hybrid interface is conformal; thin layers cannot be declared adequate."""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def test_saved_outer_interface_faces_are_shared_by_tets_and_prisms():
    # Given
    with np.load(ROOT / "artifacts/hybrid-r5/hybrid.npz") as d:
        tets, prisms = d["tets"], d["prisms"]
    # When
    tf = np.sort(
        np.concatenate(
            (
                tets[:, [0, 1, 2]],
                tets[:, [0, 1, 3]],
                tets[:, [0, 2, 3]],
                tets[:, [1, 2, 3]],
            )
        ),
        axis=1,
    )
    keys, count = np.unique(tf, axis=0, return_counts=True)
    boundary = keys[count == 1]
    top = np.sort(prisms[-129522:, 3:], axis=1)
    available = {tuple(r) for r in boundary}
    # Then
    assert all(tuple(r) in available for r in top)


def test_known_bad_mesh_stays_fix_first():
    # Given
    report = json.loads((ROOT / "evidence/polyMesh-quality.json").read_text())
    # When / Then
    assert report["max_nonorth_deg"] > 70
    assert report["status"] == "FIX_FIRST"
    assert report["solver_executed"] is False

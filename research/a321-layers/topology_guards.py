#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: imported by convert_oriented.py; tested by test_topology_guards.py.
"""Require conformal incidence and opposite cyclic winding before serializing a hybrid."""

from __future__ import annotations

import numpy as np


def require_same_triangles(actual: np.ndarray, expected: np.ndarray) -> None:
    """Compare complete multisets; reject missing, extra or split interface/wall faces."""
    a = np.sort(actual, axis=1)
    b = np.sort(expected, axis=1)
    if a.shape != b.shape or not np.array_equal(a[np.lexsort(a.T)], b[np.lexsort(b.T)]):
        raise RuntimeError("TRIANGLE_MEMBERSHIP_MISMATCH")


def require_opposite_winding(first: np.ndarray, second: np.ndarray) -> None:
    """Every shared triangle/quad must be oppositely wound, up to cyclic rotation."""
    for width in (3, 4):
        mask = (first >= 0).sum(axis=1) == width
        a = first[mask, :width]
        b = second[mask, :width][:, ::-1]
        match = np.zeros(len(a), dtype=bool)
        for shift in range(width):
            match |= np.all(a == np.roll(b, shift, axis=1), axis=1)
        if not np.all(match):
            raise RuntimeError("SHARED_FACE_WINDING_MISMATCH")

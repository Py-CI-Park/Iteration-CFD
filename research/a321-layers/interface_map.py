#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: imported by exterior_tets.py, tested by test_interface.py.
"""Restore arbitrary tetrahedral point ordering only when every interface coordinate is exact."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def align_interface(
    points: np.ndarray, cells: np.ndarray, interface: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Reject coordinate changes or duplicate mapping, but permit harmless index permutations."""
    distance, matched = cKDTree(points).query(interface)
    if np.any(distance != 0) or len(np.unique(matched)) != len(interface):
        raise RuntimeError(
            f"INTERFACE_COORDINATE_CHANGE max_distance_m={distance.max():.17g}"
        )
    remaining = np.setdiff1d(np.arange(len(points)), matched, assume_unique=True)
    order = np.r_[matched, remaining]
    inverse = np.empty(len(points), dtype=np.int64)
    inverse[order] = np.arange(len(points))
    return points[order], inverse[cells]

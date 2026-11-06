#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with numpy --with scipy --with pytest -m pytest test_interface.py
"""Input permutations are harmless; interface movement is never silently tolerated."""

import numpy as np
import pytest
from interface_map import align_interface


def test_permutation_preserves_tetrahedron_coordinates():
    points = np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0], [1, 0, 0]], float)
    cells = np.array([[0, 1, 2, 3]])
    interface = points[[2, 3, 0]]
    output, mapped = align_interface(points, cells, interface)
    assert np.array_equal(output[:3], interface)
    assert np.array_equal(output[mapped], points[cells])


def test_moved_interface_is_rejected():
    points = np.array([[0.0, 0, 0], [1, 0, 0]])
    with pytest.raises(RuntimeError, match="INTERFACE_COORDINATE_CHANGE"):
        align_interface(points, np.array([[0, 1]]), np.array([[0.0, 0, 0.000001]]))

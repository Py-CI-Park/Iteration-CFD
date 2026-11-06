#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pytest"]
# ///
# How to run: uv run --with numpy --with pytest -m pytest test_topology_guards.py
"""Reject conformal-looking coordinate matches with missing or misoriented interface faces."""

import numpy as np
import pytest
from topology_guards import require_opposite_winding, require_same_triangles


def test_opposite_cyclic_triangle_is_valid():
    require_opposite_winding(np.array([[0, 1, 2, -1]]), np.array([[1, 0, 2, -1]]))


def test_same_winding_is_rejected():
    with pytest.raises(RuntimeError, match="WINDING"):
        require_opposite_winding(np.array([[0, 1, 2, -1]]), np.array([[1, 2, 0, -1]]))


@pytest.mark.parametrize("actual", [[[0, 1, 2]], [[0, 1, 2], [0, 2, 4], [0, 4, 3]]])
def test_missing_or_split_interface_is_rejected(actual):
    with pytest.raises(RuntimeError, match="MEMBERSHIP"):
        require_same_triangles(np.array(actual), np.array([[0, 1, 2], [0, 2, 3]]))

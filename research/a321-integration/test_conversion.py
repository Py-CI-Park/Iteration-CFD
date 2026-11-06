#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_conversion.py
"""Analytic face geometry checks for padded triangle/quad converter."""

import numpy as np
import pytest
from convert_fast import geometry


def test_triangle_vector_area_and_centroid():
    # Given
    vertices = np.array([[0, 0, 0], [2, 0, 0], [0, 2, 0]], float)
    # When
    sf, cf = geometry(vertices, np.array([[0, 1, 2, -1]]))
    # Then
    assert sf[0] == pytest.approx([0, 0, 2])
    assert cf[0] == pytest.approx([2 / 3, 2 / 3, 0])


def test_quad_orientation_reverses_vector_area():
    # Given
    vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], float)
    # When
    sf, cf = geometry(vertices, np.array([[0, 1, 2, 3], [3, 2, 1, 0]]))
    # Then
    assert sf[0] == pytest.approx([0, 0, 1])
    assert sf[1] == pytest.approx([0, 0, -1])
    assert cf[0] == pytest.approx([0.5, 0.5, 0])

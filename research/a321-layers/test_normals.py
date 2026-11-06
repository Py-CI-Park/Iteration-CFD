#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_normals.py
"""Constrained direction must point out of every incident face, unlike old average normals."""

import numpy as np
from normal_field import constrained_directions


def test_obtuse_face_fan_keeps_all_outward_projections_positive():
    # Given
    normals = np.array([[1, 0, 0], [-0.4, 0.916515, 0], [0, 0, 1]], float)
    # When
    result = constrained_directions(normals, [np.array([0, 1, 2])])
    # Then
    assert np.min(normals @ result[0]) > 0.1


def test_flat_fan_stays_normal_to_plane():
    # Given
    normals = np.tile([0.0, 0.0, 1.0], (6, 1))
    # When
    result = constrained_directions(normals, [np.arange(6)])
    # Then
    assert np.allclose(result[0], [0, 0, 1])

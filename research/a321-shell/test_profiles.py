#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_profiles.py
"""Analytic regression tests for closed section lofts."""

import numpy as np
import pytest
from profiles import chord_hull, loft, radial_hull, section_points


def test_thin_airfoil_retains_exact_chord_extrema():
    # Given
    points = np.array([[0, 0], [1, 0.08], [5, 0], [1, -0.08]], float)
    # When
    ring = chord_hull(points, 128)
    # Then
    assert ring[:, 0].min() == 0
    assert ring[:, 0].max() == 5
    assert len(ring) == 128


def test_cube_section_is_exact_square():
    # Given
    v = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ],
        float,
    )
    f = np.array(
        [
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ]
    )
    # When
    points = section_points(v, f, 2, 0.5)
    # Then
    assert points.min(axis=0) == pytest.approx([0, 0])
    assert points.max(axis=0) == pytest.approx([1, 1])


def test_radial_hull_stays_on_square():
    # Given
    points = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], float)
    # When
    ring = radial_hull(points, 32)
    # Then
    assert np.max(np.abs(ring), axis=1) == pytest.approx(np.ones(32))


def test_loft_is_closed_and_has_known_volume():
    # Given
    angles = np.arange(64) * 2 * np.pi / 64
    ring = np.column_stack([np.cos(angles), np.sin(angles)])
    # When
    v, f = loft(np.array([0.0, 2.0]), np.array([ring, ring]), 2)
    # Then
    edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    assert np.unique(edges, axis=0, return_counts=True)[1].tolist() == [2] * len(
        np.unique(edges, axis=0)
    )
    tri = v[f]
    volume = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
    assert volume == pytest.approx(64 * np.sin(2 * np.pi / 64), rel=1e-12)

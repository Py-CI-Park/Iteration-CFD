#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pytest"]
# ///
# ─── How to run ───
# uv run --with pytest -m pytest research/a321-preflight/test_surface_metrics.py -q
"""Geometric invariants for the CPU-only surface gate."""

from __future__ import annotations

import numpy as np
import pytest
from surface_metrics import measure


def tetrahedron():
    """Return an outward unit-coordinate tetrahedron."""
    return np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float
    ), np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)


def test_closed_tetrahedron_has_known_area_and_volume():
    # Given
    vertices, faces = tetrahedron()
    # When
    result = measure(vertices, faces)
    # Then
    assert result["closed_oriented"]
    assert result["signed_volume_m3"] == pytest.approx(1 / 6)
    assert result["area_m2"] == pytest.approx((3 + np.sqrt(3)) / 2)


def test_missing_face_reports_three_open_edges():
    # Given
    vertices, faces = tetrahedron()
    # When
    result = measure(vertices, faces[:-1])
    # Then
    assert result["boundary_edges"] == 3
    assert not result["closed_oriented"]


def test_reversed_face_reports_orientation_error():
    # Given
    vertices, faces = tetrahedron()
    faces[0] = faces[0, ::-1]
    # When
    result = measure(vertices, faces)
    # Then
    assert result["inconsistent_edges"] == 3


def test_duplicate_face_reports_nonmanifold_edges():
    # Given
    vertices, faces = tetrahedron()
    # When
    result = measure(vertices, np.concatenate([faces, faces[:1]]))
    # Then
    assert result["duplicate_triangles"] == 1
    assert result["nonmanifold_edges"] == 3


def test_nonfinite_coordinate_is_rejected_before_topology_pass():
    # Given
    vertices, faces = tetrahedron()
    vertices[0, 0] = np.nan
    # When / Then
    with pytest.raises(RuntimeError, match="NONFINITE_VERTEX"):
        measure(vertices, faces)

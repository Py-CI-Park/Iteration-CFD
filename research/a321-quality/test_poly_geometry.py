#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pytest"]
# ///
# How to run: uv run --with numpy --with pytest -m pytest test_poly_geometry.py.
"""Independent geometric checks for a general polygonal finite-volume audit."""

from __future__ import annotations

import numpy as np
import pytest


def test_concave_polygon_uses_signed_area_centroid() -> None:
    """Given a U polygon whose vertex mean lies outside, overlap must cancel in the centroid."""
    from poly_geometry import face_geometry

    v = np.array(
        [
            [0, 0, 0],
            [3, 0, 0],
            [3, 3, 0],
            [2, 3, 0],
            [2, 1, 0],
            [1, 1, 0],
            [1, 3, 0],
            [0, 3, 0],
        ],
        float,
    )
    sf, cf = face_geometry(v, np.arange(8).reshape(1, -1))
    assert sf[0] == pytest.approx([0, 0, 7])
    assert cf[0] == pytest.approx([1.5, 19 / 14, 0])


def test_warped_cube_volume_uses_triangle_pyramid_moments() -> None:
    """Given one top corner at z=2, the stated center-fan surface encloses volume 1.25."""
    from poly_geometry import cell_geometry

    v = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 2],
            [0, 1, 1],
        ],
        float,
    )
    f = np.array(
        [
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ]
    )
    _, _, center, volume, _ = cell_geometry(
        v, f, np.zeros(6, dtype=int), np.empty(0, dtype=int)
    )
    assert volume[0] == pytest.approx(1.25)
    assert center[0] == pytest.approx([8 / 15, 8 / 15, 31 / 48])


def test_polygon_geometry_handles_pentagon() -> None:
    """Given a pentagon, the general audit must compute area and centroid without quad truncation."""
    from poly_geometry import face_geometry

    v = np.array([[0, 0, 0], [2, 0, 0], [2, 1, 0], [1, 2, 0], [0, 1, 0]], float)
    sf, cf = face_geometry(v, np.array([[0, 1, 2, 3, 4]]))
    assert sf[0] == pytest.approx([0, 0, 3])
    assert cf[0] == pytest.approx([1, 7 / 9, 0])


def test_saved_cube_has_unit_volume_and_central_centroid() -> None:
    """Given an oriented unit cube, reconstruct the finite-volume center independently of cell arrays."""
    from poly_geometry import cell_geometry

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
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ]
    )
    _, _, center, volume, closure = cell_geometry(
        v, f, np.zeros(6, dtype=int), np.empty(0, dtype=int)
    )
    assert center[0] == pytest.approx([0.5, 0.5, 0.5])
    assert volume[0] == pytest.approx(1.0)
    assert closure[0] == pytest.approx([0, 0, 0], abs=1e-15)

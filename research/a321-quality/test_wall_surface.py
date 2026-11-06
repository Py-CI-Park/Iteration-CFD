#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh", "pytest"]
# ///
# How to run: uv run --with numpy --with trimesh --with pytest -m pytest test_wall_surface.py.
"""Surface export must respect collinear split-edge points rather than make zero-area fan triangles."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from wall_surface import raw_wall_closed, triangulate_wall


def test_actual_warped_native_face_preserves_vector_area() -> None:
    """Given a valid 3-D face with a crossed projection, retain its explicit native fan."""
    rows = json.loads(
        (
            Path(__file__).parent / "evidence/polygon-regression-fixtures.json"
        ).read_text()
    )
    for row in rows:
        v = np.array(row["vertices"])
        surface = triangulate_wall(v, np.arange(len(v)).reshape(1, -1))
        triangle = surface.triangles
        area = 0.5 * np.cross(
            triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]
        ).sum(axis=0)
        expected = 0.5 * np.cross(v - v[0], np.roll(v, -1, axis=0) - v[0]).sum(axis=0)
        assert np.all(surface.area_faces > 0)
        assert np.allclose(area, expected, atol=1e-15)


def test_nonstar_concave_wall_has_no_overlapping_fan_triangles() -> None:
    """Given a U polygon, valid triangulation has area seven instead of overlapping fan area."""
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
    surface = triangulate_wall(v, np.arange(8).reshape(1, -1))
    assert np.isclose(surface.area, 7.0)


def test_cube_with_hanging_edge_point_stays_closed() -> None:
    """Given matching polygon edges, the exported triangle skin must remain closed."""
    vertices = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
            [0.5, 0, 0],
        ],
        float,
    )
    faces = np.array(
        [
            [0, 3, 2, 1, 8],
            [4, 5, 6, 7, -1],
            [0, 8, 1, 5, 4],
            [1, 2, 6, 5, -1],
            [2, 3, 7, 6, -1],
            [3, 0, 4, 7, -1],
        ]
    )
    surface = triangulate_wall(vertices, faces)
    assert surface.is_watertight
    assert surface.is_winding_consistent
    assert np.all(surface.area_faces > 0)
    assert np.isclose(surface.volume, 1.0)


def test_disconnected_near_coincident_faces_are_not_welded_closed() -> None:
    """Given face-local IDs and a tiny gap, visualization must not manufacture closure."""
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
    split = v[f].reshape(-1, 3)
    split[4:8, 2] += 1e-10
    ids = np.arange(24).reshape(6, 4)
    assert not raw_wall_closed(ids)
    assert not triangulate_wall(split, ids).is_watertight

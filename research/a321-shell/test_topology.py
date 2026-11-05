#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_topology.py
"""Vertex-link tests distinguish true solid topology from point-touching shells."""

import numpy as np
from audit_shell import vertex_links


def test_closed_tetrahedron_has_cyclic_vertex_links():
    # Given
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
    # When
    failures = vertex_links(faces, 4)
    # Then
    assert failures == []


def test_point_touching_closed_shells_fail_shared_vertex_link():
    # Given
    faces = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]], dtype=np.int64)
    other = np.where(faces == 0, 0, faces + 3)
    # When
    failures = vertex_links(np.concatenate((faces, other)), 7)
    # Then
    assert failures == [0]

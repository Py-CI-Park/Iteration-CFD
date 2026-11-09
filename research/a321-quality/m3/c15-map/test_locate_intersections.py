#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "pytest"]
# ///
# How to run: uv run --with numpy --with pytest python -B -m pytest -p no:cacheprovider test_locate_intersections.py
from __future__ import annotations

import numpy as np
from exact_contacts import audit_contact
from locate_intersections import intersection_points


def test_crossing_triangles_detected() -> None:
    # Given two triangles crossing through their interiors.
    a = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
    b = np.array([[.5, .5, -1.], [.5, .5, 1.], [1., 1., 0.]])
    # When the narrow phase is evaluated.
    points = intersection_points(a, b)
    # Then the segment endpoints lie on both triangles.
    assert len(points) == 2
    np.testing.assert_allclose(points[:, 2], 0.)


def test_edge_sharing_triangles_excluded() -> None:
    # Given triangles sharing an exact edge.
    a = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    b = np.array([[0., 0., 0.], [1., 0., 0.], [.5, .5, 1.]])
    # When adjacency exclusion is applied.
    points = intersection_points(a, b)
    # Then it is not a self-intersection candidate.
    assert len(points) == 0


def test_disjoint_triangles_excluded() -> None:
    # Given parallel separated triangles.
    a = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    # When the separated copy is checked.
    points = intersection_points(a, a + [0., 0., 1.])
    # Then there is no intersection.
    assert len(points) == 0


def test_rational_audit_finds_overlap_beyond_shared_edge() -> None:
    # Given coplanar triangles on the same side of their shared edge.
    a = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
    b = np.array([[0., 0., 0.], [2., 0., 0.], [1., .5, 0.]])
    # When exact arithmetic checks the complete intersection polygon.
    beyond, points = audit_contact(a, b)
    # Then the overlap is more than just the shared edge.
    assert beyond
    assert [1., .5, 0.] in points


def test_rational_audit_accepts_normal_shared_diagonal() -> None:
    # Given a square split into two adjacent triangles.
    a = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
    b = np.array([[1., 0., 0.], [1., 1., 0.], [0., 1., 0.]])
    # When exact arithmetic checks its diagonal contact.
    beyond, points = audit_contact(a, b)
    # Then only the shared edge is returned.
    assert not beyond
    assert len(points) == 2

#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic>=2", "pytest"]
# ///
# How to run: install uv, then uv run --with numpy --with scipy --with trimesh --with manifold3d --with pydantic --with pytest -m pytest test_smooth_loft.py (CPU geometry only).
"""Bounded Hermite rounding must change geometry without moving protected edges."""

from __future__ import annotations

import numpy as np
import pytest
import smooth_loft as sl


def fixture_rings():
    """Given a sharp spanwise camber transition with fixed outline."""
    y = np.array([0.0, 1.0, 2.0, 3.0])
    ring = np.array([[0.0, 0.0], [0.5, 0.1], [1.0, 0.0], [0.5, -0.1]])
    rings = np.repeat(ring[None], 4, axis=0)
    rings[2:, [1, 3], 1] += np.array([0.04, 0.08])[:, None]
    return y, rings


def test_rounding_is_actual_bounded_geometry():
    y, rings = fixture_rings()  # Given
    q = np.linspace(0.8, 1.2, 41)
    result = sl.transition(y, rings, 1, 0.2, q)  # When
    before = sl.linear_rings(y, rings, q)
    delta = np.linalg.norm(result - before, axis=2)
    assert 0.001 < delta.max() <= 0.01  # Then


def test_protected_le_te_are_exact():
    y, rings = fixture_rings()  # Given
    q = np.linspace(0.8, 1.2, 41)
    result = sl.transition(y, rings, 1, 0.2, q)  # When
    assert np.array_equal(result[:, [0, 2]], sl.linear_rings(y, rings, q)[:, [0, 2]])


def test_transition_has_matching_endpoint_tangents():
    y, rings = fixture_rings()  # Given
    q = np.array([0.8, 0.800001, 1.199999, 1.2])
    result = sl.transition(y, rings, 1, 0.2, q)  # When
    np.testing.assert_allclose(
        (result[1] - result[0]) / 1e-6, rings[1] - rings[0], atol=1e-6
    )
    np.testing.assert_allclose(
        (result[3] - result[2]) / 1e-6, rings[2] - rings[1], atol=1e-6
    )


def test_invalid_span_or_unbounded_change_is_rejected():
    y, rings = fixture_rings()  # Given
    with pytest.raises(sl.GeometryRejected):  # When / Then
        sl.transition(y, rings, 1, 2.0, np.array([1.0]))


def test_research_smoothing_preserves_outside_and_edges():
    source = sl.Source.model_validate_json(sl.SOURCE.read_text())  # Given
    part = next(p for p in source.parts if p.name == "wing")
    y, rings = np.array(part.stations_m), np.array(part.rings_2d_m)
    result = sl.smooth_wing(y, rings)  # When
    old = sl.linear_rings(y, rings, result.stations)
    assert np.array_equal(result.rings[:, [0, 64]], old[:, [0, 64]])  # Then
    assert max(t.max_displacement_m for t in result.transitions) <= sl.CAP_M
    assert all(
        t.slope_jump_after < t.slope_jump_before * 0.001 for t in result.transitions
    )
    mask = np.ones(len(result.stations), dtype=bool)
    for t in result.transitions:
        mask &= np.abs(result.stations - t.center_m) > t.half_width_m
    assert np.array_equal(result.rings[mask], old[mask])


def test_nonfinite_or_nonincreasing_input_rejected():
    y, rings = fixture_rings()  # Given
    y[2] = y[1]
    with pytest.raises(sl.GeometryRejected):  # When / Then
        sl.smooth_wing(y, rings)


def test_global_cap_rejects_without_clipping():
    y, rings = fixture_rings()  # Given
    rings[:, :, 1] *= 100
    with pytest.raises(sl.GeometryRejected, match="CAP_EXCEEDED"):  # When / Then
        sl.transition(y, rings, 1, 0.2, np.array([1.0]))


def test_existing_output_is_never_overwritten(tmp_path):
    output = tmp_path / "preserved"  # Given
    output.mkdir()
    (output / "marker").write_text("original")
    with pytest.raises(sl.GeometryRejected, match="OUTPUT_EXISTS"):  # When / Then
        sl.generate(output, tmp_path / "evidence.json")
    assert (output / "marker").read_text() == "original"

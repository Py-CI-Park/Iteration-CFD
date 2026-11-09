#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Behavioral contract tests; synthetic curves isolate geometric invariants."""

from pathlib import Path
import numpy as np
import pytest
import curves


def fixture() -> tuple[np.ndarray, np.ndarray]:
    y = np.array([0.0, 1.0, 2.0, 3.0])
    ring = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    return y, np.array([ring + [0.0, z] for z in [0.0, 0.2, 0.05, 0.3]])


def test_station_points_preserved_when_rebuilt() -> None:
    # Given source stations; When a new reconstruction is made; Then original constraints survive float32.
    y, r = fixture()
    result = curves.rebuild(y, r, 0.01)
    assert result.station_error_m < 1e-5


def test_all_trajectories_change_without_station_slope_jumps() -> None:
    # Given a kinked loft; When reconstructed; Then an actual bounded C1 change occurs.
    y, r = fixture()
    result = curves.rebuild(y, r, 0.01)
    assert result.changed_points > 0
    assert result.max_departure_m < 0.01
    assert result.slope_jump_after < result.slope_jump_before * 1e-4


def test_bad_station_order_rejected() -> None:
    # Given invalid station ordering; When reconstructed; Then reject.
    y, r = fixture()
    with pytest.raises(curves.CurveRejected, match="INVALID"):
        curves.rebuild(y[::-1], r, 0.01)


def test_output_no_overwrite_when_existing(tmp_path: Path) -> None:
    # Given an existing candidate; When generation is attempted; Then preserve it.
    import generate

    output = tmp_path / "candidate"
    output.mkdir()
    with pytest.raises(FileExistsError):
        generate.require_fresh(output)

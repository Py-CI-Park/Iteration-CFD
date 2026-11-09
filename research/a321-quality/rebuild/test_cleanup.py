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
"""Controlled cleanup limits and geometric contract gates."""

import pytest
from cleanup import cleanup_tolerance
from curves import CurveRejected


def test_declared_cleanup_tolerance_allowed() -> None:
    # Given declared 1um ceiling; When planned; Then preserve exact parameter.
    assert cleanup_tolerance(1e-6) == 1e-6


@pytest.mark.parametrize("value", [0.0, -1e-6, 1.0001e-6, float("nan"), float("inf")])
def test_undeclared_cleanup_rejected(value: float) -> None:
    # Given invalid or excessive tolerance; When planned; Then refuse.
    with pytest.raises(CurveRejected, match="TOLERANCE"):
        cleanup_tolerance(value)

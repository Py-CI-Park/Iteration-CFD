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
"""Bounded R5-B cleanup; implementation follows executable contract tests."""

from curves import CurveRejected
import math


def cleanup_tolerance(requested_m: float) -> float:
    """Allow only the declared positive cleanup ceiling."""
    if not math.isfinite(requested_m) or not 0 < requested_m <= 1e-6:
        raise CurveRejected("TOLERANCE_OUTSIDE_DECLARED_CEILING")
    return requested_m

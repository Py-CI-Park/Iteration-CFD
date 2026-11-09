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
"""Input contract regressions for the hardened curve boundary."""

import numpy as np
import pytest
from curves import rebuild, CurveRejected


@pytest.mark.parametrize("cap", [float("nan"), float("inf"), 0.0, -0.1, 1e-15])
def test_invalid_or_insufficient_cap_rejected(cap: float) -> None:
    # Given kinked source and invalid/insufficient cap; When rebuilt; Then fail at own boundary.
    y = np.array([0.0, 1.0, 2.0])
    r = np.array(
        [[[0.0, 0.0], [1.0, 0.0]], [[0.0, 1.0], [1.0, 1.0]], [[0.0, 0.0], [1.0, 0.0]]]
    )
    with pytest.raises(CurveRejected):
        rebuild(y, r, cap)


def test_nonfinite_ring_rejected() -> None:
    # Given nonfinite ring input; When rebuilt; Then reject before scipy interpolation.
    y = np.array([0.0, 1.0, 2.0])
    r = np.zeros((3, 2, 2))
    r[1, 0, 0] = float("nan")
    with pytest.raises(CurveRejected):
        rebuild(y, r, 0.01)

# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Planform kink detection (contract 02: LE or TE x(span) slope change > 2.0 deg between adjacent intervals)."""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
KINK_DEG = 2.0


def slope_deg(span: FloatArray, x: FloatArray) -> FloatArray:
    """Planform slope angle (deg) of each station interval, x versus span coordinate."""
    return np.degrees(np.arctan2(np.diff(x), np.diff(span)))


def detect_kinks(span: FloatArray, curves: dict[str, FloatArray], threshold_deg: float = KINK_DEG) -> list[dict]:
    """Stations (indices into span) where any named curve changes slope by more than threshold_deg.

    Returns [{"index", "span_m", "curves": {name: change_deg}}] sorted by index; first/last station never kinks.
    """
    found: dict[int, dict[str, float]] = {}
    for name, x in curves.items():
        angle = slope_deg(span, x)
        change = np.diff(angle)
        for k in np.flatnonzero(np.abs(change) > threshold_deg):
            found.setdefault(int(k) + 1, {})[name] = float(change[k])
    return [{"index": i, "span_m": float(span[i]), "curves": found[i]} for i in sorted(found)]

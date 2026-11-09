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
"""Constrained global station-trajectory reconstruction (not a shader)."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import PchipInterpolator

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class CurveRejected(RuntimeError):
    """A geometry contract failure."""

    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class Curves:
    stations: FloatArray
    rings: FloatArray
    max_departure_m: float
    station_error_m: float
    slope_jump_before: float
    slope_jump_after: float
    changed_points: int


def linear(stations: FloatArray, rings: FloatArray, query: FloatArray) -> FloatArray:
    """Evaluate corresponding original ring trajectories on the straight loft."""
    flat = rings.reshape(len(stations), -1)
    return np.column_stack([np.interp(query, stations, c) for c in flat.T]).reshape(
        len(query), *rings.shape[1:]
    )


def rebuild(
    stations: FloatArray, rings: FloatArray, cap_m: float, subdivisions: int = 4
) -> Curves:
    """Rebuild every corresponding ring-point trajectory with bounded C1 PCHIP.

    Extra controls on the original PL trajectory confine curvature near stations.
    These are not measured sections. No chordwise smoothing is implied.
    """
    if (
        len(stations) < 3
        or not np.isfinite(stations).all()
        or not np.isfinite(rings).all()
        or not np.isfinite(cap_m)
        or np.any(np.diff(stations) <= 0)
        or cap_m <= 0
    ):
        raise CurveRejected("INVALID_STATIONS_OR_CAP")
    slopes = np.diff(rings, axis=0) / np.diff(stations)[:, None, None]
    jumps = np.linalg.norm(np.diff(slopes, axis=0), axis=2)
    before = float(jumps.max())
    # A declared construction parameter, not retrospective gate relaxation.
    shoulder_fraction = 0.02
    controls = np.unique(
        np.concatenate(
            [stations]
            + [
                a + (b - a) * np.array([shoulder_fraction, 1 - shoulder_fraction])
                for a, b in zip(stations[:-1], stations[1:], strict=True)
            ]
        )
    )
    values = linear(stations, rings, controls)
    curve = PchipInterpolator(controls, values, axis=0)
    query = np.unique(
        np.concatenate(
            [controls]
            + [
                np.linspace(a, b, subdivisions + 1)
                for a, b in zip(controls[:-1], controls[1:], strict=True)
            ]
        )
    )
    result = curve(query)
    original = linear(stations, rings, query)
    departure = float(np.linalg.norm(result - original, axis=2).max())
    if departure > cap_m:
        raise CurveRejected("DEPARTURE_EXCEEDS_CAP")
    error = float(
        np.linalg.norm(
            curve(stations).astype(np.float32).astype(float) - rings, axis=2
        ).max()
    )
    # Compare one-sided analytic first derivatives very near each source station.
    eps = np.minimum(np.diff(stations)[:-1], np.diff(stations)[1:]) * 1e-8
    deriv = curve.derivative()
    after = float(
        np.linalg.norm(
            deriv(stations[1:-1] + eps) - deriv(stations[1:-1] - eps), axis=2
        ).max()
    )
    return Curves(
        query,
        result,
        departure,
        error,
        before,
        after,
        int(np.count_nonzero(np.linalg.norm(result - original, axis=2) > 1e-10)),
    )

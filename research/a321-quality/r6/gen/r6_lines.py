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
"""Longitudinal/spanwise grid-line interpolation: C2 cubic unless it overshoots, then Fritsch-Carlson C1.

A grid line is one ring column (all of its coordinates as functions of the station coordinate t).
Lines are split into segments at declared kink stations (C0 there). The method is chosen per
(grid line, segment) and recorded.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

import r6_splines as sp

FloatArray = NDArray[np.float64]
OVERSHOOT_TOL_M = 2e-6  # leaves float32 STL rounding (<= 2e-6 near 20 m) inside the 1e-5 bounds gate


@dataclass(frozen=True)
class SegmentLine:
    """One kink-free segment of all grid lines: stations [a, b] inclusive and both interpolants."""

    a: int
    b: int
    c2: sp.Curve
    fc: sp.Curve
    use_fc: NDArray[np.bool_]  # per grid line (column), True where C2 overshoots (or deviates too far, 02d)
    over: NDArray[np.bool_] | None = None  # per column: C2 overshoot reason
    dev_c2: NDArray[np.float64] | None = None  # per column: max sampled deviation of the C2 curve from the reference (m)
    dev_fc: NDArray[np.float64] | None = None  # per column: same for the FC curve, only where use_fc (NaN elsewhere)


def split_indices(n: int, kinks: list[int]) -> list[tuple[int, int]]:
    """Station index ranges between consecutive kink stations (inclusive ends)."""
    cuts = [0, *sorted(k for k in kinks if 0 < k < n - 1), n - 1]
    return list(zip(cuts[:-1], cuts[1:], strict=True))


def _interior_samples(t: FloatArray, per_interval: int) -> FloatArray:
    u = (np.arange(per_interval) + 0.5) / per_interval
    return np.concatenate([t0 + (t1 - t0) * u for t0, t1 in zip(t[:-1], t[1:], strict=True)])


def build_segments(t: FloatArray, values: FloatArray, kinks: list[int], force: str = "auto",
                   tol: float = OVERSHOOT_TOL_M, deviation=None, dev_limit: float = 0.0,
                   dev_samples: int = 8) -> list[SegmentLine]:
    """values: (n_station, n_col, n_comp). force in {'auto', 'c2', 'fc'} (c2/fc only for diagnostics).

    deviation(tq, points (S, n_col, n_comp)) -> (n_col,) maximum distance to the reference surface (m). With dev_limit > 0
    (contract 02d) a line also takes Fritsch-Carlson when its C2 curve deviates more than dev_limit in any interval.
    """
    n, ncol, ncomp = values.shape
    out = []
    for a, b in split_indices(n, kinks):
        flat = values[a:b + 1].reshape(b - a + 1, ncol * ncomp)
        c2, fc = sp.open_spline(t[a:b + 1], flat), sp.fc_curve(t[a:b + 1], flat)
        over = sp.overshoots(c2, samples_per_interval=24, tol=tol).reshape(ncol, ncomp).any(axis=1)
        use_fc = np.ones(ncol, bool) if force == "fc" else np.zeros(ncol, bool) if force == "c2" else over.copy()
        dev_c2 = dev_fc = None
        if deviation is not None and dev_limit > 0 and b - a >= 2:
            tq = _interior_samples(t[a:b + 1], dev_samples)
            dev_c2 = deviation(tq, sp.evaluate(c2, tq).reshape(-1, ncol, ncomp))
            if force == "auto":
                use_fc = use_fc | (dev_c2 > dev_limit)
            dev_fc = np.full(ncol, np.nan)
            if use_fc.any():
                cols = np.flatnonzero(use_fc)
                pts = sp.evaluate(fc, tq).reshape(-1, ncol, ncomp)[:, cols]
                dev_fc[cols] = deviation(tq, pts)
        out.append(SegmentLine(a, b, c2, fc, use_fc, over, dev_c2, dev_fc))
    return out


def evaluate_lines(segments: list[SegmentLine], tq: FloatArray, ncol: int, ncomp: int) -> FloatArray:
    """(len(tq), ncol, ncomp). A query on a kink station takes the segment on its right (left for the last)."""
    tq = np.asarray(tq, dtype=np.float64)
    out = np.zeros((len(tq), ncol, ncomp))
    for k, seg in enumerate(segments):
        lo, hi = seg.c2.t[0], seg.c2.t[-1]
        last = k == len(segments) - 1
        sel = (tq >= lo) & ((tq <= hi) if last else (tq < hi))
        if not sel.any():
            continue
        v2 = sp.evaluate(seg.c2, tq[sel]).reshape(-1, ncol, ncomp)
        vf = sp.evaluate(seg.fc, tq[sel]).reshape(-1, ncol, ncomp)
        out[sel] = np.where(seg.use_fc[None, :, None], vf, v2)
    return out

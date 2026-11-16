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
"""Station-ring curves for the R6 generator: periodic C2 for the fuselage, TE-corner open C2 for wings and tails.

A ring is N ledger points. Ledger point j keeps ring parameter tau = j. Circumferential refinement inserts
extra points at fractional tau; every ledger point stays a vertex (so station points are reproduced exactly).
The curve parameter is cumulative chord length of the ring polygon, so inserted points sit at the same
fraction of the chord-length gap between the two ledger neighbours at every station (consistent columns).
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

import r6_splines as sp

FloatArray = NDArray[np.float64]


def _plane_axes(axis: int) -> tuple[int, int]:
    return {0: (1, 2), 1: (0, 2), 2: (0, 1)}[axis]


def ring_evaluator(points: FloatArray, axis: int, corner: int | None, mode: str = "auto", tol: float = 2e-6):
    """Return f(tau) -> (len(tau), 3) for one station ring. corner = ring index of a sharp trailing edge or None.

    mode 'auto': C2 curve unless it leaves the range of its two bracketing nodes by more than tol, then
    Fritsch-Carlson C1 for that ring. 'c2' / 'fc' force one (diagnostics). The chosen kind is f.kind.
    """
    n = len(points)
    a, b = _plane_axes(axis)
    plane = points[:, [a, b]]
    if corner is None:
        s = sp.chord_params(plane, closed=True)
        curve = sp.periodic_spline(s[:-1], plane, float(s[-1]))
        if mode == "fc" or (mode == "auto" and sp.overshoots(curve, 16, tol).any()):
            curve = sp.fc_periodic(s[:-1], plane, float(s[-1]))
        knots, total, shift = s[:-1], float(s[-1]), 0
    else:
        order = (np.arange(n + 1) + corner) % n
        s = sp.chord_params(plane[order], closed=False)
        curve = sp.open_spline(s, plane[order])
        if mode == "fc" or (mode == "auto" and sp.overshoots(curve, 16, tol).any()):
            curve = sp.fc_curve(s, plane[order])
        knots, total, shift = s, float(s[-1]), corner

    def evaluate(tau: FloatArray) -> FloatArray:
        tau = np.atleast_1d(np.asarray(tau, dtype=np.float64))
        u = np.mod(tau - shift, n)
        j = np.minimum(np.floor(u).astype(int), n - 1)
        f = u - j
        ends = knots[np.minimum(j + 1, len(knots) - 1)] if corner is not None else np.where(j + 1 < n, knots[np.minimum(j + 1, n - 1)], total)
        tq = knots[j] + f * (ends - knots[j])
        xy = sp.evaluate(curve, tq)
        out = np.zeros((len(tau), 3))
        out[:, a], out[:, b] = xy[:, 0], xy[:, 1]
        out[:, axis] = points[0, axis]
        return out

    evaluate.kind = curve.kind
    return evaluate


def tau_list(n: int, inserted: FloatArray) -> FloatArray:
    """Ring tau values: every ledger index plus inserted[j] equally spaced extra points inside segment j."""
    taus = []
    for j in range(n):
        taus.append(float(j))
        m = int(inserted[j])
        taus.extend(j + np.arange(1, m + 1) / (m + 1))
    return np.asarray(taus)


def turning_deg(poly: FloatArray) -> FloatArray:
    """Turning angle (deg) at every vertex of a closed polyline (n, 3)."""
    e_in = poly - np.roll(poly, 1, axis=0)
    e_out = np.roll(poly, -1, axis=0) - poly
    cos = (e_in * e_out).sum(1) / np.maximum(np.linalg.norm(e_in, axis=1) * np.linalg.norm(e_out, axis=1), 1e-300)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def insertion_counts(rings: FloatArray, axis: int, corner: int | None, limit_deg: float, cap: int = 7,
                     symmetric: bool = False) -> FloatArray:
    """Smallest per-segment insertion counts so the curve polyline turns <= limit_deg at every non-corner vertex.

    rings: (n_station, N, 3). Counts are the maximum over stations. symmetric forces count[j] == count[N-1-j]
    (airfoil upper/lower pairing used by the planar tip caps).
    """
    n_ring = rings.shape[1]
    inserted = np.zeros(n_ring, dtype=int)
    evaluators = [ring_evaluator(r, axis, corner) for r in rings]
    for _ in range(cap + 1):
        taus = tau_list(n_ring, inserted)
        worst = np.zeros(len(taus))
        for ev in evaluators:
            worst = np.maximum(worst, turning_deg(ev(taus)))
        if corner is not None:
            worst[np.flatnonzero(np.isclose(taus, corner))] = 0.0
        bad = np.flatnonzero(worst > limit_deg)
        if len(bad) == 0:
            break
        grow = np.zeros(n_ring, dtype=bool)
        for v in bad:
            seg = int(np.floor(taus[v]))
            grow[seg] = True
            if np.isclose(taus[v], seg):
                grow[(seg - 1) % n_ring] = True
        inserted = np.where(grow, np.minimum(inserted * 2 + 1, cap), inserted)
        if symmetric:
            inserted = np.maximum(inserted, inserted[::-1])
    return inserted

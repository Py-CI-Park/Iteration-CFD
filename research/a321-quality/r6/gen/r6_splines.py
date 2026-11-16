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
"""1-D interpolants for the R6 generator (numpy only, so they also run inside Blender's Python).

* open C2 cubic spline (not-a-knot for n >= 4, parabola for n == 3, line for n == 2),
* periodic C2 cubic spline (cyclic system, one period of knots plus the period length),
* Fritsch-Carlson C1 monotone cubic Hermite (Fritsch and Carlson, SIAM J. Numer. Anal. 17(2),
  238-246, 1980; derived from the paper's constraint alpha^2 + beta^2 <= 9, no code consulted).

Every interpolant is a `Curve`: knots, values (n, k) with k independent components sharing the knots,
and per-node tangent data. `evaluate(curve, t, deriv)` returns (len(t), k).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class Curve:
    """Piecewise cubic through (t, v). kind: 'c2', 'periodic', 'fc'. m holds 2nd derivatives (c2) or tangents (fc)."""

    kind: str
    t: FloatArray
    v: FloatArray
    m: FloatArray
    period: float = 0.0


def _as2d(v: FloatArray) -> FloatArray:
    v = np.asarray(v, dtype=np.float64)
    return v[:, None] if v.ndim == 1 else v


def open_spline(t: FloatArray, v: FloatArray) -> Curve:
    """C2 cubic through every node. not-a-knot for n >= 4, parabola for 3, line for 2."""
    t = np.asarray(t, dtype=np.float64)
    v = _as2d(v)
    n = len(t)
    if n < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("knots must be strictly increasing, n >= 2")
    h = np.diff(t)
    d = np.diff(v, axis=0) / h[:, None]
    if n == 2:
        return Curve("c2", t, v, np.zeros_like(v))
    if n == 3:
        second = 2.0 * (d[1] - d[0]) / (h[0] + h[1])
        return Curve("c2", t, v, np.vstack([second, second, second]))
    a = np.zeros((n, n))
    rhs = np.zeros_like(v)
    for i in range(1, n - 1):
        a[i, i - 1], a[i, i], a[i, i + 1] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
        rhs[i] = 6 * (d[i] - d[i - 1])
    # not-a-knot: third derivative continuous at nodes 1 and n-2
    a[0, 0], a[0, 1], a[0, 2] = h[1], -(h[0] + h[1]), h[0]
    a[n - 1, n - 3], a[n - 1, n - 2], a[n - 1, n - 1] = h[n - 2], -(h[n - 3] + h[n - 2]), h[n - 3]
    return Curve("c2", t, v, np.linalg.solve(a, rhs))


def periodic_spline(t: FloatArray, v: FloatArray, period: float) -> Curve:
    """C2 periodic cubic: knots t[0..n-1] inside one period, value at t[0]+period equals v[0]."""
    t = np.asarray(t, dtype=np.float64)
    v = _as2d(v)
    n = len(t)
    if n < 3 or np.any(np.diff(t) <= 0) or period <= t[-1] - t[0]:
        raise ValueError("need n >= 3 increasing knots inside one period")
    h = np.append(np.diff(t), period - (t[-1] - t[0]))
    ext = np.vstack([v, v[:1]])
    d = np.diff(ext, axis=0) / h[:, None]
    a = np.zeros((n, n))
    rhs = np.zeros_like(v)
    for i in range(n):
        im = (i - 1) % n
        a[i, im] += h[im]
        a[i, i] += 2 * (h[im] + h[i])
        a[i, (i + 1) % n] += h[i]
        rhs[i] = 6 * (d[i] - d[im])
    return Curve("periodic", t, v, np.linalg.solve(a, rhs), period)


def _fc_tangents(t: FloatArray, v: FloatArray) -> FloatArray:
    """Fritsch-Carlson tangents: weighted three-point start, zero at sign changes, alpha^2+beta^2 <= 9 limiter."""
    n = len(t)
    h = np.diff(t)
    d = np.diff(v, axis=0) / h[:, None]
    m = np.zeros_like(v)
    if n == 2:
        m[:] = d[0]
        return m
    m[1:-1] = (h[1:, None] * d[:-1] + h[:-1, None] * d[1:]) / (h[:-1, None] + h[1:, None])
    m[0] = ((2 * h[0] + h[1]) * d[0] - h[0] * d[1]) / (h[0] + h[1])
    m[-1] = ((2 * h[-1] + h[-2]) * d[-1] - h[-1] * d[-2]) / (h[-1] + h[-2])
    for i in range(n):  # tangents must not oppose the adjacent secants
        for j in (i - 1, i):
            if 0 <= j < n - 1:
                m[i] = np.where(m[i] * d[j] < 0, 0.0, m[i])
    for i in range(n - 1):
        flat = d[i] == 0
        safe = np.where(flat, 1.0, d[i])
        alpha, beta = m[i] / safe, m[i + 1] / safe
        norm2 = alpha**2 + beta**2
        over = (norm2 > 9.0) & ~flat
        tau = np.where(over, 3.0 / np.sqrt(np.where(over, norm2, 1.0)), 1.0)
        m[i] = np.where(flat, 0.0, tau * alpha * d[i])
        m[i + 1] = np.where(flat, 0.0, tau * beta * d[i])
    return m


def fc_curve(t: FloatArray, v: FloatArray) -> Curve:
    """C1 shape-preserving (monotone on every interval) cubic Hermite through every node."""
    t = np.asarray(t, dtype=np.float64)
    v = _as2d(v)
    if len(t) < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("knots must be strictly increasing, n >= 2")
    return Curve("fc", t, v, _fc_tangents(t, v))


def fc_periodic(t: FloatArray, v: FloatArray, period: float) -> Curve:
    """Closed-curve variant of fc_curve: tangents use wrapped neighbours (two nodes either side)."""
    t = np.asarray(t, dtype=np.float64)
    v = _as2d(v)
    n = len(t)
    if n < 4 or np.any(np.diff(t) <= 0) or period <= t[-1] - t[0]:
        raise ValueError("need n >= 4 increasing knots inside one period")
    te = np.concatenate([t[-2:] - period, t, t[:2] + period])
    ve = np.vstack([v[-2:], v, v[:2]])
    return Curve("fcp", t, v, _fc_tangents(te, ve)[2:-2], period)


def _is_periodic(curve: Curve) -> bool:
    return curve.kind in ("periodic", "fcp")


def _locate(curve: Curve, tq: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Interval index, interval length and local parameter u in [0,1] for each query."""
    t = curve.t
    if _is_periodic(curve):
        tq = t[0] + np.mod(tq - t[0], curve.period)
        knots = np.append(t, t[0] + curve.period)
    else:
        knots = t
    idx = np.clip(np.searchsorted(knots, tq, side="right") - 1, 0, len(knots) - 2)
    h = knots[idx + 1] - knots[idx]
    return idx, h, (tq - knots[idx]) / h


def evaluate(curve: Curve, tq: FloatArray, deriv: int = 0) -> FloatArray:
    """Value (deriv=0), first or second derivative of the curve at the queries (len(tq), k)."""
    tq = np.atleast_1d(np.asarray(tq, dtype=np.float64))
    idx, h, u = _locate(curve, tq)
    n = len(curve.t)
    j = (idx + 1) % n if _is_periodic(curve) else idx + 1
    vi, vj, mi, mj = curve.v[idx], curve.v[j], curve.m[idx], curve.m[j]
    hh, uu = h[:, None], u[:, None]
    if curve.kind in ("fc", "fcp"):
        h00, h10 = 2 * uu**3 - 3 * uu**2 + 1, uu**3 - 2 * uu**2 + uu
        h01, h11 = -2 * uu**3 + 3 * uu**2, uu**3 - uu**2
        if deriv == 0:
            return h00 * vi + h10 * hh * mi + h01 * vj + h11 * hh * mj
        if deriv == 1:
            return ((6 * uu**2 - 6 * uu) * vi + (3 * uu**2 - 4 * uu + 1) * hh * mi
                    + (-6 * uu**2 + 6 * uu) * vj + (3 * uu**2 - 2 * uu) * hh * mj) / hh
        return ((12 * uu - 6) * vi + (6 * uu - 4) * hh * mi + (-12 * uu + 6) * vj + (6 * uu - 2) * hh * mj) / hh**2
    a, b = 1 - uu, uu
    if deriv == 0:
        return a * vi + b * vj + ((a**3 - a) * mi + (b**3 - b) * mj) * hh**2 / 6
    if deriv == 1:
        return (vj - vi) / hh + ((-(3 * a**2 - 1)) * mi + (3 * b**2 - 1) * mj) * hh / 6
    return a * mi + b * mj


def overshoots(curve: Curve, samples_per_interval: int = 16, tol: float = 1e-4) -> FloatArray:
    """Per component: True if the curve leaves [min,max] of its two bracketing nodes by more than tol anywhere."""
    t = curve.t
    n = len(t)
    flags = np.zeros(curve.v.shape[1], dtype=bool)
    u = (np.arange(1, samples_per_interval) / samples_per_interval)[None, :]
    knots = np.append(t, t[0] + curve.period) if _is_periodic(curve) else t
    count = len(knots) - 1
    tq = (knots[:count, None] + u * np.diff(knots)[:, None]).ravel()
    values = evaluate(curve, tq).reshape(count, -1, curve.v.shape[1])
    lo_node = np.minimum(curve.v, np.roll(curve.v, -1, axis=0))[:count]
    hi_node = np.maximum(curve.v, np.roll(curve.v, -1, axis=0))[:count]
    if not _is_periodic(curve):
        lo_node = np.minimum(curve.v[:-1], curve.v[1:])
        hi_node = np.maximum(curve.v[:-1], curve.v[1:])
    over = (values > hi_node[:, None, :] + tol) | (values < lo_node[:, None, :] - tol)
    return over.any(axis=(0, 1)) | flags


def chord_params(points: FloatArray, closed: bool) -> FloatArray:
    """Cumulative chord length of a polyline; closed adds the closing segment as the last length (n+1 values)."""
    pts = np.asarray(points, dtype=np.float64)
    seg = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]) if closed else pts, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])

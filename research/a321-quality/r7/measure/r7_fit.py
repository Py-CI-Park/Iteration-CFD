# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Least-squares cubic B-spline fits of the traced, normalised profiles w(x), z_c(x), z_b(x) (task 4).

Knot rule under test: equidistribution of the monitor M(x) = (|y''(x)| + eps)^(2/5) (the L2-optimal local rule for
cubic approximation) between the clamped ends, plus optional triple knots (C0) at drawing corners."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import BSpline, make_lsq_spline

from r7_profiles import LENGTH_M, Normalised

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research/a321-quality/r6/gen"))
import r6_splines  # noqa: E402

FloatArray = NDArray[np.float64]
X_LO, X_HI = 0.001, LENGTH_M - 0.001  # fit domain = ledger-style stations 1..180; 1 mm closure bands are lofted linearly (02b)
EPS_CURV = 2e-3  # 1/m, floor of the monitor so flat stretches get long intervals
CORNER_DEG = 4.0


def sample_grid(n: Normalised, step: float = 0.01) -> FloatArray:
    """x samples: uniform step plus the vertices of the traced polylines (dense at the nose, Bezier ends)."""
    xs = [np.arange(0.0, LENGTH_M + 1e-9, step)]
    for br, x0, sx in ((n.raw.top_upper, n.x0_top_pt, n.sx_top), (n.raw.top_lower, n.x0_top_pt, n.sx_top),
                       (n.raw.side_crown, n.x0_side_pt, n.sx_side), (n.raw.side_belly, n.x0_side_pt, n.sx_side)):
        xs.append((br[:, 0] - x0) / sx)
    x = np.unique(np.clip(np.concatenate(xs), 0.0, LENGTH_M))
    return x[np.concatenate([[True], np.diff(x) > 1e-7])]


def profile_samples(n: Normalised, which: str) -> tuple[FloatArray, FloatArray]:
    """(x, y) data samples of one profile; hidden-line gaps are dropped."""
    x = sample_grid(n)
    x = x[(x >= X_LO) & (x <= X_HI)]
    if which == "w":
        return x, n.width(x)
    if which == "zc":
        keep = ~n.in_gap(x, "crown")
        return x[keep], n.crown(x[keep])
    if which == "zb":
        keep = ~n.in_gap(x, "belly")
        return x[keep], n.belly(x[keep])
    raise ValueError(which)


def reference_second_derivative(x: FloatArray, y: FloatArray, xq: FloatArray) -> FloatArray:
    """|y''| from a dense auxiliary spline (smooth enough for a monitor; not used as a result)."""
    nk = 400
    knots_x = np.unique(np.concatenate([np.linspace(x[0], x[-1], nk), x[0] + np.geomspace(1e-3, 2.0, 60), x[-1] - np.geomspace(1e-3, 2.0, 30)]))
    inner = knots_x[(knots_x > x[0] + 1e-9) & (knots_x < x[-1] - 1e-9)]
    # keep every interval populated by data (Schoenberg-Whitney)
    keep = [inner[0]]
    for t in inner[1:]:
        if np.any((x > keep[-1]) & (x < t)):
            keep.append(t)
    t = np.concatenate([[x[0]] * 4, keep, [x[-1]] * 4])
    spl = make_lsq_spline(x, y, t, k=3)
    return np.abs(spl.derivative(2)(xq))


def _metric_polyline(branch_pt: FloatArray, x0: float, sx: float, scale_y: float, min_seg_pt: float = 0.02) -> FloatArray:
    """Traced branch in isotropic metres with sub-0.02 pt joint jitter removed."""
    keep = [0]
    for i in range(1, len(branch_pt)):
        if np.hypot(*(branch_pt[i] - branch_pt[keep[-1]])) >= min_seg_pt:
            keep.append(i)
    b = branch_pt[keep]
    return np.column_stack([(b[:, 0] - x0) / sx, b[:, 1] / scale_y])


def corner_positions(branch_pt: FloatArray, x0: float, sx: float, scale_y: float, deg: float = CORNER_DEG) -> list[dict]:
    """Vertices of the traced polyline where the tangent turns by more than `deg` (isotropic metres)."""
    p = _metric_polyline(branch_pt, x0, sx, scale_y)
    d = np.diff(p, axis=0)
    ang = np.degrees(np.abs(np.arctan2(d[:-1, 0] * d[1:, 1] - d[:-1, 1] * d[1:, 0], (d[:-1] * d[1:]).sum(1))))
    idx = np.where(ang > deg)[0]
    return [{"x_m": float(p[i + 1, 0]), "turn_deg": float(ang[i])} for i in idx]


def straight_run_boundaries(branch_pt: FloatArray, x0: float, sx: float, scale_y: float, min_seg_m: float = 0.5, min_run_m: float = 1.0) -> list[float]:
    """x of the ends of straight stretches (consecutive single drawn segments longer than min_seg_m): curvature jumps from 0 there."""
    p = _metric_polyline(branch_pt, x0, sx, scale_y)
    d = np.diff(p, axis=0)
    long_seg = np.hypot(d[:, 0], d[:, 1]) >= min_seg_m
    out: list[float] = []
    i = 0
    while i < len(long_seg):
        if long_seg[i]:
            j = i
            while j + 1 < len(long_seg) and long_seg[j + 1]:
                j += 1
            if p[j + 1, 0] - p[i, 0] >= min_run_m:
                out.extend([float(p[i, 0]), float(p[j + 1, 0])])
            i = j + 1
        else:
            i += 1
    return sorted(set(round(v, 6) for v in out))


def monitor_knots(x: FloatArray, y: FloatArray, n_int: int, feature_x: tuple[float, ...] = ()) -> FloatArray:
    """Interior knots at equal increments of the cumulative monitor, feature knots reserved first."""
    xq = np.unique(np.concatenate([np.linspace(x[0], x[-1], 20001), x[0] + np.geomspace(1e-5, 1.0, 400), x[-1] - np.geomspace(1e-5, 1.0, 400)]))
    m = (reference_second_derivative(x, y, xq) + EPS_CURV) ** 0.4
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (m[1:] + m[:-1]) * np.diff(xq))])
    cum /= cum[-1]
    n_free = max(n_int - len(feature_x), 1)
    targets = (np.arange(1, n_free + 1)) / (n_free + 1)
    interior = np.interp(targets, cum, xq)
    allk = np.unique(np.concatenate([interior, np.asarray(feature_x, dtype=np.float64)]))
    return allk


def _populated(x: FloatArray, knots: FloatArray) -> FloatArray:
    out: list[float] = []
    prev = x[0]
    for t in knots:
        if np.any((x > prev) & (x < t)):
            out.append(float(t))
            prev = t
    return np.asarray(out)


def fit_lsq(x: FloatArray, y: FloatArray, knots: FloatArray, abscissa: str = "x", c0_at: tuple[float, ...] = ()) -> Callable[[FloatArray], FloatArray]:
    """Clamped cubic LSQ B-spline; abscissa 'sqrt' fits y as a spline of sqrt(x) (nose-adapted); c0_at gets triple knots."""
    tf = (lambda v: np.sqrt(np.maximum(v, 0.0))) if abscissa == "sqrt" else (lambda v: v)
    kx = _populated(x, knots)
    kx = np.array([k for k in kx if all(abs(k - c) > 1e-6 for c in c0_at)])
    inner = np.sort(np.concatenate([tf(kx), np.repeat(tf(np.asarray(c0_at, dtype=np.float64)), 3)])) if len(c0_at) else tf(kx)
    t = np.concatenate([[tf(x[0])] * 4, inner, [tf(x[-1])] * 4])
    spl = make_lsq_spline(tf(x), y, t, k=3)
    return lambda xq: spl(tf(np.asarray(xq, dtype=np.float64)))


def residuals(fit: Callable, x: FloatArray, y: FloatArray, slope_pairs: bool = True) -> dict:
    r = fit(x) - y
    i = int(np.argmax(np.abs(r)))
    out = {"max_abs_m": float(np.abs(r).max()), "x_of_max_m": float(x[i]), "rms_m": float(np.sqrt(np.mean(r**2))),
           "signed_at_max_m": float(r[i])}
    for name, lo, hi in (("x_lt_0.05", 0.0, 0.05), ("x_0.05_1", 0.05, 1.0), ("x_1_to_43", 1.0, 43.0), ("x_gt_43", 43.0, LENGTH_M + 1)):
        m = (x >= lo) & (x < hi)
        if m.any():
            out[f"max_{name}_m"] = float(np.abs(r[m]).max())
    # normal-distance estimate: vertical residual divided by sqrt(1 + slope^2) (slope in m/m, same units on both axes)
    slope = np.gradient(y, x)
    nd = np.abs(r) / np.sqrt(1 + slope**2)
    out["max_normal_dist_m"] = float(nd.max())
    out["max_normal_dist_x_gt_1mm_m"] = float(nd[x > 0.001].max())
    return out


def overshoot(fit: Callable, x: FloatArray, y: FloatArray, knots: FloatArray, tol: float = 5e-4) -> list[dict]:
    """Intervals where the fit leaves the data envelope of the interval by more than tol (m)."""
    edges = np.concatenate([[x[0]], knots, [x[-1]]])
    out = []
    xf = np.unique(np.concatenate([x, np.linspace(x[0], x[-1], 60001)]))
    yf = fit(xf)
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        md = (x >= a) & (x <= b)
        mf = (xf >= a) & (xf <= b)
        if md.sum() < 2:
            continue
        over = max(yf[mf].max() - y[md].max(), y[md].min() - yf[mf].min(), 0.0)
        if over > tol:
            out.append({"x0_m": float(a), "x1_m": float(b), "overshoot_m": float(over)})
    return out


def fc_on_knots(x: FloatArray, y: FloatArray, knots: FloatArray) -> dict:
    """Fritsch-Carlson C1 interpolant through the data at the same knots (02b fallback); residual vs data."""
    kn = np.unique(np.concatenate([[x[0]], _populated(x, knots), [x[-1]]]))
    yk = np.interp(kn, x, y)
    curve = r6_splines.fc_curve(kn, yk)
    fit = lambda xq: r6_splines.evaluate(curve, np.asarray(xq), 0)[:, 0]
    return residuals(fit, x, y)


def extremes(fit: Callable, x: FloatArray, y: FloatArray) -> dict:
    xf = np.linspace(x[0], x[-1], 80001)
    yf = fit(xf)
    return {"fit_max": float(yf.max()), "fit_min": float(yf.min()), "data_max": float(y.max()), "data_min": float(y.min()),
            "overshoot_above_data_max_m": float(max(yf.max() - y.max(), 0.0)), "undershoot_below_data_min_m": float(max(y.min() - yf.min(), 0.0))}

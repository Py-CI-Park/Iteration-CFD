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
"""Ring spacing rule, 02a paper check and tessellation-deviation estimate for the R7 fuselage (tasks 5 and 7).

Everything here is computed from analytic ring POINT coordinates in memory. No mesh connectivity is built, no STL or
OBJ is written, and no flip logic is run: the barrel test and the fuselage are phase B."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from r7_model import X_HI, X_LO, FuselageModel

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class RingRule:
    n_points: int = 128  # per ring, multiple of 4 (vertices at crown, belly, both max-width points)
    delta_long_m: float = 1.0e-3  # allowed longitudinal chord deviation (sagitta) of the meridians
    shape_factor: float = 3.0  # target meridian edge length <= shape_factor x circumferential edge length
    d_max_m: float = 0.6  # absolute cap on the meridian edge length
    growth_gradient: float = 0.18  # |dh/dx| limit -> consecutive spacing ratio about 1.2 (< 1.25)


def _curv(f: FloatArray, x: FloatArray) -> FloatArray:
    d1 = np.gradient(f, x)
    d2 = np.gradient(d1, x)
    return np.abs(d2) / (1.0 + d1**2) ** 1.5


def meridian_curvature(model: FuselageModel, x: FloatArray) -> FloatArray:
    """Largest longitudinal curvature of the crown, belly and half-width meridians (1/m)."""
    xc = np.clip(x, X_LO, X_HI)
    return np.maximum.reduce([_curv(model.crown(xc), xc), _curv(model.belly(xc), xc), _curv(model.width(xc) / 2, xc)])


def meridian_distance(model: FuselageModel, x0: float, x1: np.ndarray) -> np.ndarray:
    """Max over crown/belly/side meridians of the 3-D distance between the ring points at x0 and at each x1."""
    xs = np.array([x0])
    a0, zw0, bu0, _ = model.section(xs)
    zc0, zb0 = model.crown(xs), model.belly(xs)
    a1 = model.section(x1)[0]
    zc1, zb1 = model.crown(np.clip(x1, X_LO, X_HI)), model.belly(np.clip(x1, X_LO, X_HI))
    dx = x1 - x0
    return np.maximum.reduce([np.hypot(dx, zc1 - zc0), np.hypot(dx, zb1 - zb0), np.hypot(dx, a1 - a0)])


def size_function(model: FuselageModel, rule: RingRule, xg: FloatArray) -> FloatArray:
    """Target meridian edge length h(x): curvature, shape and cap limits, then gradient-limited growth."""
    kappa = np.maximum(meridian_curvature(model, xg), 1e-6)
    d_curv = np.sqrt(8.0 * rule.delta_long_m / kappa)
    e_c = model.perimeter(xg) / rule.n_points
    t = np.minimum.reduce([d_curv, rule.shape_factor * e_c, np.full_like(xg, rule.d_max_m)])
    h = t.copy()
    for i in range(1, len(h)):
        h[i] = min(h[i], h[i - 1] + rule.growth_gradient * (xg[i] - xg[i - 1]))
    for i in range(len(h) - 2, -1, -1):
        h[i] = min(h[i], h[i + 1] + rule.growth_gradient * (xg[i + 1] - xg[i]))
    return h


def _march(model: FuselageModel, xg: FloatArray, h: FloatArray, start: float, stop: float, direction: int) -> list[float]:
    """March ring stations from `start` towards `stop` (direction +1/-1) with meridian edge length h(x)."""
    xs = [start]
    while (stop - xs[-1]) * direction > 1e-9:
        x0 = xs[-1]
        target = float(np.interp(x0, xg, h))
        far = x0 + direction * (2.0 * target + 1e-3)
        far = min(far, X_HI) if direction > 0 else max(far, X_LO)
        if meridian_distance(model, x0, np.array([far]))[0] <= target:
            nxt = far
        else:
            lo, hi = x0 + direction * 1e-7, far
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if meridian_distance(model, x0, np.array([mid]))[0] <= target:
                    lo = mid
                else:
                    hi = mid
            nxt = lo
        xs.append(nxt)
    return xs


def ring_stations(model: FuselageModel, rule: RingRule, join: tuple[float, float] = (12.0, 28.0)) -> FloatArray:
    """Ring x stations X_LO..X_HI (the 1 mm closure bands outside are lofted per 02b).

    March from the nose to the first ring at or beyond join[0] and from the tail end backwards to the first ring at or
    before join[1]; the plateau between them (constant section, size function equal to its cap) is divided into equal
    steps so the growth ratio stays below 1.25 at both joins."""
    xg = np.unique(np.concatenate([np.linspace(X_LO, X_HI, 44509 + 1), X_LO + np.geomspace(1e-5, 1.0, 300), X_HI - np.geomspace(1e-5, 1.0, 300)]))
    xg = xg[(xg >= X_LO) & (xg <= X_HI)]
    h = size_function(model, rule, xg)
    front = _march(model, xg, h, X_LO, join[0], +1)
    back = _march(model, xg, h, X_HI, join[1], -1)
    x_a, x_b = front[-1], back[-1]
    n_mid = max(int(round((x_b - x_a) / float(np.interp(0.5 * (x_a + x_b), xg, h)))), 1)
    mid = np.linspace(x_a, x_b, n_mid + 1)[1:-1]
    return np.array(front + list(mid) + back[::-1])


def spacing_report(model: FuselageModel, xs: FloatArray) -> dict:
    """x spacing and, as the DPW-IV surface-spacing quantity, the growth ratio of the meridian edge length."""
    dx = np.diff(xs)
    dm = np.array([meridian_distance(model, float(xs[i]), np.array([xs[i + 1]]))[0] for i in range(len(xs) - 1)])
    rm = dm[1:] / dm[:-1]
    rmm = np.maximum(rm, 1 / rm)
    rx = dx[1:] / dx[:-1]
    rxx = np.maximum(rx, 1 / rx)
    return {"n_rings": int(len(xs)), "x_first_m": float(xs[0]), "x_last_m": float(xs[-1]),
            "dx_min_m": float(dx.min()), "dx_max_m": float(dx.max()), "x_at_dx_min_m": float(xs[np.argmin(dx)]),
            "meridian_edge_min_m": float(dm.min()), "meridian_edge_max_m": float(dm.max()),
            "meridian_growth_ratio_max": float(rmm.max()), "meridian_growth_ratio_p99": float(np.percentile(rmm, 99)),
            "meridian_growth_gt_1.25": int((rmm > 1.25).sum()), "x_of_max_meridian_ratio_m": float(xs[1:-1][np.argmax(rmm)]),
            "dx_growth_ratio_max": float(rxx.max()), "dx_growth_note": "dx ratio is larger than the meridian ratio at the nose because the radius grows like sqrt(x); the 1.25 limit is applied to the meridian edge length"}


# ------------------------------------------------------------------------------------------------------ triangles
def _tri_metrics(a: FloatArray, b: FloatArray, c: FloatArray) -> dict[str, FloatArray]:
    ab, bc, ca = np.linalg.norm(b - a, axis=-1), np.linalg.norm(c - b, axis=-1), np.linalg.norm(a - c, axis=-1)
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=-1)
    longest = np.maximum.reduce([ab, bc, ca])
    r_circ = ab * bc * ca / np.maximum(4.0 * area, 1e-300)
    q = 4.0 * area / (3.0 * np.sqrt(3.0) * np.maximum(r_circ, 1e-300) ** 2)

    def ang(p: FloatArray, q_: FloatArray, r: FloatArray) -> FloatArray:
        u, v = q_ - p, r - p
        cos = (u * v).sum(-1) / np.maximum(np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1), 1e-300)
        return np.degrees(np.arccos(np.clip(cos, -1, 1)))

    min_angle = np.minimum.reduce([ang(a, b, c), ang(b, c, a), ang(c, a, b)])
    return {"q": q, "min_angle": min_angle, "aspect": longest**2 / np.maximum(2.0 * area, 1e-300), "area": area, "longest": longest, "normal": cross / np.maximum(2 * area, 1e-300)[..., None]}


def _dihedral(n1: FloatArray, n2: FloatArray) -> FloatArray:
    return np.degrees(np.arccos(np.clip((n1 * n2).sum(-1), -1, 1)))


def paper_check(model: FuselageModel, xs: FloatArray, n_points: int) -> dict:
    """Per-quad triangle metrics from ring-point coordinates (quad split along the better diagonal), 02a quantities."""
    rings = np.stack([model.ring(float(x), n_points) for x in xs])  # (R, N, 3)
    b, t = rings[:-1], rings[1:]
    b1, t1 = np.roll(b, -1, axis=1), np.roll(t, -1, axis=1)
    # diagonal A: (b_j, t_{j+1}); diagonal B: (b_{j+1}, t_j)
    tA1, tA2 = _tri_metrics(b, b1, t1), _tri_metrics(b, t1, t)
    tB1, tB2 = _tri_metrics(b, b1, t), _tri_metrics(b1, t1, t)
    scoreA = np.minimum(tA1["min_angle"], tA2["min_angle"])
    scoreB = np.minimum(tB1["min_angle"], tB2["min_angle"])
    useA = scoreA >= scoreB
    pick = lambda k: (np.where(useA, tA1[k], tB1[k]), np.where(useA, tA2[k], tB2[k]))
    q, ma, asp, area, lon = (np.stack(pick(k)) for k in ("q", "min_angle", "aspect", "area", "longest"))  # (2, R-1, N)
    n_a = np.where(useA[..., None], tA1["normal"], tB1["normal"]), np.where(useA[..., None], tA2["normal"], tB2["normal"])

    def p(v: FloatArray, pc: float) -> float:
        return float(np.percentile(v, pc))

    # grading: adjacent triangles = (same quad), (next column), (next ring strip), via area and longest edge
    def pair_ratio(v: FloatArray) -> FloatArray:
        r1 = v[0] / v[1]  # two triangles of one quad
        r2 = v[0] / np.roll(v[0], -1, axis=1)  # neighbouring columns (first triangle)
        r3 = v[1][1:] / v[0][:-1]  # strip i+1 vs strip i (second triangle vs first triangle)
        r4 = v[0][1:] / v[1][:-1]
        return np.concatenate([np.maximum(r, 1 / r).ravel() for r in (r1, r2, r3, r4)])

    ar, er = pair_ratio(area), pair_ratio(lon)
    # dihedral on quad-split edges: diagonal, longitudinal edge, ring edge
    d_diag = _dihedral(n_a[0], n_a[1])
    d_long = _dihedral(np.roll(n_a[0], 1, axis=1), n_a[1])  # approximate adjacency of the strip across a ring-to-ring edge
    d_ring = _dihedral(n_a[1][:-1], n_a[0][1:])
    dih = np.concatenate([d_diag.ravel(), d_long.ravel(), d_ring.ravel()])
    ring_turn = []
    for r in rings:
        e = np.roll(r, -1, axis=0) - r
        e2 = np.roll(e, -1, axis=0)
        cosv = (e * e2).sum(1) / (np.linalg.norm(e, axis=1) * np.linalg.norm(e2, axis=1))
        ring_turn.append(np.degrees(np.arccos(np.clip(cosv, -1, 1))).max())
    # leaning strips (02c): triangles (b_j, t_{j+s}, t_{j+2s}) and (b_j, t_{j+2s}, b_{j+s}); s = +-1 chosen per strip by the larger min angle
    lean_q, lean_ma, lean_asp = [], [], []
    for i in range(len(b)):
        best = None
        for sgn in (1, -1):
            ts1, ts2, bs1 = np.roll(t[i], -sgn, axis=0), np.roll(t[i], -2 * sgn, axis=0), np.roll(b[i], -sgn, axis=0)
            m1, m2 = _tri_metrics(b[i], ts1, ts2), _tri_metrics(b[i], ts2, bs1)
            score = min(m1["min_angle"].min(), m2["min_angle"].min())
            if best is None or score > best[0]:
                best = (score, m1, m2)
        _, m1, m2 = best
        lean_q += [m1["q"], m2["q"]]
        lean_ma += [m1["min_angle"], m2["min_angle"]]
        lean_asp += [m1["aspect"], m2["aspect"]]
    lq, lma, lasp = (np.concatenate(v) for v in (lean_q, lean_ma, lean_asp))
    inner = slice(2, -2)
    d_inner = np.concatenate([d_diag[inner].ravel(), d_long[inner].ravel(), d_ring[2:-2].ravel()])
    loc = {"diag": d_diag, "long": d_long}
    kmax = max(loc, key=lambda k: loc[k].max())
    i_max = int(np.unravel_index(np.argmax(loc[kmax]), loc[kmax].shape)[0])
    return {
        "triangles_quad_split": int(2 * q.shape[1] * q.shape[2]),
        "Q_OF": {"min": float(q.min()), "p1": p(q, 1), "median": p(q, 50)},
        "min_angle_deg": {"min": float(ma.min()), "p1": p(ma, 1), "p5": p(ma, 5), "median": p(ma, 50)},
        "aspect": {"max": float(asp.max()), "p99": p(asp, 99), "median": p(asp, 50)},
        "leaning_strip_all_strips": {"Q_OF": {"min": float(lq.min()), "p1": p(lq, 1)}, "min_angle_deg": {"min": float(lma.min()), "p1": p(lma, 1), "p5": p(lma, 5)},
                                     "aspect": {"max": float(lasp.max()), "p99": p(lasp, 99)}},
        "grade_area_ratio": {"max": float(ar.max()), "p99": p(ar, 99)},
        "grade_edge_ratio": {"max": float(er.max()), "p99": p(er, 99)},
        "dihedral_deg": {"max": float(dih.max()), "p99": p(dih, 99), "ring_polygon_turn_max": float(max(ring_turn)),
                         "max_excluding_first_last_2_strips": float(d_inner.max()), "x_of_max_m": float(xs[i_max]), "edge_type_of_max": kmax},
        "worst_quad_min_angle": {"strip": int(np.unravel_index(np.argmin(ma), ma.shape)[1]), "x_m": float(xs[np.unravel_index(np.argmin(ma), ma.shape)[1]]),
                                 "angle_deg": float(ma.min())},
        "note": "per-quad estimate from ring point coordinates; leaning strips and axis-parallel flips are phase B and are not applied; valence of a regular quad-split interior vertex is 6 (flips raise one end by 1)",
    }


# ------------------------------------------------------------------------------------------------ deviation estimate
def ring_sagitta(model: FuselageModel, xs: FloatArray, n_points: int) -> dict:
    """Max distance of ring-polygon chord midpoints from the analytic section (in the section plane), per ring."""
    worst, where = 0.0, 0.0
    per_ring = []
    for x in xs:
        r = model.ring(float(x), n_points)
        mid = 0.5 * (r + np.roll(r, -1, axis=0))
        d = model.signed_distance_estimate(mid)
        per_ring.append(float(np.abs(d).max()))
        if per_ring[-1] > worst:
            worst, where = per_ring[-1], float(x)
    arr = np.array(per_ring)
    return {"max_m": worst, "x_of_max_m": where, "p99_m": float(np.percentile(arr, 99)), "median_m": float(np.median(arr))}


def strip_deviation(model: FuselageModel, xs: FloatArray, n_points: int, stride: int = 1) -> dict:
    """Max distance of points of the quad-split triangles (centroids, diagonal and edge midpoints) from the analytic surface."""
    rings = np.stack([model.ring(float(x), n_points) for x in xs])
    b, t = rings[:-1], rings[1:]
    b1, t1 = np.roll(b, -1, axis=1), np.roll(t, -1, axis=1)
    worst = np.zeros(len(b))
    for (p0, p1, p2) in ((b, b1, t1), (b, t1, t), (b, b1, t), (b1, t1, t)):  # triangles of both diagonals
        pts = [(p0 + p1 + p2) / 3.0, 0.5 * (p0 + p1), 0.5 * (p1 + p2), 0.5 * (p0 + p2)]
        for q in pts:
            d = np.abs(model.signed_distance_estimate(q.reshape(-1, 3))).reshape(q.shape[:2]).max(axis=1)
            worst = np.maximum(worst, d)
    i = int(np.argmax(worst))
    regions = {"x_lt_1": xs[:-1] < 1.0, "x_1_6": (xs[:-1] >= 1.0) & (xs[:-1] < 6.0), "x_6_31": (xs[:-1] >= 6.0) & (xs[:-1] < 31.0),
               "x_31_44": xs[:-1] >= 31.0}
    return {"max_m": float(worst.max()), "x_of_max_m": float(xs[i]), "p99_m": float(np.percentile(worst, 99)), "median_m": float(np.median(worst)),
            "by_region_max_m": {k: float(worst[m].max()) if m.any() else 0.0 for k, m in regions.items()}}

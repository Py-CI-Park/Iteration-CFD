#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree"]
# ///
"""G4R measurements of the R7 fuselage (03a L6, L7) and the information-only comparison with R3.

L6 own-curve deviation, two-sided and dense:
  (a) surface -> analytic: every triangle sampled at the 7 barycentric points of dense_component_deviation.py; the distance
      to the analytic M3+M4 surface is the exact minimum over (x, theta) of |P(x, theta) - p| (vectorised Levenberg-Marquardt
      from the first-order estimate), not F/|grad F|. Samples in the 1 mm closure bands use the linear band loft (ring at
      X_LO scaled to the end ring); samples on the planar caps use |x - x_end|.
  (b) analytic -> surface: the analytic surface sampled at 4 points per ring interval in x and 512 points in angle, exact
      closest point on the triangles (trimesh).
L7 outline bands (per view, every trace sample): top view = half-width silhouette (max |y| per x slice) vs EACH traced edge about
the best-fit centreline; side view = crown / belly silhouette (max / min z per x slice) vs the normalised traced crown / belly.
The hidden-line bridges are reported separately; the closure bands (x < 0.001, x > 44.509) are excluded.

How to run: uv run --no-project r7_dense.py --attempt <dir with fuselage.stl and fuselage.npz> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
import trimesh

import r7_common

r7_common.add_paths()
import r6_io  # noqa: E402
import r7_curves  # noqa: E402
import r7_fit as F  # noqa: E402
from r7_model import X_HI, X_LO, FuselageModel  # noqa: E402

BARY = np.array([[1 / 3, 1 / 3, 1 / 3], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
LIMIT_L6, BAND_TOP, BAND_SIDE = 0.0025, 0.0244, 0.0445
BRIDGES = {"crown": (26.563, 27.162), "belly": (15.703, 24.782)}
CLOSURE_SCALE, LENGTH = 0.03, 44.51


class Analytic:
    """Analytic M3+M4 surface P(x, theta) inside the fit domain, linear band loft outside."""

    def __init__(self, model: FuselageModel, end_rings: dict) -> None:
        self.m = model
        self.end = end_rings  # {"lo": (ring_vertices (N,3) at X_LO, centroid), "hi": ...}

    def point(self, x: np.ndarray, th: np.ndarray) -> np.ndarray:
        a, zw, bu, bl = self.m.section(x)
        c = np.cos(th)
        return np.column_stack([x, a * np.sin(th), zw + np.where(c >= 0, bu, bl) * c])

    def theta_of(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        a, zw, bu, bl = self.m.section(x)
        zz = z - zw
        return np.arctan2(y / a, zz / np.where(zz >= 0, bu, bl))


def exact_distance(an: Analytic, p: np.ndarray, iters: int = 25) -> np.ndarray:
    """min over (x, theta) of |P - p| by vectorised Levenberg-Marquardt; start at x = p_x, theta from the section ellipse."""
    x = np.clip(p[:, 0], X_LO, X_HI)
    th = an.theta_of(x, p[:, 1], p[:, 2])
    lam = np.full(len(p), 1e-6)
    r = an.point(x, th) - p
    cost = (r**2).sum(1)
    hx, ht = 1e-6, 1e-6
    for _ in range(iters):
        jx = (an.point(np.clip(x + hx, X_LO, X_HI), th) - an.point(np.clip(x - hx, X_LO, X_HI), th)) / (np.clip(x + hx, X_LO, X_HI) - np.clip(x - hx, X_LO, X_HI))[:, None]
        jt = (an.point(x, th + ht) - an.point(x, th - ht)) / (2 * ht)
        a11, a12, a22 = (jx * jx).sum(1), (jx * jt).sum(1), (jt * jt).sum(1)
        g1, g2 = (jx * r).sum(1), (jt * r).sum(1)
        d11, d22 = a11 * (1 + lam), a22 * (1 + lam)
        det = d11 * d22 - a12 * a12
        det = np.where(np.abs(det) < 1e-30, 1e-30, det)
        dx, dt = -(d22 * g1 - a12 * g2) / det, -(d11 * g2 - a12 * g1) / det
        xn, tn = np.clip(x + dx, X_LO, X_HI), th + dt
        rn = an.point(xn, tn) - p
        cn = (rn**2).sum(1)
        better = cn < cost
        x, th, r, cost = np.where(better, xn, x), np.where(better, tn, th), np.where(better[:, None], rn, r), np.where(better, cn, cost)
        lam = np.where(better, np.maximum(lam * 0.3, 1e-9), np.minimum(lam * 10, 1e6))
    return np.sqrt(cost)


def band_distance(p: np.ndarray, end_ring: np.ndarray, x_end_full: float, x_closure: float) -> np.ndarray:
    """Distance of samples in a 1 mm closure band to the linear loft between the full ring at x_end_full and its scaled copy at x_closure."""
    c = end_ring.mean(axis=0)
    out = np.empty(len(p))
    ts = np.linspace(0.0, 1.0, 21)
    # loft = union of 21 sections between the rings, each section a polygon of the 128 ring points; sample the loft densely and use a KD query
    from scipy.spatial import cKDTree
    pts = []
    for t in np.linspace(0.0, 1.0, 51):
        s = 1.0 + (CLOSURE_SCALE - 1.0) * t
        q = c + s * (end_ring - c)
        q[:, 0] = x_end_full + (x_closure - x_end_full) * t
        # densify the polygon edges 8x
        q2 = np.vstack([q + (np.roll(q, -1, axis=0) - q) * f for f in np.linspace(0, 1, 9)[:-1]])
        pts.append(q2)
    tree = cKDTree(np.vstack(pts))
    out[:] = tree.query(p)[0]
    return out


def surface_to_analytic(an: Analytic, vertices: np.ndarray, faces: np.ndarray, rings: dict) -> dict:
    tri = vertices[faces]
    samples = np.einsum("bk,nkd->nbd", BARY, tri).reshape(-1, 3)
    d = np.zeros(len(samples))
    x = samples[:, 0]
    mid = (x >= X_LO) & (x <= X_HI)
    cap_lo, cap_hi = (x <= 1e-9), (x >= LENGTH - 1e-5)
    band_lo, band_hi = (x < X_LO) & ~cap_lo, (x > X_HI) & ~cap_hi
    d[mid] = np.concatenate([exact_distance(an, samples[mid][i:i + 200000]) for i in range(0, mid.sum(), 200000)]) if mid.any() else 0.0
    if band_lo.any():
        d[band_lo] = band_distance(samples[band_lo], rings["lo"], X_LO, 0.0)
    if band_hi.any():
        d[band_hi] = band_distance(samples[band_hi], rings["hi"], X_HI, LENGTH)
    d[cap_lo] = np.abs(x[cap_lo] - 0.0)
    d[cap_hi] = np.abs(x[cap_hi] - float(np.float32(LENGTH)))
    j = int(np.argmax(d))
    return {"samples": int(len(samples)), "max_m": float(d[j]), "p99_m": float(np.percentile(d, 99)), "worst_xyz_m": [round(float(v), 4) for v in samples[j]],
            "samples_in_domain": int(mid.sum()), "samples_closure_bands": int(band_lo.sum() + band_hi.sum()), "samples_caps": int(cap_lo.sum() + cap_hi.sum()),
            "max_in_domain_m": float(d[mid].max()) if mid.any() else None, "max_closure_bands_m": float(d[band_lo | band_hi].max()) if (band_lo | band_hi).any() else None,
            "max_caps_m": float(d[cap_lo | cap_hi].max()) if (cap_lo | cap_hi).any() else None, "over_limit_samples": int((d > LIMIT_L6).sum())}


def analytic_to_surface(an: Analytic, mesh: trimesh.Trimesh, stations: np.ndarray, rings: dict, n_theta: int = 512) -> dict:
    xs = []
    for a, b in zip(stations[:-1], stations[1:], strict=True):
        xs.extend(a + (b - a) * np.array([0.0, 0.25, 0.5, 0.75]))
    xs.append(stations[-1])
    xs = np.clip(np.array(xs), X_LO, X_HI)
    th = np.arange(n_theta) * 2 * np.pi / n_theta
    pts = an.point(np.repeat(xs, n_theta), np.tile(th, len(xs)))
    band = []
    for key, x_full, x_cl in (("lo", X_LO, 0.0), ("hi", X_HI, LENGTH)):
        ring = rings[key]
        c = ring.mean(axis=0)
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            q = c + (1.0 + (CLOSURE_SCALE - 1.0) * t) * (ring - c)
            q[:, 0] = x_full + (x_cl - x_full) * t
            band.append(q)
    pts = np.vstack([pts] + band)
    d = np.empty(len(pts))
    for s in range(0, len(pts), 100000):
        _, d[s:s + 100000], _ = trimesh.proximity.closest_point(mesh, pts[s:s + 100000])
    j = int(np.argmax(d))
    return {"samples": int(len(pts)), "max_m": float(d[j]), "p99_m": float(np.percentile(d, 99)), "worst_xyz_m": [round(float(v), 4) for v in pts[j]],
            "x_samples": int(len(xs)), "theta_samples": n_theta, "over_limit_samples": int((d > LIMIT_L6).sum())}


def slice_extents(tri: np.ndarray, xq: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """max |y|, max z, min z of the surface in each plane x = xq (vertices count: slices exactly at a ring pass through its vertices)."""
    xmin, xmax = tri[:, :, 0].min(axis=1), tri[:, :, 0].max(axis=1)
    order = np.argsort(xmin)
    xmin_s = xmin[order]
    ymax, zmax, zmin = np.full(len(xq), np.nan), np.full(len(xq), np.nan), np.full(len(xq), np.nan)
    for k, x0 in enumerate(xq):
        hi = np.searchsorted(xmin_s, x0, side="right")
        cand = order[:hi]
        cand = cand[xmax[cand] >= x0]
        t = tri[cand]
        pts = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = t[:, i], t[:, j]
            da, db = a[:, 0] - x0, b[:, 0] - x0
            cross = (da * db <= 0) & ((da != 0) | (db != 0))
            s = np.where(cross, da / np.where(da - db == 0, 1, da - db), 0.0)
            pts.append(np.where(cross[:, None], a + (b - a) * s[:, None], np.nan)[:, 1:])
        p = np.vstack(pts)
        p = p[~np.isnan(p[:, 0])]
        ymax[k], zmax[k], zmin[k] = np.abs(p[:, 0]).max(), p[:, 1].max(), p[:, 1].min()
    return ymax, zmax, zmin


def outline_bands(tri: np.ndarray) -> dict:
    raw, r3, cs, n = r7_curves.load_normalisation()
    out: dict = {}
    # top view: best-fit centreline shift exactly as r7_consistency.symmetry
    xs_sym = np.linspace(0.05, LENGTH - 0.05, 8892)
    wu, wl = n.half_widths_from_drawn_centreline(xs_sym)
    shift = float((wu - wl).mean() / 2)
    x_top, _ = F.profile_samples(n, "w")
    up_pt, lo_pt = n.top_edges_pt(x_top)
    cl = raw.centreline_y_pt
    t_upper = (cl - up_pt) / n.sy_top - shift
    t_lower = (lo_pt - cl) / n.sy_top + shift
    ymax, _, _ = slice_extents(tri, x_top)
    out["top_view"] = {"band_m": BAND_TOP, "best_fit_centre_shift_m": shift, "samples": int(len(x_top)), "vs_upper_edge_max_m": float(np.abs(ymax - t_upper).max()), "vs_lower_edge_max_m": float(np.abs(ymax - t_lower).max()),
                       "x_of_max_upper_m": float(x_top[np.argmax(np.abs(ymax - t_upper))]), "x_of_max_lower_m": float(x_top[np.argmax(np.abs(ymax - t_lower))])}
    out["top_view"]["max_m"] = max(out["top_view"]["vs_upper_edge_max_m"], out["top_view"]["vs_lower_edge_max_m"])
    drawn_up = (cl - up_pt) / n.sy_top
    drawn_lo = (lo_pt - cl) / n.sy_top
    out["top_view"]["reported_not_gated_vs_drawn_centreline_max_m"] = float(max(np.abs(ymax - drawn_up).max(), np.abs(ymax - drawn_lo).max()))
    for which, label in (("zc", "crown"), ("zb", "belly")):
        x, y = F.profile_samples(n, which)
        _, zmax, zmin = slice_extents(tri, x)
        sil = zmax if which == "zc" else zmin
        dev = np.abs(sil - y)
        lo, hi = BRIDGES[label]
        gap = (x > lo) & (x < hi)
        out.setdefault("side_view", {"band_m": BAND_SIDE})[label] = {"samples": int(len(x)), "max_m": float(dev.max()), "x_of_max_m": float(x[np.argmax(dev)]), "signed_at_max_m": float((sil - y)[np.argmax(dev)])}
    # bridges: traced outline is not drawn there; the candidate follows the fitted curve over a straight-line assumption
    for which, label in (("zc", "crown"), ("zb", "belly")):
        lo, hi = BRIDGES[label]
        xb = np.linspace(lo, hi, 400)
        raw_line = n.crown(xb) if which == "zc" else n.belly(xb)  # the normalised polyline bridges the gap linearly (np.interp)
        _, zmax, zmin = slice_extents(tri, xb)
        sil = zmax if which == "zc" else zmin
        out["side_view"][label + "_bridge_reported_separately"] = {"x_range_m": [lo, hi], "max_deviation_to_straight_bridge_m": float(np.abs(sil - raw_line).max())}
    out["side_view"]["max_m"] = max(out["side_view"]["crown"]["max_m"], out["side_view"]["belly"]["max_m"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-r3", action="store_true")
    args = ap.parse_args()
    t0 = time.perf_counter()
    tri = r6_io.read_stl(args.attempt / "fuselage.stl").astype(np.float64)
    data = np.load(args.attempt / "fuselage.npz")
    vertices, faces, points = data["vertices"], data["faces"], data["points"]
    stations = points[1:-1, 0, 0]
    curves = r7_curves.build_curves()
    model = FuselageModel(curves.w, curves.zc, curves.zb, curves.rho)
    rings = {"lo": model.ring(X_LO, 128), "hi": model.ring(X_HI, 128)}
    an = Analytic(model, rings)
    res: dict = {"stl": str((args.attempt / "fuselage.stl").name), "limit_L6_m": LIMIT_L6}
    mesh = trimesh.Trimesh(vertices=tri.reshape(-1, 3), faces=np.arange(len(tri) * 3).reshape(-1, 3), process=False)
    res["L6_surface_to_analytic"] = surface_to_analytic(an, vertices, faces, rings)
    t1 = time.perf_counter()
    res["L6_analytic_to_surface"] = analytic_to_surface(an, mesh, stations, rings)
    res["L6_max_m"] = max(res["L6_surface_to_analytic"]["max_m"], res["L6_analytic_to_surface"]["max_m"])
    res["L6_pass"] = res["L6_max_m"] <= LIMIT_L6
    t2 = time.perf_counter()
    res["L7"] = outline_bands(tri)
    res["L7_pass"] = bool(res["L7"]["top_view"]["max_m"] <= BAND_TOP and res["L7"]["side_view"]["max_m"] <= BAND_SIDE)
    t3 = time.perf_counter()
    if not args.skip_r3:
        r3 = r6_io.read_stl(r7_common.REPO / "research/a321-integration/artifacts/shell-r3/fuselage.stl").astype(np.float64)
        from r6_mesh import closure_and_orientation, weld
        v3, f3 = weld(r3)
        r3_mesh = trimesh.Trimesh(vertices=r3.reshape(-1, 3), faces=np.arange(len(r3) * 3).reshape(-1, 3), process=False)
        info = {}
        for label, (src_tri, dst_mesh) in (("r7_to_r3", (tri, r3_mesh)), ("r3_to_r7", (r3, mesh))):
            pts = np.einsum("bk,nkd->nbd", BARY, src_tri).reshape(-1, 3)
            d = np.empty(len(pts))
            for s in range(0, len(pts), 200000):
                _, d[s:s + 200000], _ = trimesh.proximity.closest_point(dst_mesh, pts[s:s + 200000])
            j = int(np.argmax(d))
            info[label] = {"samples": int(len(pts)), "max_m": float(d[j]), "p99_m": float(np.percentile(d, 99)), "worst_xyz_m": [round(float(v), 4) for v in pts[j]]}
        vol7 = float(mesh.volume)
        vol3 = float(r3_mesh.volume)
        info.update({"dense_two_sided_max_m": max(info["r7_to_r3"]["max_m"], info["r3_to_r7"]["max_m"]), "volume_r7_m3": vol7, "volume_r3_m3": vol3, "volume_relative_difference": (vol7 - vol3) / vol3,
                     "note": "information only (not gated for the R7 fuselage); the R6 limits were 25 mm and 1 % volume"})
        res["info_vs_r3"] = info
    res["wall_s"] = {"L6a": round(t1 - t0, 1), "L6b": round(t2 - t1, 1), "L7": round(t3 - t2, 1), "total": round(time.perf_counter() - t0, 1)}
    args.out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("L6 max mm", round(res["L6_max_m"] * 1000, 3), "pass", res["L6_pass"], "| L7 top", round(res["L7"]["top_view"]["max_m"] * 1000, 2), "side", round(res["L7"]["side_view"]["max_m"] * 1000, 2), "pass", res["L7_pass"])


if __name__ == "__main__":
    main()

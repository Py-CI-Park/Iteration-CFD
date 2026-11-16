#!/usr/bin/env -S uv run --script
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
"""R7 fuselage curves under contract 03 / 03a: normalisation, locked-knot refit, spurious-extremum check, renormalisation.

Steps (03a L2, L3):
  1. normalisation reproduced from the raw trace with r7_profiles; scales must equal the locked L2 values to 1e-6 relative;
  2. each of w, z_c, z_b refitted (cubic least squares, C2, no C0 knot) with the LOCKED knot vectors read from r7-measure.json;
     the residual maximum must equal the locked value to 1e-6 m;
  3. no spurious extrema: fit extrema (relief >= NOISE_FLOOR_M) with no trace extremum (prominence >= 0.5 mm) of the same
     kind in the same or an adjacent knot interval mark the interval; marked intervals become Fritsch-Carlson C1 Hermite
     pieces on the same knots (values = spline values at the knots, FC tangents of those values); recorded;
  4. renormalisation: w *= 3.95 / max(w), (z - 4.02) *= 4.14 / max(z_c - z_b); each factor must be within [0.9995, 1.0005].
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Callable

sys.dont_write_bytecode = True

import numpy as np
from scipy.interpolate import BSpline, make_lsq_spline
from scipy.optimize import minimize_scalar
from scipy.signal import find_peaks

import r7_common

r7_common.add_paths()
import r6_splines  # noqa: E402
import r7_fit as F  # noqa: E402
import r7_profiles as P  # noqa: E402
import r7_r3 as R  # noqa: E402
import r7_trace_io as T  # noqa: E402

FIT_FLOOR_APPLIED_M = 5.0e-4  # applied reading: a fit extremum counts only when its relief is >= the 0.5 mm floor the contract gives the trace (declared)
FIT_FLOOR_LITERAL_M = 1.0e-6  # literal reading (any fit extremum above float noise): evaluated for information only
TRACE_PROMINENCE_M = 5.0e-4  # 03a L3
MID_Z = 4.02
LOCKED_SCALES = {"top_x": 7.948651, "top_y": 7.955704, "side_x": 7.945896, "side_z": 8.025725}
LOCKED_RESIDUAL_MAX_MM = {"w": 4.6247, "zc": 9.6361, "zb": 2.7167}


@dataclass
class Curves:
    w: Callable
    zc: Callable
    zb: Callable
    rho: float
    record: dict


def _hermite(a: float, b: float, ya: float, yb: float, ma: float, mb: float, x: np.ndarray) -> np.ndarray:
    h = b - a
    s = (x - a) / h
    h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * ya + h10 * h * ma + h01 * yb + h11 * h * mb


class Piecewise:
    """Cubic spline with some knot intervals replaced by Fritsch-Carlson C1 Hermite pieces on the same knots.

    The replaced pieces interpolate the TRACE values at the knots (02b: FC through the data points), tangents from
    Fritsch-Carlson on those knot values. continuous=True keeps the curve C0: the knots at which a replaced run meets a
    spline interval take the SPLINE value there (the trace-minus-spline difference is recorded as `run_end_mismatch`);
    continuous=False uses the trace value at every knot and the curve jumps there (information only)."""

    def __init__(self, spl: BSpline, edges: np.ndarray, replaced: list[int], trace_at_edges: np.ndarray, continuous: bool = True) -> None:
        self.spl, self.edges, self.replaced = spl, edges, sorted(replaced)
        sv = spl(edges)
        rep = set(self.replaced)
        vals = np.array(trace_at_edges, dtype=np.float64)
        self.jumps, self.run_end_mismatch = [], []
        for k in range(1, len(edges) - 1):  # knot k separates interval k-1 and interval k
            if ((k - 1) in rep) != (k in rep):
                self.run_end_mismatch.append({"knot_x_m": float(edges[k]), "trace_minus_spline_m": float(vals[k] - sv[k])})
                if continuous:
                    vals[k] = sv[k]
                else:
                    self.jumps.append({"knot_x_m": float(edges[k]), "jump_m": float(vals[k] - sv[k])})
        for k in (0, len(edges) - 1):  # curve ends: a replaced end interval starts from the spline value
            if (0 if k == 0 else len(edges) - 2) in rep and continuous:
                vals[k] = sv[k]
        self.vals = vals
        self.tan = r6_splines._fc_tangents(edges, vals[:, None])[:, 0] if replaced else None

    def __call__(self, xq) -> np.ndarray:
        x = np.asarray(xq, dtype=np.float64)
        y = self.spl(x)
        for i in self.replaced:
            a, b = self.edges[i], self.edges[i + 1]
            m = (x >= a) & (x <= b)
            if m.any():
                y = np.where(m, _hermite(a, b, self.vals[i], self.vals[i + 1], self.tan[i], self.tan[i + 1], x), y)
        return y


def load_normalisation():
    raw = T.load_raw()
    meta = json.loads((r7_common.R7_MEASURE / "trace-meta.json").read_text(encoding="utf-8"))
    if raw.sha256 != meta["raw_trace_sha256"]:
        raise SystemExit("RAW_TRACE_SHA_MISMATCH")
    r3 = R.load_r3_profile()
    cs = R.constant_section(r3, 1e-3)
    n = P.build_normalisation(raw, cs["crown_z"], cs["belly_z"])
    return raw, r3, cs, n


def lsq_spline(x: np.ndarray, y: np.ndarray, knots: np.ndarray) -> tuple[BSpline, np.ndarray]:
    """Identical to r7_fit.fit_lsq(abscissa='x'): populated knots, clamped cubic LSQ."""
    kx = F._populated(x, knots)
    t = np.concatenate([[x[0]] * 4, kx, [x[-1]] * 4])
    return make_lsq_spline(x, y, t, k=3), kx


def fit_extrema(spl: Callable, dspl: Callable, x_lo: float, x_hi: float, step: float = 1e-3) -> list[dict]:
    """Local extrema of a smooth curve found from sign changes of its derivative at 1 mm spacing, refined, with relief."""
    xg = np.arange(x_lo, x_hi + 0.5 * step, step)
    d = dspl(xg)
    idx = np.where(d[:-1] * d[1:] < 0)[0]
    ext = []
    for i in idx:
        lo, hi = xg[i], xg[i + 1]
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if dspl(np.array([lo]))[0] * dspl(np.array([mid]))[0] <= 0:
                hi = mid
            else:
                lo = mid
        xe = 0.5 * (lo + hi)
        ext.append({"x_m": float(xe), "value": float(spl(np.array([xe]))[0]), "kind": "max" if d[i] > 0 else "min"})
    seq = [float(spl(np.array([x_lo]))[0])] + [e["value"] for e in ext] + [float(spl(np.array([x_hi]))[0])]
    for k, e in enumerate(ext):
        e["relief_m"] = float(min(abs(seq[k + 1] - seq[k]), abs(seq[k + 1] - seq[k + 2])))
    return ext


def trace_extrema(x: np.ndarray, y: np.ndarray, prominence: float = TRACE_PROMINENCE_M) -> list[dict]:
    out = []
    for kind, sig in (("max", y), ("min", -y)):
        pk, props = find_peaks(sig, prominence=prominence)
        out += [{"x_m": float(x[i]), "kind": kind, "prominence_m": float(p)} for i, p in zip(pk, props["prominences"], strict=True)]
    return sorted(out, key=lambda e: e["x_m"])


def spurious_intervals(spl: BSpline, edges: np.ndarray, x: np.ndarray, y: np.ndarray, floor: float) -> tuple[list[int], dict]:
    dspl = spl.derivative(1)
    fe = [e for e in fit_extrema(spl, dspl, edges[0], edges[-1]) if e["relief_m"] >= floor]
    te = trace_extrema(x, y)
    marked: set[int] = set()
    rows = []
    for e in fe:
        j = int(np.clip(np.searchsorted(edges, e["x_m"]) - 1, 0, len(edges) - 2))
        near = [t for t in te if t["kind"] == e["kind"] and edges[max(j - 1, 0)] <= t["x_m"] <= edges[min(j + 2, len(edges) - 1)]]
        rows.append({**e, "interval": j, "knot_interval_m": [float(edges[j]), float(edges[j + 1])], "matched_trace_extremum": bool(near)})
        if not near:
            marked.add(j)
    return sorted(marked), {"fit_extrema_with_relief_ge_floor": rows, "trace_extrema_prominence_ge_0.5mm": te}


def after_check(f: Callable, edges: np.ndarray, x: np.ndarray, y: np.ndarray, floor: float) -> dict:
    """Extrema of the final piecewise curve at 1 mm spacing (sign changes of the sampled differences, flat runs skipped)."""
    xg = np.arange(edges[0], edges[-1] + 5e-4, 1e-3)
    v = f(xg)
    d = np.diff(v)
    d[np.abs(d) < 1e-12] = 0.0
    s = np.sign(d)
    nz = np.flatnonzero(s)
    ext = []
    for a, b in zip(nz[:-1], nz[1:], strict=True):
        if s[a] != s[b]:
            ext.append({"x_m": float(xg[a + 1]), "kind": "max" if s[a] > 0 else "min", "value": float(v[a + 1])})
    seq = [float(v[0])] + [e["value"] for e in ext] + [float(v[-1])]
    for k, e in enumerate(ext):
        e["relief_m"] = float(min(abs(seq[k + 1] - seq[k]), abs(seq[k + 1] - seq[k + 2])))
    te = trace_extrema(x, y)
    rows = []
    for e in ext:
        if e["relief_m"] < floor:
            continue
        j = int(np.clip(np.searchsorted(edges, e["x_m"]) - 1, 0, len(edges) - 2))
        near = [t for t in te if t["kind"] == e["kind"] and edges[max(j - 1, 0)] <= t["x_m"] <= edges[min(j + 2, len(edges) - 1)]]
        rows.append({**e, "matched_trace_extremum": bool(near)})
    unmatched = [r for r in rows if not r["matched_trace_extremum"]]
    sub = trace_extrema(x, y, 1e-5)
    for r in unmatched:  # does the trace itself hold the extremum below the 0.5 mm prominence floor?
        near = [t for t in sub if t["kind"] == r["kind"] and abs(t["x_m"] - r["x_m"]) < 3.0]
        r["trace_has_subthreshold_extremum"] = bool(near)
        r["trace_subthreshold_prominence_m"] = max((t["prominence_m"] for t in near), default=None)
        r["trace_subthreshold_x_m"] = [t["x_m"] for t in near]
    return {"extrema_relief_ge_floor": rows, "unmatched": unmatched}


def replace_until_clean(spl: BSpline, edges: np.ndarray, x: np.ndarray, y: np.ndarray, floor: float, continuous: bool = True) -> dict:
    """First-pass spurious intervals -> FC pieces, then repeat on extrema left at the run ends until none (or nothing to add)."""
    marked, first = spurious_intervals(spl, edges, x, y, floor)
    trace_at_edges = np.interp(edges, x, y)
    pw = Piecewise(spl, edges, marked, trace_at_edges, continuous)
    iterations = [{"iteration": 0, "replaced_intervals": list(marked), "unmatched_after": len(after_check(pw, edges, x, y, floor)["unmatched"])}]
    for it in range(1, 25):
        unmatched = after_check(pw, edges, x, y, floor)["unmatched"]
        if not unmatched:
            break
        add = set()
        for e in unmatched:
            j = int(np.clip(np.searchsorted(edges, e["x_m"]) - 1, 0, len(edges) - 2))
            for cand in (j - 1, j, j + 1) if min(abs(e["x_m"] - edges[j]), abs(e["x_m"] - edges[j + 1])) < 2e-3 else (j,):
                if 0 <= cand < len(edges) - 1 and cand not in marked:
                    add.add(cand)
        if not add:
            break
        marked = sorted(set(marked) | add)
        pw = Piecewise(spl, edges, marked, trace_at_edges, continuous)
        iterations.append({"iteration": it, "replaced_intervals": sorted(add), "unmatched_after": len(after_check(pw, edges, x, y, floor)["unmatched"])})
    return {"marked": marked, "pw": pw, "iterations": iterations, "first_pass": first}


def argmax_refined(f: Callable, lo: float, hi: float) -> tuple[float, float]:
    xg = np.arange(lo, hi + 1e-4, 1e-4)
    i = int(np.argmax(f(xg)))
    a, b = xg[max(i - 1, 0)], xg[min(i + 1, len(xg) - 1)]
    res = minimize_scalar(lambda t: -float(f(np.array([t]))[0]), bounds=(a, b), method="bounded", options={"xatol": 1e-12})
    return float(res.x), float(-res.fun)


def build_curves() -> Curves:
    raw, r3, cs, n = load_normalisation()
    rec: dict = {"raw_trace_sha256": raw.sha256}
    scales = {"top_x": n.sx_top, "top_y": n.sy_top, "side_x": n.sx_side, "side_z": n.sz_side}
    rec["L2_scales"] = {k: {"reproduced": scales[k], "locked": LOCKED_SCALES[k], "relative_diff": abs(scales[k] - LOCKED_SCALES[k]) / LOCKED_SCALES[k]} for k in scales}
    rec["L2_ok"] = all(v["relative_diff"] <= 1e-6 for v in rec["L2_scales"].values())
    rec["z_offset_m"] = n.z_offset
    if not rec["L2_ok"]:
        raise SystemExit("STOP: L2 scales not reproduced: " + json.dumps(rec["L2_scales"]))
    measure = json.loads((r7_common.R7_MEASURE / "r7-measure.json").read_text(encoding="utf-8"))
    rec["r7_measure_sha256"] = r7_common.sha256_file(r7_common.R7_MEASURE / "r7-measure.json")
    fits: dict[str, Callable] = {}
    rec["curves"] = {}
    for which in ("w", "zc", "zb"):
        x, y = F.profile_samples(n, which)
        knots = np.asarray(measure["fits"]["curves"][which]["candidates"]["64"]["knots_m"], dtype=np.float64)
        spl, kx = lsq_spline(x, y, knots)
        ref = F.fit_lsq(x, y, knots, "x")
        locked_max = measure["fits"]["curves"][which]["candidates"]["64"]["residual"]["max_abs_m"]
        resid = float(np.abs(spl(x) - y).max())
        c = {"n_samples": int(len(x)), "locked_knot_count": int(len(knots)), "populated_knot_count": int(len(kx)), "residual_max_m": resid, "locked_residual_max_m": locked_max,
             "residual_diff_m": abs(resid - locked_max), "identical_to_r7_fit_lsq_max_abs_diff_m": float(np.abs(spl(x) - ref(x)).max()), "ok_1e-6": abs(resid - locked_max) <= 1e-6}
        rec["curves"][which] = c
        edges = np.concatenate([[x[0]], kx, [x[-1]]])
        applied = replace_until_clean(spl, edges, x, y, FIT_FLOOR_APPLIED_M)
        literal = replace_until_clean(spl, edges, x, y, FIT_FLOOR_LITERAL_M, continuous=False)
        marked, ex, pw = applied["marked"], applied["first_pass"], applied["pw"]
        c["fc_iterations"] = applied["iterations"]
        c["fc_run_end_mismatch_trace_minus_spline"] = pw.run_end_mismatch
        c["fc_jumps_at_replaced_run_ends"] = pw.jumps
        c["after_replacement"] = after_check(pw, edges, x, y, FIT_FLOOR_APPLIED_M)
        c["literal_reading_information_only"] = {
            "floor_m": FIT_FLOOR_LITERAL_M, "fit_extrema": len(literal["first_pass"]["fit_extrema_with_relief_ge_floor"]),
            "replaced_intervals": [int(i) for i in literal["marked"]], "replaced_x_ranges_m": [[float(edges[i]), float(edges[i + 1])] for i in literal["marked"]],
            "iterations": literal["iterations"], "jumps_at_run_ends_mm": [{"knot_x_m": j["knot_x_m"], "jump_mm": j["jump_m"] * 1000} for j in literal["pw"].jumps],
            "max_abs_jump_mm": max((abs(j["jump_m"]) for j in literal["pw"].jumps), default=0.0) * 1000,
            "unmatched_after": [{k: v for k, v in e.items() if k != "value"} for e in after_check(literal["pw"], edges, x, y, FIT_FLOOR_LITERAL_M)["unmatched"]],
            "note": "FC pieces interpolate the trace at the knots; where a replaced run meets a spline interval the curve jumps by this amount (not used)"}
        c["extrema_check"] = {"applied_fit_floor_m": FIT_FLOOR_APPLIED_M, "trace_prominence_m": TRACE_PROMINENCE_M, "fit_extrema_count": len(ex["fit_extrema_with_relief_ge_floor"]),
                              "unmatched_fit_extrema": [e for e in ex["fit_extrema_with_relief_ge_floor"] if not e["matched_trace_extremum"]], "trace_extrema_count": len(ex["trace_extrema_prominence_ge_0.5mm"]),
                              "fc_replaced_intervals": [{"interval": i, "x_m": [float(edges[i]), float(edges[i + 1])]} for i in marked]}
        c["worker_overshoot_intervals_over_0.5mm"] = measure["fits"]["curves"][which]["candidates"]["64"]["overshoot_intervals_over_0.5mm"]
        # the same list re-examined with the extremum definition: an interval of the worker list is spurious only if it holds an unmatched fit extremum
        c["worker_overshoot_reexamined"] = [{**o, "contains_unmatched_fit_extremum": any(o["x0_m"] - 1e-9 <= e["x_m"] <= o["x1_m"] + 1e-9 for e in c["extrema_check"]["unmatched_fit_extrema"])} for o in c["worker_overshoot_intervals_over_0.5mm"]]
        c["fit_extrema_all"] = ex["fit_extrema_with_relief_ge_floor"]
        c["trace_extrema"] = ex["trace_extrema_prominence_ge_0.5mm"]
        fits[which] = pw
        rec.setdefault("_edges", {})[which] = edges.tolist()
    rec["L3_ok"] = all(c["ok_1e-6"] for c in rec["curves"].values())
    if not rec["L3_ok"]:
        raise SystemExit("STOP: L3 residual maxima not reproduced: " + json.dumps({k: (c["residual_max_m"], c["locked_residual_max_m"]) for k, c in rec["curves"].items()}))
    # renormalisation (03a L3 last item)
    lo, hi = F.X_LO, F.X_HI
    xw, wmax = argmax_refined(fits["w"], lo, hi)
    height = lambda t: fits["zc"](t) - fits["zb"](t)  # noqa: E731
    xh, hmax = argmax_refined(height, lo, hi)
    fw, fz = 3.95 / wmax, 4.14 / hmax
    rec["renormalisation"] = {"w_fit_max_m": wmax, "w_fit_argmax_x_m": xw, "factor_w": fw, "height_fit_max_m": hmax, "height_fit_argmax_x_m": xh, "factor_z": fz,
                              "mid_z_m": MID_Z, "factors_ok": bool(0.9995 <= fw <= 1.0005 and 0.9995 <= fz <= 1.0005)}
    if not rec["renormalisation"]["factors_ok"]:
        raise SystemExit("STOP: renormalisation factor outside [0.9995, 1.0005]: " + json.dumps(rec["renormalisation"]))
    w0, zc0, zb0 = fits["w"], fits["zc"], fits["zb"]
    w = lambda t: np.asarray(w0(t)) * fw  # noqa: E731
    zc = lambda t: MID_Z + (np.asarray(zc0(t)) - MID_Z) * fz  # noqa: E731
    zb = lambda t: MID_Z + (np.asarray(zb0(t)) - MID_Z) * fz  # noqa: E731
    rec["rho_L1"] = 0.499988
    xw2, wmax2 = argmax_refined(w, lo, hi)
    xh2, hmax2 = argmax_refined(lambda t: zc(t) - zb(t), lo, hi)
    rec["after_renormalisation"] = {"w_max_m": wmax2, "w_argmax_x_m": xw2, "height_max_m": hmax2, "height_argmax_x_m": xh2}
    rec.pop("_edges", None)
    return Curves(w, zc, zb, 0.499988, rec)


if __name__ == "__main__":
    c = build_curves()
    brief = {k: v for k, v in c.record.items() if k != "curves"}
    brief["curves"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("fit_extrema_all", "trace_extrema", "worker_overshoot_intervals_over_0.5mm")} for k, v in c.record["curves"].items()}
    print(json.dumps(brief, indent=1)[:12000])

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
"""R7 fuselage attempt generator under contracts 03 / 03a (step 0 passed).

curves (r7_curves: refit with the locked knots, renormalised) -> ring stations (r7_rings rule + forced rings at argmax w and
argmax height, growth <= 1.25) -> 128-point rings (two half-ellipses, L1 rho) -> 1 mm closure bands (ring scaled by the same
0.03 as the step-0 barrels, round caps) -> r7_surface.assemble (02c leaning strips, quad-scope 02d flips with Q margin).

How to run: uv run --no-project r7_fuselage.py --out-dir <new dir>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

import r7_common

r7_common.add_paths()
import r7_curves  # noqa: E402
import r7_rings  # noqa: E402
import r7_surface  # noqa: E402
from r7_model import X_HI, X_LO, FuselageModel  # noqa: E402

CLOSURE_SCALE = 0.03  # same value as the step-0 barrels (barrel-params.json)
BAND_M = 0.001
LENGTH_M = 44.51
N_POINTS = 128
WINDOW = 6  # stations on each side of a forced ring that are re-divided


def _gm(model: FuselageModel, a: float, b: float) -> float:
    return float(r7_rings.meridian_distance(model, a, np.array([b]))[0])


def insert_forced(model: FuselageModel, xs: np.ndarray, forced: list[float]) -> tuple[np.ndarray, list[dict]]:
    """Make every forced x a ring station.

    The nearest base station becomes the forced station (same count). The WINDOW stations on each side are then relaxed
    (Gauss-Seidel, bisection per station) so that every ratio of consecutive MERIDIAN gaps (the quantity the 1.25 limit is
    applied to) keeps the value it had in the base marching; the window ends and the forced station stay fixed."""
    xs = np.array(xs, dtype=np.float64)
    rec = []
    for xf in forced:
        i = int(np.argmin(np.abs(xs - xf)))
        lo, hi = i - WINDOW, i + WINDOW
        if lo < 1 or hi > len(xs) - 2:
            raise SystemExit(f"STOP: forced station {xf} too close to a model end")
        before = xs.copy()
        rho = {k: _gm(model, xs[k], xs[k + 1]) / _gm(model, xs[k - 1], xs[k]) for k in range(lo + 1, hi)}
        xs[i] = xf
        for _ in range(200):
            moved = 0.0
            for k in list(range(lo + 1, i)) + list(range(i + 1, hi)):
                a_, b_ = xs[k - 1] + 1e-9, xs[k + 1] - 1e-9
                for _ in range(50):
                    mid = 0.5 * (a_ + b_)
                    if _gm(model, mid, xs[k + 1]) - rho[k] * _gm(model, xs[k - 1], mid) > 0:
                        a_ = mid
                    else:
                        b_ = mid
                new = 0.5 * (a_ + b_)
                moved = max(moved, abs(new - xs[k]))
                xs[k] = new
            if moved < 1e-10:
                break
        gm = [_gm(model, xs[k], xs[k + 1]) for k in range(lo, hi)]
        ratios = [max(gm[j + 1] / gm[j], gm[j] / gm[j + 1]) for j in range(len(gm) - 1)]
        rec.append({"forced_x_m": xf, "nearest_base_station_m": float(before[i]), "distance_m": float(xf - before[i]), "window_stations_m": [float(xs[lo]), float(xs[hi])],
                    "window_meridian_gap_ratio_max": float(max(ratios)), "max_station_shift_m": float(np.abs(xs - before).max())})
    return xs, rec


def ring_stations_with_forced(model: FuselageModel, forced: list[float]) -> tuple[np.ndarray, dict]:
    rule = r7_rings.RingRule()
    base = r7_rings.ring_stations(model, rule)
    xs, rec = insert_forced(model, base, forced)
    return xs, {"base_stations": int(len(base)), "final_stations": int(len(xs)), "forced": rec, "base_spacing": r7_rings.spacing_report(model, base), "final_spacing": r7_rings.spacing_report(model, xs),
                "rule": rule.__dict__}


def feature_polylines(vertices: np.ndarray, rows: int, cols: int, feature_rows: tuple) -> dict:
    names = {0: "cap_boundary_first", 1: "closure_band_boundary_first", rows - 2: "closure_band_boundary_last", rows - 1: "cap_boundary_last"}
    items = []
    for r in feature_rows:
        ids = list(r * cols + np.arange(cols))
        items.append({"name": names[r], "polyline": vertices[ids + [ids[0]]].tolist()})
    return {"tolerance_m": 1e-4, "origin": "R7 declared feature rings (closure band boundary rings and cap rims)", "features": items}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    curves = r7_curves.build_curves()
    model = FuselageModel(curves.w, curves.zc, curves.zb, curves.rho)
    ar = curves.record["after_renormalisation"]
    forced = sorted([ar["w_argmax_x_m"], ar["height_argmax_x_m"]])
    t1 = time.perf_counter()
    xs, ring_rec = ring_stations_with_forced(model, forced)
    t2 = time.perf_counter()
    rings = [model.ring(float(x), N_POINTS) for x in xs]
    points = np.stack([r7_surface.closure_ring(rings[0], float(xs[0]) - BAND_M, CLOSURE_SCALE)] + rings + [r7_surface.closure_ring(rings[-1], float(xs[-1]) + BAND_M, CLOSURE_SCALE)])
    built = r7_surface.assemble(points)
    v, f = built["vertices"], built["faces"]
    rows, cols = built["manifest"]["rows"], built["manifest"]["columns"]
    np.savez_compressed(args.out_dir / "fuselage.npz", vertices=v, faces=f, row=built["row"], col=built["col"], region=built["region"], points=points)
    (args.out_dir / "features-fuselage.json").write_text(json.dumps(feature_polylines(v, rows, cols, built["feature_rows"])), encoding="utf-8")
    lo, hi = v.min(axis=0), v.max(axis=0)
    stations = {"parts": [{"name": "fuselage", "axis": 0, "stations_m": [float(s) for s in points[:, 0, 0]], "reference_bounds_m": [lo.tolist(), hi.tolist()]}]}
    (args.out_dir / "stations-fuselage.json").write_text(json.dumps(stations), encoding="utf-8")
    manifest = {"contract": ["r7-geometry-contract-03", "r7-geometry-contract-03a", "r6-geometry-contract-02a", "r6-geometry-contract-02b", "r6-geometry-contract-02c", "r6-geometry-contract-02d"],
                "date_local": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "closure_end_ring_scale": CLOSURE_SCALE, "band_m": BAND_M, "n_points": N_POINTS,
                "curves": curves.record, "rings": ring_rec, "surface": built["manifest"], "bounds_m": [lo.tolist(), hi.tolist()],
                "wall_s": {"curves": round(t1 - t0, 1), "stations": round(t2 - t1, 1), "assemble": round(time.perf_counter() - t2, 1)}}
    (args.out_dir / "feature-manifest.json").write_text(json.dumps(manifest, indent=1, default=float), encoding="utf-8")
    m = built["manifest"]
    print("fuselage rings", rows, "vertices", m["vertices"], "triangles", m["triangles"], "leaning", m["leaning_strips"], "/", m["strips_total"], "flip found/flipped/after",
          m["flip"]["axis_parallel_edges_found"], m["flip"]["flipped"], m["flip"]["axis_parallel_edges_after"], "max valence", m["max_valence"], "volume", round(m["signed_volume_m3"], 4))
    print("growth max (final)", ring_rec["final_spacing"]["meridian_growth_ratio_max"], "stations", ring_rec["base_stations"], "->", ring_rec["final_stations"], "bounds", lo.tolist(), hi.tolist())


if __name__ == "__main__":
    main()

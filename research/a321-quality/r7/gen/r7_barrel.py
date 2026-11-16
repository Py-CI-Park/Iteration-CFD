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
"""Step-0 barrels of contract 03a L9 (B0a constant section, B0b with a 3 m taper to the traced blunt tail).

Free parameters of the barrels that L9 does not fix are declared in `BARREL_PARAMS` and written, with the date, to
barrel-params.json BEFORE any checker runs. They are not changed afterwards to make a barrel pass.

Method (contract 03 M5): leaning-strip tessellation (02c), 02d axis-parallel flip with quad-scope refusal + Q margin
(r7_flip), 02b-style 1 mm closure bands with round caps, no vertex moved after placement, float32-exact vertices.

How to run: uv run --no-project r7_barrel.py --out-dir <new dir>
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
import r6_mesh  # noqa: E402

import r7_surface  # noqa: E402
import r7_rings  # noqa: E402
from r7_model import FuselageModel  # noqa: E402

BARREL_PARAMS = {
    "crown_z_m": 4.02 + 2.07, "belly_z_m": 4.02 - 2.07, "width_m": 3.95, "height_m": 4.14, "rho": 0.499988,
    "n_points": 128, "closure_band_m": 0.001, "closure_end_ring_scale": 0.03,
    "closure_scale_basis": "R3 ledger rings: station 0 / 1 and last-1 / last differ by 0.028-0.031 in half-size (measured, printed in the step-0 log)",
    "cap": "r6_tess.round_cap(final_max=8, inner_radius=0.3) on the closure end ring, orient_cap against the grid",
    "plateau_stations": "committed r7-measure.json stations (proposed_N128_delta1mm.stations_m): the first station >= 12.0 m and the following ones",
    "b0a_length_m": 12.0, "b0b_plateau_length_m": 10.0, "b0b_taper_length_m": 3.0,
    "tail_width_m": 0.405, "tail_height_m": 0.391, "tail_centre_z_m": 5.1125,
    "tail_centre_basis": "R3 ledger tail ring z 4.9242..5.3007 -> centre 5.11245 (rounded to 5.1125)",
    "taper": "crown, belly and width linear in x between the last plateau station and the tail ring; slope break at the joint is a declared C0 knot",
    "taper_ring_spacing": "L4 rule: h = min(sqrt(8 delta/kappa), 3P/128, 0.6), |dh/dx| <= 0.18, marched from the joint; last gap shorter than h/2 absorbed",
    "feature_edges_for_flip": "rings 0, 1, R-2, R-1 (closure end rings and band boundary rings) as closed polylines",
    "tessellation": "r6_tess.lean_triangles over all rows, then r7_flip.flip_axis_parallel",
}


def make_model(kind: str, x_j: float, x_t: float) -> FuselageModel:
    p = BARREL_PARAMS
    tail_zc = p["tail_centre_z_m"]
    tail_crown, tail_belly = tail_zc + p["tail_height_m"] / 2, tail_zc - p["tail_height_m"] / 2

    def lerp(x, v0, v1):
        t = np.clip((np.asarray(x, dtype=np.float64) - x_j) / (x_t - x_j), 0.0, 1.0)
        return v0 + (v1 - v0) * t

    if kind == "B0a":
        return FuselageModel(lambda x: np.full_like(x, p["width_m"], dtype=np.float64), lambda x: np.full_like(x, p["crown_z_m"], dtype=np.float64),
                             lambda x: np.full_like(x, p["belly_z_m"], dtype=np.float64), p["rho"])
    return FuselageModel(lambda x: lerp(x, p["width_m"], p["tail_width_m"]), lambda x: lerp(x, p["crown_z_m"], tail_crown),
                         lambda x: lerp(x, p["belly_z_m"], tail_belly), p["rho"])


def committed_stations() -> np.ndarray:
    data = json.loads((r7_common.R7_MEASURE / "r7-measure.json").read_text(encoding="utf-8"))
    return np.asarray(data["rings"]["proposed_N128_delta1mm"]["stations_m"], dtype=np.float64)


def taper_stations(model: FuselageModel, x_j: float, x_t: float) -> list[float]:
    rule = r7_rings.RingRule()
    xg = np.linspace(x_j, x_t, 3001)
    h = r7_rings.size_function(model, rule, xg)
    xs = [x_j]
    while x_t - xs[-1] > 1e-9:
        x0 = xs[-1]
        target = float(np.interp(x0, xg, h))
        if r7_rings.meridian_distance(model, x0, np.array([x_t]))[0] <= target:
            xs.append(x_t)
            break
        lo, hi = x0 + 1e-9, x_t
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if r7_rings.meridian_distance(model, x0, np.array([mid]))[0] <= target:
                lo = mid
            else:
                hi = mid
        xs.append(lo)
    if len(xs) > 2 and (xs[-1] - xs[-2]) < 0.5 * float(np.interp(xs[-2], xg, h)):
        del xs[-2]
    return xs


def stations_for(kind: str) -> dict:
    p = BARREL_PARAMS
    s = committed_stations()
    x_a = float(s[s >= 12.0][0])
    if kind == "B0a":
        x_b = float(s[s <= x_a + p["b0a_length_m"]][-1])
        plateau = [float(x) for x in s[(s >= x_a) & (s <= x_b)]]
        return {"x_first": x_a, "x_plateau_end": x_b, "x_last": x_b, "plateau": plateau, "taper": [], "model_xj": x_b, "model_xt": x_b + 1.0}
    x_j = float(s[s <= x_a + p["b0b_plateau_length_m"]][-1])
    x_t = x_j + p["b0b_taper_length_m"]
    plateau = [float(x) for x in s[(s >= x_a) & (s <= x_j)]]
    model = make_model("B0b", x_j, x_t)
    taper = taper_stations(model, x_j, x_t)
    return {"x_first": x_a, "x_plateau_end": x_j, "x_last": x_t, "plateau": plateau, "taper": taper[1:], "model_xj": x_j, "model_xt": x_t}


def build(kind: str) -> dict:
    p = BARREL_PARAMS
    st = stations_for(kind)
    model = make_model(kind, st["model_xj"], st["model_xt"])
    xs = st["plateau"] + st["taper"]
    rings = [model.ring(x, p["n_points"]) for x in xs]
    scale, band = p["closure_end_ring_scale"], p["closure_band_m"]
    points = np.stack([r7_surface.closure_ring(rings[0], xs[0] - band, scale)] + rings + [r7_surface.closure_ring(rings[-1], xs[-1] + band, scale)])
    built = r7_surface.assemble(points, st["x_plateau_end"])
    m = built["manifest"]
    m.update({"kind": kind, "plateau_station_count": len(st["plateau"]), "taper_station_count": len(st["taper"]), "x_plateau_end_m": st["x_plateau_end"], "length_between_full_rings_m": xs[-1] - xs[0]})
    return {**built, "points": points}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (args.out_dir / "barrel-params.json").write_text(json.dumps({"frozen_at": stamp, "params": BARREL_PARAMS, "contract": ["r7-geometry-contract-03", "r7-geometry-contract-03a L9"]}, indent=1, ensure_ascii=False), encoding="utf-8")
    manifest = {}
    for kind in ("B0a", "B0b"):
        t0 = time.perf_counter()
        b = build(kind)
        tri = b["vertices"][b["faces"]]
        r6_mesh.write_stl(args.out_dir / f"{kind}.stl", tri)
        np.savez_compressed(args.out_dir / f"{kind}.npz", vertices=b["vertices"], faces=b["faces"], row=b["row"], col=b["col"], region=b["region"], points=b["points"])
        b["manifest"]["wall_s"] = round(time.perf_counter() - t0, 2)
        b["manifest"]["stl_sha256"] = r7_common.sha256_file(args.out_dir / f"{kind}.stl")
        manifest[kind] = b["manifest"]
        m = b["manifest"]
        print(kind, "rings", m["rows"], "vertices", m["vertices"], "triangles", m["triangles"], "leaning strips", m["leaning_strips"], "/", m["strips_total"],
              "axis-parallel edges before/after flip", m["flip"]["axis_parallel_edges_found"], m["flip"]["axis_parallel_edges_after"], "flipped", m["flip"]["flipped"], "volume", round(m["signed_volume_m3"], 4))
    (args.out_dir / "barrel-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

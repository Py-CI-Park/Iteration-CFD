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
# How to run: uv run --no-project run_measure.py --out r7-measure.json   (reads .worktmp/r7-trace/raw-trace.json)
"""R7 fuselage phase A: every number the contract 03a needs, measured on the traced drawing (no PyMuPDF here)."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

import r7_compare
import r7_consistency as C
import r7_embed as E
import r7_fitrun
import r7_model as M
import r7_profiles as P
import r7_r3 as R
import r7_rings as RG
import r7_trace_io as T

HERE = Path(__file__).resolve().parent
COMPONENT_SHA = {"wing.stl": "7577e3ad35c73ca6b86d2f8450e6fa56961fdb38542668333c62fea176f0c252",
                 "horizontal.stl": "21a5a1ee2e0a28c915c21f41d51dff20ae6e3d926d83479d7d6d1f359e4808a1",
                 "vertical.stl": "e6fe6f0f81e34b01c4e28052eda4ec8950ee1f2e57ad6d0d3712edb72a93c890"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outline_bands(cons: dict) -> dict:
    """Per-view outline band from the measured drawing consistency (root-sum-square and linear sum of the components)."""
    sym = cons["symmetry"]["about_best_fit_centreline"]["max_abs_m"] / 2.0  # per-edge error
    sym_drawn = cons["symmetry"]["about_drawn_centreline"]["max_abs_m"] / 2.0
    tip = cons["scales"]["line_uncertainty_m"]["measured_tip_offset_max_m"]
    sc = cons["scales"]
    y_rel = abs(sc["top_view_y"]["scale_from_3.95_tips_pt_per_m"] - sc["top_view_y"]["scale_from_5.75_tips_pt_per_m"]) / sc["top_view_y"]["scale_from_3.95_tips_pt_per_m"]
    top_scale = y_rel * 3.95 / 2.0  # effect on a half-width
    z4, z5 = sc["side_view_z"]["scale_from_4.14_tips_pt_per_m"], sc["side_view_z"]["scale_from_5.87_tips_pt_per_m"]
    side_scale = 4.14 * abs(z4 - z5) / (z4 + z5)  # half the spread of the two printed vertical dimensions, on the full height
    length = abs(cons["length_agreement"]["difference_m_at_top_scale"])
    top = {"components_m": {"left_right_asymmetry_per_edge_best_fit_centre": sym, "tip_to_centreline": tip, "y_scale_spread_3.95_vs_5.75_on_half_width": top_scale,
                            "top_vs_side_length": length},
           "alt_component_asymmetry_about_drawn_centreline_m": sym_drawn}
    top["rss_m"] = float(np.sqrt(sum(v**2 for v in top["components_m"].values())))
    top["linear_sum_m"] = float(sum(top["components_m"].values()))
    side = {"components_m": {"z_scale_spread_4.14_vs_5.87_on_full_height": side_scale, "tip_to_centreline": tip, "top_vs_side_length": length}}
    side["rss_m"] = float(np.sqrt(sum(v**2 for v in side["components_m"].values())))
    side["linear_sum_m"] = float(sum(side["components_m"].values()))
    return {"top_view": top, "side_view": side,
            "rule": "band = root-sum-square of the measured drawing-consistency components (linear sum given as the conservative alternative); fit residual and tessellation deviation are separate gates"}


def ceil_to(v: float, step: float) -> float:
    return float(np.ceil(v / step - 1e-9) * step)


def proposal(cs: dict, norm: dict, fit_report: dict, rings: dict, emb: dict, bands: dict) -> dict:
    """Numbers proposed for contract 03a, each with the measured quantities it is derived from."""
    chosen = str(fit_report["chosen_candidate_interior_knots"])
    cur = fit_report["curves"]
    prop = rings["proposed_N128_delta1mm"]
    dev_max = prop["strip_deviation"]["max_m"]
    res_tail = max(cur["zc"]["candidates"][chosen]["residual_by_region_max_m"]["x_ge_30.3"], cur["zb"]["candidates"][chosen]["residual_by_region_max_m"]["x_ge_30.3"])
    off = max(abs(norm["side_view"]["crown_z_minus_R3_m"]), abs(norm["side_view"]["belly_z_minus_R3_m"]))
    a5_sum = bands["side_view"]["linear_sum_m"] + res_tail + off + dev_max
    depth = {k: v["root_station_R7"]["min_depth_exact_m"] for k, v in emb.items()}
    return {
        "r3_frame": {"crown_z_m": cs["crown_z"], "belly_z_m": cs["belly_z"], "z_w_m": cs["z_w_median"], "rho": cs["rho_median"], "rho_range": [cs["rho_min"], cs["rho_max"]],
                     "constant_section_x_range_m": cs["x_range_m"], "tolerance_m": cs["tol_m"],
                     "basis": "98 R3 stations with crown, belly within 1 mm and width within 2 mm; z_w by a parabola fit to the side points of each ring"},
        "side_profile_z_offset_m": {"offset_to_mid_height_m": norm["side_view"]["z_offset_mid_height_m"], "crown_residual_m": norm["side_view"]["crown_z_minus_R3_m"],
                                    "belly_residual_m": norm["side_view"]["belly_z_minus_R3_m"],
                                    "basis": "z = (y_ref - y_pt)/sz + offset, y_ref = mid of the drawn constant crown/belly lines; offset = R3 mid-height 4.02"},
        "knot_rule": {"interior_knots_per_curve": int(chosen), "rule": fit_report["rule"], "fit_domain_m": fit_report["fit_domain_m"],
                      "crown_extra": "triple (C0) knot at the windshield corner x = 1.395 m reduces the crown maximum residual from "
                                     f"{cur['zc']['candidates'][chosen]['residual']['max_abs_m'] * 1000:.2f} mm to {cur['zc']['variant_c0_knot_at_windshield_' + chosen]['max_abs_m'] * 1000:.2f} mm",
                      "residual_max_mm": {k: cur[k]["candidates"][chosen]["residual"]["max_abs_m"] * 1000 for k in cur},
                      "residual_rms_mm": {k: cur[k]["candidates"][chosen]["residual"]["rms_m"] * 1000 for k in cur}},
        "ring_rule": {**prop["rule"], "rule": "meridian edge length h(x) = min(sqrt(8 delta/kappa), shape_factor x P/N, d_max), gradient-limited |dh/dx| <= growth_gradient; march from both ends, equal steps on the plateau 12-28 m; vertices at crown, both max-width points, belly; equal arc length per quadrant",
                      "n_rings": prop["spacing"]["n_rings"], "triangles_estimate": prop["triangles_estimate"], "meridian_growth_ratio_max": prop["spacing"]["meridian_growth_ratio_max"]},
        "own_curve_deviation_limit_m": {"proposed": ceil_to(1.4 * dev_max, 5e-4), "estimated_max_m": dev_max, "ring_sagitta_max_m": prop["ring_sagitta"]["max_m"],
                                        "basis": "1.4 x the estimated maximum point distance of triangle centroids, diagonal and edge midpoints from the analytic surface, rounded up to 0.5 mm; the estimate samples points, not every point of every triangle"},
        "outline_band_m": {"top_view_rss": bands["top_view"]["rss_m"], "side_view_rss": bands["side_view"]["rss_m"],
                           "top_view_linear_sum": bands["top_view"]["linear_sum_m"], "side_view_linear_sum": bands["side_view"]["linear_sum_m"]},
        "A5_margin_m": {"proposed": ceil_to(a5_sum, 5e-3), "sum_m": a5_sum, "components_m": {"side_band_linear_sum": bands["side_view"]["linear_sum_m"], "fit_residual_x_ge_30.3": res_tail,
                                                                                          "z_offset_vs_R3": off, "tessellation_deviation_estimate": dev_max},
                        "measured_min_depth_m": depth, "depth_over_margin": {k: v / ceil_to(a5_sum, 5e-3) for k, v in depth.items()}},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "r7-measure.json")
    args = ap.parse_args()
    t_start = time.time()
    raw = T.load_raw()
    meta = json.loads((HERE / "trace-meta.json").read_text(encoding="utf-8"))
    if raw.sha256 != meta["raw_trace_sha256"]:
        raise SystemExit("RAW_TRACE_SHA_MISMATCH")
    r3 = R.load_r3_profile()
    cs = R.constant_section(r3, 1e-3)
    cs_tight = R.constant_section(r3, 1e-5)
    n = P.build_normalisation(raw, cs["crown_z"], cs["belly_z"])
    x_dense = np.linspace(0.0, P.LENGTH_M, 44511)
    cons = {"symmetry": C.symmetry(n), "scales": C.scales(n), "length_agreement": C.length_agreement(n), "tail_cap_seen_in_both_views": C.corner_features(n),
            "stroke_vs_fill_agreement_pt": meta["stroke_vs_fill_agreement_pt"]}
    normalisation = {
        "top_view": {"x0_pt": n.x0_top_pt, "x_scale_pt_per_m": n.sx_top, "y_scale_pt_per_m": n.sy_top},
        "side_view": {"x0_pt": n.x0_side_pt, "x_scale_pt_per_m": n.sx_side, "z_scale_pt_per_m": n.sz_side, "crown_const_pt": n.crown_const_pt,
                      "belly_const_pt": n.belly_const_pt, "z_offset_mid_height_m": n.z_offset,
                      "crown_z_const_m": float(n.crown(np.array([15.0]))[0]), "belly_z_const_m": float(n.belly(np.array([15.0]))[0]),
                      "crown_z_minus_R3_m": float(n.crown(np.array([15.0]))[0] - cs["crown_z"]), "belly_z_minus_R3_m": float(n.belly(np.array([15.0]))[0] - cs["belly_z"]),
                      "gaps_pt": {"crown": list(P.CROWN_GAP_PT), "belly": list(P.BELLY_GAP_PT)},
                      "gaps_m": {"crown": [float((v - n.x0_side_pt) / n.sx_side) for v in P.CROWN_GAP_PT], "belly": [float((v - n.x0_side_pt) / n.sx_side) for v in P.BELLY_GAP_PT]}},
        "max_width_m": float(n.width(x_dense).max()), "max_height_m": float((n.crown(x_dense) - n.belly(x_dense)).max()),
        "extremes": {"crown_max_z_m": float(n.crown(x_dense).max()), "crown_max_at_x_m": float(x_dense[np.argmax(n.crown(x_dense))]), "belly_min_z_m": float(n.belly(x_dense).min())},
    }
    t0 = time.time()
    cmp_r3 = r7_compare.compare(n, r3)
    fit_report, fits = r7_fitrun.run(n)
    t_fit = time.time() - t0
    model = M.FuselageModel(fits["w"], fits["zc"], fits["zb"], cs["rho_median"])
    rings: dict = {}
    for tag, rule in {"proposed_N128_delta1mm": RG.RingRule(128, 1.0e-3), "alt_N128_delta2mm": RG.RingRule(128, 2.0e-3), "alt_N96_delta1mm": RG.RingRule(96, 1.0e-3)}.items():
        xs = RG.ring_stations(model, rule)
        rings[tag] = {"rule": rule.__dict__, "spacing": RG.spacing_report(model, xs), "triangles_estimate": int(2 * rule.n_points * (len(xs) - 1)),
                      "paper_check": RG.paper_check(model, xs, rule.n_points), "ring_sagitta": RG.ring_sagitta(model, xs, rule.n_points),
                      "strip_deviation": RG.strip_deviation(model, xs, rule.n_points)}
        if tag == "proposed_N128_delta1mm":
            rings[tag]["stations_m"] = [round(float(v), 5) for v in xs]
    emb: dict = {}
    for name in ("wing", "horizontal", "vertical"):
        ring, pts = E.root_ring(name)
        emb[name] = {"root_station_R7": E.root_station_depth(model, ring), "root_station_R3_fuselage": E.r3_depth(ring),
                     "stations": E.station_profile(model, pts), "junction": E.junction_loops(model, name),
                     "component_sha256": sha(E.CANDIDATE / f"{name}.stl"), "sha_ok": sha(E.CANDIDATE / f"{name}.stl") == COMPONENT_SHA[f"{name}.stl"]}
    bands = outline_bands(cons)
    out = {
        "schema": "r7-measure-v1", "worker": "sonnet-r7-fuselage phase A", "no_surface_generated": True,
        "trace": {"raw_trace_sha256": raw.sha256, "pdf_sha256": meta["pdf_sha256"], "stroke_width_pt": meta["stroke_width_pt_top"], "meta": "trace-meta.json"},
        "r3_constant_section": cs, "r3_constant_section_tight_1e-5": {k: cs_tight[k] for k in ("x_range_m", "n_stations", "rho_median", "rho_min", "rho_max")},
        "normalisation": normalisation, "consistency": cons, "outline_bands": bands, "vs_r3": cmp_r3, "fits": fit_report,
        "rings": rings, "embedment": emb, "proposed_03a": proposal(cs, normalisation, fit_report, rings, emb, bands),
        "wall_s": {"fit_stage": t_fit, "total": time.time() - t_start},
    }
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", args.out, "total s", round(time.time() - t_start, 1))


if __name__ == "__main__":
    main()

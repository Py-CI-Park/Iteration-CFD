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
"""How consistent is the official drawing with itself (task 2 of the R7 measurement brief). All results in metres
after the contract M2 normalisation unless the unit is given."""
from __future__ import annotations

import numpy as np

from r7_profiles import HEIGHT_M, LENGTH_M, WIDTH_M, Normalised

STROKE_PT = 0.4542720317840576


def _pair(tips: list[dict], axis: str, near_a: float, near_b: float, tol: float = 1.0) -> dict:
    for t in tips:
        if t["axis"] == axis and abs(t["tip_a_pt"] - near_a) < tol and abs(t["tip_b_pt"] - near_b) < tol:
            return t
    raise ValueError(f"dimension pair not found near {near_a},{near_b}")


def _stats(d: np.ndarray, x: np.ndarray) -> dict[str, float]:
    i = int(np.argmax(np.abs(d)))
    return {"max_abs_m": float(np.abs(d).max()), "rms_m": float(np.sqrt(np.mean(d**2))), "mean_m": float(d.mean()), "x_of_max_m": float(x[i])}


def symmetry(n: Normalised) -> dict:
    """Left versus right half-width of the top view, about the drawn centre line and about the best-fit centre line."""
    x = np.linspace(0.05, LENGTH_M - 0.05, 8892)
    wu, wl = n.half_widths_from_drawn_centreline(x)
    d = wu - wl  # upper-page edge minus lower-page edge
    out: dict = {"definition": "half-width above the page centre line minus half-width below it; per-edge error = |d|/2",
                 "about_drawn_centreline": _stats(d, x)}
    mean = float(d.mean())
    out["about_best_fit_centreline"] = _stats(d - mean, x)
    out["best_fit_centre_shift_m"] = mean / 2
    regions = {"nose_0_6m": (0.05, 6.0), "constant_6_30m": (6.0, 30.0), "tail_cone_30_44m": (30.0, 44.45)}
    out["by_region_about_best_fit_centreline"] = {k: _stats((d - mean)[(x >= a) & (x <= b)], x[(x >= a) & (x <= b)]) for k, (a, b) in regions.items()}
    out["by_region_about_drawn_centreline"] = {k: _stats(d[(x >= a) & (x <= b)], x[(x >= a) & (x <= b)]) for k, (a, b) in regions.items()}
    xs = np.array([0.05, 0.5, 1.0, 2.0, 4.0, 6.0])
    out["nose_samples"] = {f"x={v:g}": {"wu": float(a), "wl": float(b)} for v, a, b in zip(xs, *n.half_widths_from_drawn_centreline(xs), strict=True)}
    return out


def scales(n: Normalised) -> dict:
    """Scale implied by printed dimensions (arrow tips) versus the view's own outline scale, x and z separately."""
    raw = n.raw
    t_len = _pair(raw.tips74, "H", n.x0_top_pt, n.x0_top_pt + n.sx_top * LENGTH_M, 0.5)
    up_pt = float(raw.top_upper[:, 1].min())
    lo_pt = float(raw.top_lower[:, 1].max())
    t_wid = _pair(raw.tips74, "V", up_pt, lo_pt, 0.5)
    t_hgt = _pair(raw.tips73, "V", n.crown_const_pt, n.belly_const_pt, 0.5)
    t_fin = next(t for t in raw.tips73 if t["axis"] == "V" and abs(t["tip_a_pt"] - 171.51) < 0.5 and abs(t["tip_b_pt"] - 217.66) < 0.5)
    t_engine = next(t for t in raw.tips74 if t["axis"] == "V" and abs(t["tip_a_pt"] - 323.18) < 0.5)
    t_x15 = next(t for t in raw.tips74 if t["axis"] == "H" and abs(t["tip_b_pt"] - 258.79) < 0.5)

    def s(t: dict, value: float) -> float:
        return (t["tip_b_pt"] - t["tip_a_pt"]) / value

    s_top_x_tips = s(t_len, LENGTH_M)
    out = {
        "stroke_width_pt": STROKE_PT,
        "top_view_x": {"scale_from_44.51_tips_pt_per_m": s_top_x_tips, "scale_from_outline_pt_per_m": n.sx_top,
                       "scale_from_15.40_tips_pt_per_m": s(t_x15, 15.40),
                       "outline_length_vs_tips_m": (n.sx_top - s_top_x_tips) * LENGTH_M / s_top_x_tips},
        "top_view_y": {"scale_from_3.95_tips_pt_per_m": s(t_wid, WIDTH_M), "scale_from_outline_width_pt_per_m": n.sy_top,
                       "scale_from_5.75_tips_pt_per_m": s(t_engine, 5.75),
                       "ratio_y_to_x_from_tips": s(t_wid, WIDTH_M) / s_top_x_tips,
                       "ratio_y_to_x_from_outline": n.sy_top / n.sx_top,
                       "width_if_scaled_by_x_scale_m": (n.sy_top * WIDTH_M) / n.sx_top,
                       "width_if_scaled_by_5.75_scale_m": (n.sy_top * WIDTH_M) / s(t_engine, 5.75)},
        "side_view_x": {"scale_from_outline_length_pt_per_m": n.sx_side, "scale_top_view_tips_pt_per_m": s_top_x_tips,
                        "side_length_at_top_view_scale_m": (n.raw.side_crown[-1, 0] - n.x0_side_pt) / s_top_x_tips,
                        "ratio_side_to_top_x_scale": n.sx_side / s_top_x_tips},
        "side_view_z": {"scale_from_4.14_tips_pt_per_m": s(t_hgt, HEIGHT_M), "scale_from_outline_height_pt_per_m": n.sz_side,
                        "scale_from_5.87_tips_pt_per_m": s(t_fin, 5.87), "x_scale_pt_per_m": n.sx_side,
                        "ratio_z4.14_to_x": s(t_hgt, HEIGHT_M) / n.sx_side, "ratio_z5.87_to_x": s(t_fin, 5.87) / n.sx_side,
                        "height_if_scaled_by_x_scale_m": (n.belly_const_pt - n.crown_const_pt) / n.sx_side,
                        "height_if_scaled_by_5.87_scale_m": (n.belly_const_pt - n.crown_const_pt) / s(t_fin, 5.87)},
    }
    # tips versus the stroke centre lines (is the printed dimension measured to the centre or to an edge of the line)
    out["tip_to_centreline_pt"] = {
        "top_width_upper": float(t_wid["tip_a_pt"] - up_pt), "top_width_lower": float(t_wid["tip_b_pt"] - lo_pt),
        "top_length_nose": float(t_len["tip_a_pt"] - n.x0_top_pt), "top_length_tail": float(t_len["tip_b_pt"] - (n.x0_top_pt + n.sx_top * LENGTH_M)),
        "side_height_crown": float(t_hgt["tip_a_pt"] - n.crown_const_pt), "side_height_belly": float(t_hgt["tip_b_pt"] - n.belly_const_pt),
    }
    tip_m = {k: abs(v) / (n.sy_top if "width" in k else n.sz_side if "height" in k else n.sx_top) for k, v in out["tip_to_centreline_pt"].items()}
    out["tip_to_centreline_m"] = tip_m
    out["line_uncertainty_m"] = {"half_stroke_if_edge_referenced_top": 0.5 * STROKE_PT / n.sy_top,
                                 "half_stroke_if_edge_referenced_side_z": 0.5 * STROKE_PT / n.sz_side,
                                 "measured_tip_offset_max_m": float(max(tip_m.values())),
                                 "conclusion": "dimension arrows end on the stroke centre lines within the measured offset; the stroke width does not shift the printed dimension"}
    return out


def length_agreement(n: Normalised) -> dict:
    top_len_pt = n.sx_top * LENGTH_M
    side_len_pt = n.sx_side * LENGTH_M
    return {"top_outline_length_pt": top_len_pt, "side_outline_length_pt": side_len_pt,
            "difference_pt": side_len_pt - top_len_pt, "difference_m_at_top_scale": (side_len_pt - top_len_pt) / n.sx_top,
            "ratio": side_len_pt / top_len_pt,
            "note": "per-view normalisation makes both lengths 44.51 m; the number above is the shift removed by it"}


def corner_features(n: Normalised) -> dict:
    """Tail cap size seen in both views (a physical dimension that both views see)."""
    up_t = n.raw.top_upper[-1]
    lo_t = n.raw.top_lower[-1]
    cr, be = n.raw.side_crown[-1], n.raw.side_belly[-1]
    return {"tail_cap_width_from_top_m": float((lo_t[1] - up_t[1]) / n.sy_top),
            "tail_cap_height_from_side_m": float((be[1] - cr[1]) / n.sz_side),
            "tail_cap_z_range_m": [float(n.z_of_pt(be[1])), float(n.z_of_pt(cr[1]))]}

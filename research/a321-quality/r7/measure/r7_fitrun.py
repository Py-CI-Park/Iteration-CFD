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
"""Run the knot-rule candidates of r7_fit on the three profiles and collect the numbers for the report."""
from __future__ import annotations

from typing import Callable

import numpy as np

import r7_fit as F
from r7_profiles import Normalised

KNOT_COUNTS = (36, 48, 64)
CHOSEN = 64  # candidate used by the ring, embedment and deviation estimates  # interior knots per curve, feature knots included
WINDSHIELD_X = 1.395  # drawing corner of the crown (turn 23 deg), see corners in the output


def sources(n: Normalised) -> dict[str, list]:
    r = n.raw
    return {"w": [(r.top_upper, n.x0_top_pt, n.sx_top, n.sy_top), (r.top_lower, n.x0_top_pt, n.sx_top, n.sy_top)],
            "zc": [(r.side_crown, n.x0_side_pt, n.sx_side, n.sz_side)], "zb": [(r.side_belly, n.x0_side_pt, n.sx_side, n.sz_side)]}


def feature_knots(n: Normalised, which: str, x: np.ndarray) -> list[float]:
    f = sorted({round(v, 3) for br, x0, sx, sc in sources(n)[which] for v in F.straight_run_boundaries(br, x0, sx, sc)})
    return [v for v in f if x[0] < v < x[-1]]


PLATEAU = {"w": (6.0, 32.8), "zc": (7.5, 33.0), "zb": (5.0, 30.5)}  # inside the straight stretches of each curve


def run(n: Normalised) -> tuple[dict, dict[str, Callable]]:
    """Candidates for each profile; returns (report dict, the 48-knot fits used by the model)."""
    report: dict = {"chosen_candidate_interior_knots": CHOSEN, "fit_domain_m": [F.X_LO, F.X_HI], "rule": "interior knots = feature knots (ends of straight stretches >= 1 m) + equidistribution of (|y''|+2e-3)^(2/5)",
                    "corner_threshold_deg": F.CORNER_DEG, "curves": {}}
    chosen: dict[str, Callable] = {}
    for which in ("w", "zc", "zb"):
        x, y = F.profile_samples(n, which)
        feat = feature_knots(n, which, x)
        corners = [c for br, x0, sx, sc in sources(n)[which] for c in F.corner_positions(br, x0, sx, sc, 8.0)]
        entry: dict = {"n_samples": int(len(x)), "feature_knots_m": feat, "drawing_corners_over_8deg": corners, "candidates": {}}
        lo, hi = PLATEAU[which]
        pl = (x >= lo) & (x <= hi)
        for nk in KNOT_COUNTS:
            kn = F.monitor_knots(x, y, nk, tuple(feat))
            fit = F.fit_lsq(x, y, kn, "x")
            res = F.residuals(fit, x, y)
            ext = F.extremes(fit, x, y)
            plateau_fit_minus_data_max = float((fit(x[pl]) - y[pl]).max())
            plateau_data_range = float(np.ptp(y[pl]))
            fc = F.fc_on_knots(x, y, kn)
            entry["candidates"][str(nk)] = {
                "n_interior_knots": int(len(kn)), "knots_m": [round(float(k), 4) for k in kn], "residual": res, "global_extremes": ext,
                "plateau_data_range_m": plateau_data_range, "plateau_fit_minus_data_max_m": plateau_fit_minus_data_max, "plateau_x_range_m": [lo, hi],
                "overshoot_intervals_over_0.5mm": F.overshoot(fit, x, y, kn)[:12], "fc_same_knots_residual": fc,
                "residual_by_region_max_m": {nm: float(np.abs(fit(x[m]) - y[m]).max()) for nm, m in
                                             (("x_lt_6.2", x < 6.2), ("x_6.2_30.3", (x >= 6.2) & (x < 30.34)), ("x_ge_30.3", x >= 30.34))},
            }
            if nk == CHOSEN:
                chosen[which] = fit
        # variants at 48 knots: nose-adapted abscissa and a triple (C0) knot at the crown windshield corner
        knc = F.monitor_knots(x, y, CHOSEN, tuple(feat))
        fs = F.fit_lsq(x, y, knc, "sqrt")
        entry[f"variant_sqrt_abscissa_{CHOSEN}"] = F.residuals(fs, x, y)
        if which == "zc":
            fc0 = F.fit_lsq(x, y, knc, "x", c0_at=(WINDSHIELD_X,))
            entry[f"variant_c0_knot_at_windshield_{CHOSEN}"] = {**F.residuals(fc0, x, y), "c0_at_x_m": WINDSHIELD_X}
            for nk in (36, 48):
                kk = F.monitor_knots(x, y, nk, tuple(feat))
                entry[f"variant_c0_knot_at_windshield_{nk}"] = {**F.residuals(F.fit_lsq(x, y, kk, "x", c0_at=(WINDSHIELD_X,)), x, y), "c0_at_x_m": WINDSHIELD_X}
        report["curves"][which] = entry
    return report, chosen

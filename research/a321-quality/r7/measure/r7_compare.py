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
"""Normalised traced outline versus the R3 ledger fuselage (information only, task 3)."""
from __future__ import annotations

import numpy as np

from r7_profiles import Normalised
from r7_r3 import R3Profile

REGIONS = {
    "nose_0.25_1m": (0.2, 1.0), "nose_1_3m": (1.0, 3.0), "nose_3_6.2m": (3.0, 6.2),
    "constant_6.2_30.3m": (6.2, 30.34), "tail_30.3_35m": (30.34, 35.0), "tail_35_40m": (35.0, 40.0), "tail_40_44.5m": (40.0, 44.52),
    "nose_all_0.2_6.2m": (0.2, 6.2), "tail_all_30.3_44.5m": (30.34, 44.52),
}


def _stats(d: np.ndarray, x: np.ndarray) -> dict[str, float]:
    i = int(np.argmax(np.abs(d)))
    return {"max_abs_m": float(np.abs(d).max()), "x_of_max_m": float(x[i]), "signed_at_max_m": float(d[i]),
            "mean_abs_m": float(np.abs(d).mean()), "mean_signed_m": float(d.mean()), "n_stations": int(len(d))}


def compare(n: Normalised, r3: R3Profile) -> dict:
    x = r3.stations
    keep = (x > 0.2) & (x < 44.5095)
    xs = x[keep]
    diffs = {"width": n.width(xs) - r3.width[keep], "crown": n.crown(xs) - r3.crown[keep], "belly": n.belly(xs) - r3.belly[keep]}
    out: dict = {"definition": "normalised traced outline minus R3 ledger ring extent at the R3 stations (x < 0.2 and the closure station at x = 44.51 excluded)",
                 "regions": {}}
    for name, (lo, hi) in REGIONS.items():
        m = (xs >= lo) & (xs < hi)
        out["regions"][name] = {k: _stats(v[m], xs[m]) for k, v in diffs.items()} if m.any() else {}
    out["overall"] = {k: _stats(v, xs) for k, v in diffs.items()}
    return out

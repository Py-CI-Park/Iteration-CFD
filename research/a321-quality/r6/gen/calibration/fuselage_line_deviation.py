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
"""Per-interval deviation of the fuselage longitudinal lines (C2 and Fritsch-Carlson) from the R3 surface (contract 02d diagnostic).

Dense deterministic sampling along every grid line (8 samples per ledger interval, every column), unlike the random
surface sampling of the gate, so tiny regions such as the nose cone between stations 1 and 2 are covered.

How to run: python fuselage_line_deviation.py --out report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
import r6_dev
import r6_grid
import r6_io
import r6_ledger
import r6_lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--samples", type=int, default=8)
    args = ap.parse_args()
    part = r6_ledger.load_parts()["fuselage"]
    surface = r6_dev.TriangleSurface(r6_io.read_stl(r6_ledger.R3_DIR / "fuselage.stl").astype(np.float64))
    params = r6_grid.GridParams(turn_limit_deg=10.0, aspect_factor=3.0)
    t, rings = r6_grid.full_stations(part)
    taus, plane, kinds, inserted = r6_grid.ring_columns(part, rings, params)
    ncol = plane.shape[1]
    kinks = [1, len(t) - 2]
    out = {}
    for label, force in (("c2", "c2"), ("fc", "fc")):
        seg = [s for s in r6_lines.build_segments(t, plane, kinks, force=force) if s.b - s.a > 1][0]
        tq = r6_lines._interior_samples(t[seg.a:seg.b + 1], args.samples)
        curve = seg.c2 if label == "c2" else seg.fc
        from r6_splines import evaluate
        pts = evaluate(curve, tq).reshape(-1, ncol, 2)
        dev = r6_grid.make_deviation(part, surface)
        per_interval = []
        n_int = seg.b - seg.a
        for k in range(n_int):
            sl = slice(k * args.samples, (k + 1) * args.samples)
            d = dev(tq[sl], pts[sl])
            j = int(np.argmax(d))
            per_interval.append({"interval": [seg.a + k, seg.a + k + 1], "x_from_m": float(t[seg.a + k]), "max_dev_m": float(d.max()), "column": j})
        worst = sorted(per_interval, key=lambda r: -r["max_dev_m"])[:10]
        out[label] = {"max_dev_m": worst[0]["max_dev_m"], "worst_intervals": worst,
                      "intervals_over_20mm": int(sum(r["max_dev_m"] > 0.02 for r in per_interval)),
                      "intervals_over_25mm": int(sum(r["max_dev_m"] > 0.025 for r in per_interval))}
        print(label, json.dumps(out[label]["worst_intervals"][:5]), out[label]["intervals_over_20mm"], out[label]["intervals_over_25mm"])
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

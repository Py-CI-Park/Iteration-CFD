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
"""Side finding: are the R3 ledger fuselage crown and belly exactly flat (z = const over a y-range per ring)?

For every station ring, finds the point(s) of maximum / minimum z and the run of ring points around them whose z equals
that extreme (|dz| <= tol) and reports the y-extent of the run. Also lists all runs of >= 3 consecutive equal-z points.

How to run: python ledger_flat_clips.py --out flat-clips.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r6_ledger


def run_at_extreme(ring: np.ndarray, kind: str, tol: float) -> dict:
    z = ring[:, 2]
    ext = z.max() if kind == "top" else z.min()
    flat = np.abs(z - ext) <= tol
    n = len(z)
    start = int(np.argmax(z) if kind == "top" else np.argmin(z))
    lo = hi = start
    while flat[(lo - 1) % n] and (start - lo) < n - 1:
        lo -= 1
    while flat[(hi + 1) % n] and (hi - start) < n - 1:
        hi += 1
    idx = np.arange(lo, hi + 1) % n
    return {"z_extreme_m": float(ext), "points_at_extreme": int(len(idx)), "y_extent_m": float(ring[idx, 1].max() - ring[idx, 1].min()),
            "y_min_m": float(ring[idx, 1].min()), "y_max_m": float(ring[idx, 1].max())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tol", type=float, default=1e-9, help="z equality tolerance for a flat run (m)")
    args = ap.parse_args()
    part = r6_ledger.load_parts()["fuselage"]
    rows = []
    for i, ring in enumerate(part.points):
        top, bottom = run_at_extreme(ring, "top", args.tol), run_at_extreme(ring, "bottom", args.tol)
        rows.append({"station": i, "x_m": float(part.stations[i]), "top": top, "bottom": bottom})

    def ranges(kind: str) -> list[dict]:
        out, cur = [], None
        for r in rows:
            flat = r[kind]["points_at_extreme"] >= 3
            key = round(r[kind]["z_extreme_m"], 3) if flat else None
            if cur and flat and abs(cur["z_extreme_m"] - r[kind]["z_extreme_m"]) < 5e-3 and r["station"] == cur["station_last"] + 1:
                cur.update(station_last=r["station"], x_last_m=r["x_m"], y_extent_max_m=max(cur["y_extent_max_m"], r[kind]["y_extent_m"]),
                           y_extent_min_m=min(cur["y_extent_min_m"], r[kind]["y_extent_m"]))
            else:
                if cur:
                    out.append(cur)
                cur = {"z_extreme_m": r[kind]["z_extreme_m"], "station_first": r["station"], "station_last": r["station"], "x_first_m": r["x_m"], "x_last_m": r["x_m"],
                       "y_extent_max_m": r[kind]["y_extent_m"], "y_extent_min_m": r[kind]["y_extent_m"]} if flat else None
            del key
        if cur:
            out.append(cur)
        return out

    result = {"tolerance_m": args.tol, "crown_flat_ranges": ranges("top"), "belly_flat_ranges": ranges("bottom"),
              "stations_with_flat_crown": int(sum(r["top"]["points_at_extreme"] >= 3 for r in rows)),
              "stations_with_flat_belly": int(sum(r["bottom"]["points_at_extreme"] >= 3 for r in rows)), "stations": len(rows),
              "per_station": rows}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_station"}, indent=1))


if __name__ == "__main__":
    main()

# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh", "rtree", "scipy"]
# ///
"""Locate the largest candidate-to-reference deviations (G4 between-station) by axial position.

Samples the candidate surface (area weighted), measures the distance to the reference mesh and prints, per axial
bin, the maximum deviation and the point where it occurs. Writes a JSON next to --out.

How to run: uv run locate_deviation.py --candidate f.stl --reference r3-f.stl --out report.json [--samples 200000]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_io


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--samples", type=int, default=200000)
    ap.add_argument("--bin-m", type=float, default=0.5)
    args = ap.parse_args()
    cand = trimesh.Trimesh(*r6_io.weld(r6_io.read_stl(args.candidate)), process=False)
    ref = trimesh.Trimesh(*r6_io.weld(r6_io.read_stl(args.reference)), process=False)
    pts, _ = trimesh.sample.sample_surface(cand, args.samples, seed=7)
    _, dist, _ = trimesh.proximity.closest_point(ref, pts)
    order = np.argsort(-dist)[:10]
    bins = np.floor(pts[:, 0] / args.bin_m).astype(int)
    per_bin = []
    for b in np.unique(bins):
        m = bins == b
        k = np.flatnonzero(m)[np.argmax(dist[m])]
        per_bin.append({"x_from_m": float(b * args.bin_m), "max_dev_m": float(dist[k]), "point_m": pts[k].tolist(), "p99_dev_m": float(np.percentile(dist[m], 99))})
    top = sorted(per_bin, key=lambda r: -r["max_dev_m"])[:8]
    report = {"samples": args.samples, "max_dev_m": float(dist.max()), "top10_points": [{"dev_m": float(dist[i]), "point_m": pts[i].tolist()} for i in order],
              "worst_bins": top, "per_bin": per_bin}
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"max_dev_m": report["max_dev_m"], "top10_points": report["top10_points"][:5], "worst_bins": top[:5]}, indent=1))


if __name__ == "__main__":
    main()

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
"""Where the OpenVSP fuselage (printed-dimension ellipse/ellipsoid rules) differs from the R3 fuselage, binned along x.

Samples every OpenVSP fuselage triangle at 7 barycentric points, exact closest point on the R3 fuselage, bins by x (4 m).
How to run: uv run --no-project ../../r7/openvsp/fuselage_bins.py --out ../../r7/openvsp/fuselage-deviation-bins.json"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BARY = np.array([[1 / 3, 1 / 3, 1 / 3], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5],
                 [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])


def read_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    count = int.from_bytes(raw[80:84], "little")
    dt = np.dtype([("n", "<f4", (3,)), ("t", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(raw, dtype=dt, count=count, offset=84)["t"].astype(np.float64)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    src = read_stl(REPO / ".worktmp/r7-openvsp/openvsp_fuselage.stl")
    ref = read_stl(REPO / "research/a321-integration/artifacts/shell-r3/fuselage.stl")
    pts = np.einsum("bk,nkd->nbd", BARY, src).reshape(-1, 3)
    m = trimesh.Trimesh(vertices=ref.reshape(-1, 3), faces=np.arange(len(ref) * 3).reshape(-1, 3), process=False)
    d = np.empty(len(pts))
    cp = np.empty_like(pts)
    for s in range(0, len(pts), 50000):
        cp[s:s + 50000], d[s:s + 50000], _ = trimesh.proximity.closest_point(m, pts[s:s + 50000])
    bins = np.arange(0.0, 44.51 + 4.0, 4.0)
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        sel = (pts[:, 0] >= lo) & (pts[:, 0] < hi)
        if sel.any():
            j = np.where(sel)[0][np.argmax(d[sel])]
            rows.append({"x_from_m": float(lo), "x_to_m": float(min(hi, 44.51)), "samples": int(sel.sum()), "max_mm": float(d[sel].max() * 1000), "p50_mm": float(np.median(d[sel]) * 1000),
                         "worst_xyz_m": [round(float(v), 3) for v in pts[j]]})
    args.out.write_text(json.dumps({"openvsp_fuselage_to_r3_fuselage": rows}, indent=1), encoding="utf-8")
    for r in rows:
        print(r["x_from_m"], r["x_to_m"], round(r["max_mm"], 1), round(r["p50_mm"], 2), r["worst_xyz_m"])


if __name__ == "__main__":
    main()

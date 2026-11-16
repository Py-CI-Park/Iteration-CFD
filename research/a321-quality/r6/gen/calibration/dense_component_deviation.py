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
"""Dense two-sided deviation of every candidate component from its R3 component (G4 cross-check).

The G4 gate uses a 20000-sample random two-sided max, a lower bound of the Hausdorff distance that
missed the 51.8 mm fuselage nose deviation. This check samples EVERY candidate triangle at 7
barycentric points (centroid, 3 edge midpoints, 3 inner points) and EVERY reference triangle the same way,
and reports the max, p99 and worst location in both directions, with the gate's exact point-triangle query
(trimesh.proximity.closest_point). References are the gate's: R3 fuselage/vertical, and the full-span
wing/horizontal references in <attempt>/refs (R3 starboard half + mirror, y = 0 cap removed).

How to run: python dense_component_deviation.py --attempt <candidate dir> --out report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
import r6_io  # noqa: E402
import r6_ledger  # noqa: E402

LIMITS_M = {"fuselage": 0.025, "wing": 0.010, "horizontal": 0.010, "vertical": 0.010}
BARY = np.array([
    [1 / 3, 1 / 3, 1 / 3],
    [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5],
    [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3],
])


def sample(tri: np.ndarray) -> np.ndarray:
    return np.einsum("bk,nkd->nbd", BARY, tri).reshape(-1, 3)


def one_way(src: np.ndarray, dst: np.ndarray) -> dict:
    pts = sample(src)
    mesh = trimesh.Trimesh(vertices=dst.reshape(-1, 3), faces=np.arange(len(dst) * 3).reshape(-1, 3), process=False)
    d = np.empty(len(pts))
    for s in range(0, len(pts), 200000):
        _, d[s:s + 200000], _ = trimesh.proximity.closest_point(mesh, pts[s:s + 200000])
    j = int(np.argmax(d))
    return {"samples": int(len(pts)), "max_m": float(d[j]), "p99_m": float(np.percentile(d, 99)),
            "worst_xyz_m": [round(float(v), 4) for v in pts[j]],
            "over_limit_samples": None, "_d": d}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = {}
    for name, limit in LIMITS_M.items():
        cand = r6_io.read_stl(args.attempt / f"{name}.stl").astype(np.float64)
        full = args.attempt / "refs" / f"ref-{name}-fullspan.stl"
        ref_path = full if full.exists() else r6_ledger.R3_DIR / f"{name}.stl"
        ref = r6_io.read_stl(ref_path).astype(np.float64)
        row = {"limit_m": limit, "reference": ref_path.name}
        for label, (a, b) in (("candidate_to_r3", (cand, ref)), ("r3_to_candidate", (ref, cand))):
            r = one_way(a, b)
            r["over_limit_samples"] = int((r.pop("_d") > limit).sum())
            row[label] = r
        row["dense_max_m"] = max(row["candidate_to_r3"]["max_m"], row["r3_to_candidate"]["max_m"])
        row["pass"] = row["dense_max_m"] <= limit
        out[name] = row
        print(name, f"dense max {row['dense_max_m'] * 1000:.2f} mm (limit {limit * 1000:.0f} mm)",
              "PASS" if row["pass"] else "FAIL", row["candidate_to_r3"]["worst_xyz_m"], row["r3_to_candidate"]["worst_xyz_m"])
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

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
"""INFORMATION ONLY diagnostics of an R7 fuselage attempt (no gate is judged here; nothing is changed):
  - which triangles fail the 02a per-triangle G5 limits (by region: closure band, leaning strip, other) and G5 without the closure bands;
  - the L6 surface -> analytic deviation split by leaning strips (02c) versus ordinary strips;
  - the G6 ring-edge turning split by x range (nose, mid, plateau, tail);
  - the open end gap of every surfaceBooleanFeatures junction loop.

How to run: uv run --no-project r7_diag.py --attempt <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import r7_common

r7_common.add_paths()
import r6_io  # noqa: E402
import r6_mesh  # noqa: E402
import r6_metrics  # noqa: E402
import r7_curves  # noqa: E402
import r7_dense  # noqa: E402
from r7_model import X_HI, X_LO, FuselageModel  # noqa: E402


def g5_split(v, f, row, region) -> dict:
    q = r6_metrics.triangle_quality(v, f)
    band = np.array([set(region[t]) >= {"band"} for t in f]) | np.all(row[f] >= 0, axis=1) & np.any(np.isin(row[f], [0, row.max()]), axis=1) & ~np.all(row[f] >= 1, axis=1)
    band = np.any(np.isin(row[f], [0, int(row.max())]), axis=1) & np.all(row[f] >= 0, axis=1)
    cap = np.any(row[f] < 0, axis=1)
    out = {"triangles": int(len(f)), "closure_band_triangles": int(band.sum()), "cap_triangles": int(cap.sum())}
    keep = ~band
    for label, m in (("all", np.ones(len(f), bool)), ("without_closure_bands", keep), ("closure_bands_only", band)):
        out[label] = {"q_of_min": float(q["q_of"][m].min()), "min_angle_deg_min": float(q["min_angle_deg"][m].min()), "aspect_max": float(q["aspect"][m].max()),
                      "aspect_p99": float(np.percentile(q["aspect"][m], 99))}
    fail = (q["aspect"] > 100) | (q["min_angle_deg"] < 1.0) | (q["q_of"] < 0.001)
    out["g5_per_triangle_failures"] = {"total": int(fail.sum()), "in_closure_bands": int((fail & band).sum()), "elsewhere": int((fail & ~band).sum())}
    topo, edges = r6_mesh.closure_and_orientation(v, f)
    a, b = edges.face_a, edges.face_b
    inter = (a >= 0) & (b >= 0)
    _, _, area = r6_mesh.face_geometry(v, f)
    ratio = np.maximum(area[a[inter]], area[b[inter]]) / np.minimum(area[a[inter]], area[b[inter]])
    nb = band[a[inter]] | band[b[inter]]
    out["adjacent_area_ratio_max"] = {"all": float(ratio.max()), "without_closure_bands": float(ratio[~nb].max()), "closure_bands": float(ratio[nb].max())}
    return out


def l6_split(att: Path, v, f, row, manifest) -> dict:
    curves = r7_curves.build_curves()
    model = FuselageModel(curves.w, curves.zc, curves.zb, curves.rho)
    an = r7_dense.Analytic(model, {"lo": model.ring(X_LO, 128), "hi": model.ring(X_HI, 128)})
    tri = v[f]
    samples = np.einsum("bk,nkd->nbd", r7_dense.BARY, tri).reshape(-1, 3)
    x = samples[:, 0]
    mid = (x >= X_LO) & (x <= X_HI)
    d = np.zeros(len(samples))
    idx = np.flatnonzero(mid)
    for s in range(0, len(idx), 200000):
        d[idx[s:s + 200000]] = r7_dense.exact_distance(an, samples[idx[s:s + 200000]])
    per_tri = d.reshape(-1, 7).max(axis=1)
    leaning = manifest["surface"]["leaning_strip_rows"]
    rows_f = row[f]
    lean_tri = np.zeros(len(f), bool)
    for s in leaning:
        lean_tri |= np.all((rows_f == s) | (rows_f == s + 1), axis=1) & (rows_f.min(axis=1) >= 0)
    order = np.argsort(-per_tri)[:5]
    return {"leaning_strip_rows": leaning, "leaning_triangles": int(lean_tri.sum()), "max_in_leaning_strips_m": float(per_tri[lean_tri].max()) if lean_tri.any() else None,
            "max_in_ordinary_strips_m": float(per_tri[~lean_tri & mid.reshape(-1, 7).all(axis=1)].max()),
            "worst_5": [{"triangle": int(i), "dev_m": float(per_tri[i]), "centroid_m": [round(float(c), 4) for c in tri[i].mean(axis=0)], "rows": rows_f[i].tolist(), "leaning": bool(lean_tri[i])} for i in order],
            "ring_sagitta_note": "a leaning triangle joins b_j to t_{j+2}: its chord spans two ring segments, so its sagitta is 4x that of an ordinary strip"}


def g6_split(v, f, att: Path) -> dict:
    topo, edges = r6_mesh.closure_and_orientation(v, f)
    ids, ang = r6_metrics.interior_dihedral(v, f, edges)
    p0, p1 = v[edges.vertices[ids, 0]], v[edges.vertices[ids, 1]]
    ln = np.linalg.norm(p1 - p0, axis=1)
    ringlike = np.abs(p1[:, 0] - p0[:, 0]) <= 0.05 * ln
    xm = 0.5 * (p0[:, 0] + p1[:, 0])
    out = {}
    for lo, hi in ((0.0, 0.01), (0.01, 2.0), (2.0, 6.0), (6.0, 12.0), (12.0, 28.0), (28.0, 44.0), (44.0, 44.51)):
        m = ringlike & (xm >= lo) & (xm < hi) & np.isfinite(ang)
        out[f"x_{lo}_{hi}"] = {"ring_like_edges": int(m.sum()), "mean_deg": float(ang[m].mean()) if m.any() else None, "p99_deg": float(np.percentile(ang[m], 99)) if m.any() else None}
    return out


def junction_gaps(att: Path) -> dict:
    out = {}
    for n in ("wing", "horizontal", "vertical"):
        rep = json.loads((att / f"junctions/{n}.json").read_text(encoding="utf-8"))
        txt = Path(rep["edge_mesh_obj"]).read_text(encoding="utf-8").splitlines()
        pts = np.array([list(map(float, line.split()[1:4])) for line in txt if line.startswith("v ")])
        ln = np.array([[int(a) - 1 for a in line.split()[1:3]] for line in txt if line.startswith("l ")])
        deg = np.bincount(ln.ravel(), minlength=len(pts))
        g = coo_matrix((np.ones(len(ln)), (ln[:, 0], ln[:, 1])), shape=(len(pts), len(pts)))
        _, lab = connected_components(g, directed=False)
        loops = []
        for c in range(lab.max() + 1):
            ends = np.flatnonzero((deg == 1) & (lab == c))
            loops.append({"loop": c, "open_ends": int(len(ends)), "end_gap_m": float(np.linalg.norm(pts[ends[0]] - pts[ends[1]])) if len(ends) == 2 else None,
                          "end_xyz_m": [pts[e].round(5).tolist() for e in ends]})
        out[n] = {"loops": loops, "closed_by_geometry_1e-6": all(l["open_ends"] == 0 or (l["end_gap_m"] is not None and l["end_gap_m"] < 1e-6) for l in loops)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    att = args.attempt
    tri = r6_io.read_stl(att / "fuselage.stl")
    v, f = r6_io.weld(tri)
    npz = np.load(att / "fuselage.npz")
    assert np.array_equal(npz["vertices"], v) or len(npz["vertices"]) == len(v)
    v, f, row, region = npz["vertices"], npz["faces"], npz["row"], npz["region"]
    manifest = json.loads((att / "feature-manifest.json").read_text(encoding="utf-8"))
    res = {"note": "information only", "G5": g5_split(v, f, row, region), "L6_split": l6_split(att, v, f, row, manifest), "G6_by_x": g6_split(v, f, att), "junction_open_gaps": junction_gaps(att)}
    args.out.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"G5_fail": res["G5"]["g5_per_triangle_failures"], "G5_without_bands": res["G5"]["without_closure_bands"], "L6_lean": res["L6_split"]["max_in_leaning_strips_m"], "L6_ord": res["L6_split"]["max_in_ordinary_strips_m"]}))


if __name__ == "__main__":
    main()

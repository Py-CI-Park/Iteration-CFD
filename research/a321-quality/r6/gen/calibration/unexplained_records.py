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
"""Characterise surfaceCheck self-intersection records that are NOT at an exactly axis-parallel edge.

For each such record the neighbourhood (triangles with a vertex within --radius) is described: float32 ulp counts of the
edge components (near-parallel edges: both minor components within a few ulps), coplanar triangles (all three vertices share
one float32 coordinate), distinct coordinate values in the neighbourhood, nearest-vertex distance and valence.

How to run: uv run unexplained_records.py --stl f.stl --points selfInterPoints.obj --out report.json [--radius 0.06]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import r6_io


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stl", type=Path, required=True)
    ap.add_argument("--points", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--radius", type=float, default=0.06)
    args = ap.parse_args()
    v, f = r6_io.weld(r6_io.read_stl(args.stl))
    v32 = v.astype(np.float32)
    pts = np.array([[float(x) for x in r.split()[1:4]] for r in args.points.read_text().splitlines() if r.startswith("v ")])
    e = np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
    d = v32[e[:, 1]] - v32[e[:, 0]]
    exact = ((d == 0).sum(axis=1) >= 2)
    tree = cKDTree(v)
    mid = 0.5 * (v[e[:, 0]] + v[e[:, 1]])
    etree = cKDTree(mid)
    dist, vid = tree.query(pts)
    adj = {}
    for k, (a, b) in enumerate(e):
        adj.setdefault(int(a), []).append(k)
        adj.setdefault(int(b), []).append(k)
    rows = []
    for p, dd, i in zip(pts, dist, vid, strict=True):
        if any(exact[k] for k in adj[int(i)]):
            continue
        near_edges = etree.query_ball_point(p, args.radius)
        info = {"point_m": p.tolist(), "nearest_vertex_distance_m": float(dd), "valence": len(adj[int(i)]), "edges_in_radius": len(near_edges)}
        ulps = []
        for k in near_edges:
            ends = v32[e[k]]
            ulp = np.spacing(np.abs(ends).max(axis=0)).astype(np.float64)
            comp = np.abs(d[k]).astype(np.float64) / ulp
            order = np.argsort(comp)
            ulps.append((float(comp[order[0]]), float(comp[order[1]]), "xyz"[int(order[0])] + "xyz"[int(order[1])], bool(exact[k])))
        # near-parallel: the two smallest components within 4 ulps (but not exactly zero in both)
        near = [u for u in ulps if u[1] <= 4.0 and not u[3]]
        info["edges_with_two_minor_components_within_4_ulp_not_exact"] = len(near)
        info["smallest_second_component_ulps"] = float(min((u[1] for u in ulps), default=np.nan))
        info["exactly_parallel_edges_in_radius"] = int(sum(exact[k] for k in near_edges))
        verts = np.unique(e[near_edges].ravel())
        vv = v32[verts]
        info["distinct_z_values_in_radius"] = int(len(np.unique(vv[:, 2])))
        info["z_range_ulps"] = float((vv[:, 2].max() - vv[:, 2].min()) / np.spacing(np.abs(vv[:, 2]).max()))
        info["distinct_y_values_in_radius"] = int(len(np.unique(vv[:, 1])))
        tri_pts = v32[f]
        near_f = np.flatnonzero(np.any(np.linalg.norm(v[f] - p, axis=2) < args.radius, axis=1))
        same_z = int(np.sum(np.all(tri_pts[near_f][:, :, 2] == tri_pts[near_f][:, :1, 2], axis=1)))
        info["triangles_in_radius"] = int(len(near_f))
        info["coplanar_horizontal_triangles_in_radius"] = same_z
        rows.append(info)
    summary = {"unexplained_records": len(rows), "records_total": len(pts),
               "with_near_parallel_edges_within_4ulp": int(sum(r["edges_with_two_minor_components_within_4_ulp_not_exact"] > 0 for r in rows)),
               "with_coplanar_horizontal_triangles": int(sum(r["coplanar_horizontal_triangles_in_radius"] > 0 for r in rows))}
    args.out.write_text(json.dumps({"summary": summary, "records": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for r in rows:
        print([round(x, 4) for x in r["point_m"]], {k: r[k] for k in r if k != "point_m"})


if __name__ == "__main__":
    main()

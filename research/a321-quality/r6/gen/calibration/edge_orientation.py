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
"""Edge-orientation analysis of surfaceCheck self-intersection records on a candidate STL.

For every record point (selfInterPoints.obj) finds the nearest mesh vertex and reports whether any edge at that vertex
is exactly parallel to a coordinate axis in the float32 STL (the trigger found by the synthetic calibration), which
axis, the vertex valence, and where the record lies (axial position, region). Summaries: hits explained by an exactly
axis-parallel edge, hits not explained, histogram by axial bin.

How to run: uv run edge_orientation.py --stl f.stl --points selfInterPoints.obj --out report.json
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
    args = ap.parse_args()
    tri = r6_io.read_stl(args.stl).astype(np.float32)
    v, f = r6_io.weld(tri.astype(np.float64))
    v32 = v.astype(np.float32)
    pts = np.array([[float(x) for x in r.split()[1:4]] for r in args.points.read_text().splitlines() if r.startswith("v ")])
    edges = np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
    d = v32[edges[:, 1]] - v32[edges[:, 0]]
    parallel_axis = np.where(d[:, 0] == 0, "x", "")  # exactly zero component = edge normal to that axis (parallel to the other two)
    exact = {"x": d[:, 0] == 0, "y": d[:, 1] == 0, "z": d[:, 2] == 0}
    # an edge parallel to axis a has the other two components exactly zero
    parallel = {"x": (d[:, 1] == 0) & (d[:, 2] == 0), "y": (d[:, 0] == 0) & (d[:, 2] == 0), "z": (d[:, 0] == 0) & (d[:, 1] == 0)}
    del parallel_axis, exact
    adj = [[] for _ in range(len(v))]
    for k, (a, b) in enumerate(edges):
        adj[a].append(k)
        adj[b].append(k)
    tree = cKDTree(v)
    dist, vid = tree.query(pts)
    rows = []
    for p, dd, i in zip(pts, dist, vid, strict=True):
        axes = [a for a in "xyz" if any(parallel[a][k] for k in adj[i])]
        zero_comp = [a for a in "xyz" if any((d[k, "xyz".index(a)] == 0) for k in adj[i])]
        rows.append({"point_m": p.tolist(), "nearest_vertex_distance_m": float(dd), "vertex_valence": len(adj[i]), "axis_parallel_edges_at_vertex": axes,
                     "edges_with_one_zero_component_at_vertex": zero_comp})
    explained = [r for r in rows if r["axis_parallel_edges_at_vertex"]]
    bins = {}
    for r in rows:
        b = f"x {np.floor(r['point_m'][0]):.0f}..{np.floor(r['point_m'][0]) + 1:.0f}"
        bins[b] = bins.get(b, 0) + 1
    # all axis-parallel edges in the mesh, by axis and axial position
    census = {a: int(parallel[a].sum()) for a in "xyz"}
    summary = {"records": len(rows), "records_with_axis_parallel_edge_at_nearest_vertex": len(explained), "records_without": len(rows) - len(explained),
               "max_nearest_vertex_distance_m": float(dist.max()), "records_by_axial_bin": bins, "mesh_axis_parallel_edge_count": census,
               "mesh_edges": int(len(edges))}
    args.out.write_text(json.dumps({"summary": summary, "records": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    for r in rows[:12]:
        print(r["point_m"], r["vertex_valence"], r["axis_parallel_edges_at_vertex"], r["edges_with_one_zero_component_at_vertex"])


if __name__ == "__main__":
    main()

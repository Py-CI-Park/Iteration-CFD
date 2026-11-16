#!/usr/bin/env -S uv run --script
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
"""INFORMATION ONLY: classify the open end gap of the wing/fuselage junction loop (A1).

Takes the two open ends of a surfaceBooleanFeatures loop, collects both meshes' triangles in a box around them and computes
every edge-triangle intersection point (Moeller-Trumbore, both directions, float64). If such points run through the gap the
curve is geometrically continuous and surfaceBooleanFeatures dropped segments; if the gap holds none the geometry itself is
open there. Also lists the fuselage vertices/edges within 1 mm of each end and whether the facing triangles are near-coplanar.

How to run: uv run --no-project r7_wing_gap.py --attempt <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

import r7_common

r7_common.add_paths()
import r6_io  # noqa: E402


def edge_tri(p0, p1, tris, eps=1e-12):
    """Intersection points of segments (p0,p1) (n,3) with triangles tris (m,3,3): returns list of (edge_i, tri_j, point)."""
    out = []
    d = p1 - p0
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = b - a, c - a
    for i in range(len(p0)):
        h = np.cross(d[i], e2)
        det = np.einsum("ij,ij->i", e1, h)
        ok = np.abs(det) > eps
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = p0[i] - a
        u = np.einsum("ij,ij->i", s, h) * inv
        q = np.cross(s, e1)
        v = (q @ d[i]) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t >= -1e-9) & (t <= 1 + 1e-9)
        for j in np.flatnonzero(hit):
            out.append((i, int(j), (p0[i] + t[j] * d[i]).tolist()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    att = args.attempt
    rep = json.loads((att / "junctions/wing.json").read_text(encoding="utf-8"))
    txt = Path(rep["edge_mesh_obj"]).read_text(encoding="utf-8").splitlines()
    pts = np.array([list(map(float, line.split()[1:4])) for line in txt if line.startswith("v ")])
    ln = np.array([[int(a) - 1 for a in line.split()[1:3]] for line in txt if line.startswith("l ")])
    deg = np.bincount(ln.ravel(), minlength=len(pts))
    ends = pts[np.flatnonzero(deg == 1)]
    ends = ends[ends[:, 1] > 0]  # the +y loop (the -y loop mirrors it)
    lo, hi = ends.min(axis=0) - 0.02, ends.max(axis=0) + 0.02
    fus = r6_io.read_stl(att / "fuselage.stl").astype(np.float64)
    wing = r6_io.read_stl(att / "wing.stl").astype(np.float64)
    inbox = lambda t: t[(t.max(axis=1) >= lo).all(axis=1) & (t.min(axis=1) <= hi).all(axis=1)]  # noqa: E731
    fb, wb = inbox(fus), inbox(wing)
    res: dict = {"ends_m": ends.tolist(), "gap_m": float(np.linalg.norm(ends[0] - ends[1])), "box_lo": lo.tolist(), "box_hi": hi.tolist(), "fuselage_triangles_in_box": int(len(fb)), "wing_triangles_in_box": int(len(wb))}
    points = []
    for tris_a, tris_b, label in ((wb, fb, "wing_edges_vs_fuselage_tris"), (fb, wb, "fuselage_edges_vs_wing_tris")):
        for k0, k1 in ((0, 1), (1, 2), (2, 0)):
            for i, j, p in edge_tri(tris_a[:, k0], tris_a[:, k1], tris_b):
                points.append({"src": label, "xyz": p})
    xyz = np.array([p["xyz"] for p in points]) if points else np.zeros((0, 3))
    inside = xyz[(xyz >= lo).all(axis=1) & (xyz <= hi).all(axis=1)] if len(xyz) else xyz
    order = np.argsort(inside[:, 0]) if len(inside) else []
    res["intersection_points_in_box"] = int(len(inside))
    res["intersection_points_x_sorted"] = inside[order].round(5).tolist()[:80]
    a, b = ends[0], ends[1]
    between = [p for p in inside.tolist() if min(a[0], b[0]) - 1e-4 <= p[0] <= max(a[0], b[0]) + 1e-4]
    res["points_with_x_between_the_two_ends"] = between[:40]
    res["count_points_between_ends"] = len(between)
    near = []
    for e in ends:
        d = np.linalg.norm(fus.reshape(-1, 3) - e, axis=1)
        v_idx = np.unique(np.flatnonzero(d < 1e-3))
        dw = np.linalg.norm(wing.reshape(-1, 3) - e, axis=1)
        near.append({"end": e.tolist(), "fuselage_vertices_within_1mm": int(len(np.unique(fus.reshape(-1, 3)[v_idx].round(6), axis=0))), "nearest_fuselage_vertex_m": float(d.min()), "nearest_wing_vertex_m": float(dw.min())})
        tri_f = fus[np.where(np.linalg.norm(fus.mean(axis=1) - e, axis=1) < 0.03)[0]]
        tri_w = wing[np.where(np.linalg.norm(wing.mean(axis=1) - e, axis=1) < 0.03)[0]]
        nf = np.cross(tri_f[:, 1] - tri_f[:, 0], tri_f[:, 2] - tri_f[:, 0])
        nw = np.cross(tri_w[:, 1] - tri_w[:, 0], tri_w[:, 2] - tri_w[:, 0])
        nf /= np.maximum(np.linalg.norm(nf, axis=1, keepdims=True), 1e-300)
        nw /= np.maximum(np.linalg.norm(nw, axis=1, keepdims=True), 1e-300)
        ang = np.degrees(np.arccos(np.clip(np.abs(nf @ nw.T), 0, 1))) if len(nf) and len(nw) else np.array([[np.nan]])
        near[-1]["triangles_within_30mm"] = {"fuselage": int(len(tri_f)), "wing": int(len(tri_w)), "min_normal_angle_deg_between_a_fuselage_and_a_wing_triangle": float(np.nanmin(ang))}
    res["ends_detail"] = near
    args.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("gap", res["gap_m"], "points in box", res["intersection_points_in_box"], "between ends", res["count_points_between_ends"])


if __name__ == "__main__":
    main()

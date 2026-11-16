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
"""A1/A2 junction analysis of an OpenFOAM v1912 surfaceBooleanFeatures result.

Reads the intersection edge mesh (OBJ lines), counts connected loops, tests each for closure (every vertex degree 2)
and measures the smallest angle between the two surfaces along every loop (grazing test, 0 = tangent).

How to run: uv run junction_analysis.py --sbf-dir <attempt dir> --fuselage f.stl --other o.stl --out report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_io


def read_obj_lines(path: Path) -> tuple[np.ndarray, np.ndarray]:
    verts, lines = [], []
    for row in path.read_text().splitlines():
        parts = row.split()
        if parts and parts[0] == "v":
            verts.append([float(x) for x in parts[1:4]])
        elif parts and parts[0] == "l":
            lines.append([int(x) - 1 for x in parts[1:3]])
    return np.array(verts), np.array(lines, dtype=int)


def surface_normals(mesh: trimesh.Trimesh, points: np.ndarray) -> np.ndarray:
    _, _, tri = trimesh.proximity.closest_point(mesh, points)
    return mesh.face_normals[tri]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sbf-dir", type=Path, required=True)
    ap.add_argument("--fuselage", type=Path, required=True)
    ap.add_argument("--other", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    obj = next((args.sbf_dir / "constant/extendedFeatureEdgeMesh").glob("*_intersection_edgeMesh.obj"))
    verts, lines = read_obj_lines(obj)
    uniq = verts  # the OBJ lists every point once; edges index into it (no welding, so no merged neighbours)
    n = len(uniq)
    graph = coo_matrix((np.ones(len(lines)), (lines[:, 0], lines[:, 1])), shape=(n, n))
    count, label = connected_components(graph, directed=False)
    degree = np.bincount(lines.ravel(), minlength=n)
    meshes = [trimesh.Trimesh(*r6_io.weld(r6_io.read_stl(p)), process=False) for p in (args.fuselage, args.other)]
    mids = 0.5 * (uniq[lines[:, 0]] + uniq[lines[:, 1]])
    n1, n2 = (surface_normals(m, mids) for m in meshes)
    cos = np.clip(np.einsum("ij,ij->i", n1, n2), -1, 1)
    angle = np.degrees(np.minimum(np.arccos(cos), np.arccos(-cos)))
    loops = []
    for c in range(count):
        verts_c = np.flatnonzero(label == c)
        edge_c = np.flatnonzero(label[lines[:, 0]] == c)
        loops.append({
            "vertices": int(len(verts_c)), "edges": int(len(edge_c)), "closed": bool(np.all(degree[verts_c] == 2)),
            "min_surface_angle_deg": float(angle[edge_c].min()), "p5_angle_deg": float(np.percentile(angle[edge_c], 5)),
            "centroid_m": uniq[verts_c].mean(axis=0).tolist(), "bbox_min_m": uniq[verts_c].min(axis=0).tolist(),
            "bbox_max_m": uniq[verts_c].max(axis=0).tolist(),
            "worst_edge_midpoint_m": mids[edge_c[np.argmin(angle[edge_c])]].tolist()})
    ends = np.flatnonzero(degree == 1)  # open-arc endpoints: distance between endpoints of different arcs shows how nearly the loop closes
    gaps = []
    for i in ends:
        for j in ends:
            if i < j and label[i] != label[j]:
                gaps.append({"a_m": uniq[i].tolist(), "b_m": uniq[j].tolist(), "gap_m": float(np.linalg.norm(uniq[i] - uniq[j]))})
    gaps.sort(key=lambda g: g["gap_m"])
    paired = {int(i) for i in ends for j in ends if i != j and label[i] != label[j] and np.linalg.norm(uniq[i] - uniq[j]) < 1e-6}
    effectively_closed = bool(len(ends) == 0 or len(paired) == len(ends))  # every open end meets an end of another arc within 1 micrometre
    report = {"effectively_closed_after_endpoint_merge_1e-6": effectively_closed, "arc_endpoints": int(len(ends)), "open_arc_endpoint_gaps": gaps[:4], "edge_mesh_obj": str(obj), "loops": loops, "loop_count": int(count),
              "all_closed": all(item["closed"] for item in loops),
              "min_surface_angle_deg": float(angle.min()) if len(angle) else None, "edges": int(len(lines)),
              "points_unique": int(n)}
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("loop_count", "all_closed", "min_surface_angle_deg", "edges")}))


if __name__ == "__main__":
    main()

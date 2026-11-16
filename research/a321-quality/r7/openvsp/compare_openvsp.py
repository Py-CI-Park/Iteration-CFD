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
"""Compare the OpenVSP A321 model with R3 / R6-c: gate rows, printed dimensions, dense deviation, symmetry, junctions.

Reads the r6_gate reports (gate/*.json), the surfaceCheck attempt logs (sc/attempts) and the STL files in
.worktmp/r7-openvsp. Writes one JSON. Nothing under research/a321-quality/r7/measure is read (independence).

How to run (from research/a321-quality/r6/checks so that uv finds no project):
  uv run --no-project ../../r7/openvsp/compare_openvsp.py --out ../../r7/openvsp/openvsp-compare.json [--skip-dense]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
WORKTMP = REPO / ".worktmp" / "r7-openvsp"
R3_DIR = REPO / "research/a321-integration/artifacts/shell-r3"
R6C = REPO / "research/a321-quality/r6/candidates/r6-c/attempt01"
THRESH = json.loads((REPO / "research/a321-quality/r6/plans/r6-geometry-contract-02a.json").read_text(encoding="utf-8"))["thresholds_per_component"]
V = {k: v["value"] for k, v in THRESH.items()}
FID_LIMIT = {"fuselage": 0.025, "wing": 0.010, "horizontal": 0.010, "vertical": 0.010}
NAMES = ("fuselage", "wing", "horizontal", "vertical")
BARY = np.array([[1 / 3, 1 / 3, 1 / 3], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5],
                 [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])


def read_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    count = int.from_bytes(raw[80:84], "little")
    if len(raw) != 84 + 50 * count:
        raise ValueError(f"not binary STL: {path}")
    dt = np.dtype([("n", "<f4", (3,)), ("t", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(raw, dtype=dt, count=count, offset=84)["t"].astype(np.float64)


def weld(tri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = tri.reshape(-1, 3) + 0.0
    u, inv = np.unique(flat, axis=0, return_inverse=True)
    return u, inv.reshape(-1, 3)


def mesh_of(tri: np.ndarray) -> trimesh.Trimesh:
    return trimesh.Trimesh(vertices=tri.reshape(-1, 3), faces=np.arange(len(tri) * 3).reshape(-1, 3), process=False)


def dense_one_way(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Distances (and sample points) of every src triangle at 7 barycentric points to the exact closest point on dst."""
    pts = np.einsum("bk,nkd->nbd", BARY, src).reshape(-1, 3)
    m = mesh_of(dst)
    d = np.empty(len(pts))
    for s in range(0, len(pts), 50000):
        _, d[s:s + 50000], _ = trimesh.proximity.closest_point(m, pts[s:s + 50000])
    return d, pts


def summarise(d: np.ndarray, pts: np.ndarray, limit: float | None) -> dict:
    j = int(np.argmax(d))
    out = {"samples": int(len(d)), "max_m": float(d[j]), "p99_m": float(np.percentile(d, 99)), "p50_m": float(np.percentile(d, 50)),
           "worst_xyz_m": [round(float(v), 4) for v in pts[j]]}
    if limit is not None:
        out["over_limit_samples"] = int((d > limit).sum())
    return out


def drop_cap(tri: np.ndarray, axis: int, value: float, tol: float = 1e-6) -> np.ndarray:
    """Triangles of a flat root cap (all three vertices on axis == value) removed."""
    on = np.abs(tri[:, :, axis] - value) < tol
    return tri[~on.all(axis=1)]


def parse_sc(text: str) -> dict:
    loc = re.search(r"self-intersecting at (\d+) locations", text)
    q = re.search(r"min ([\d.e+-]+) for triangle (\d+)", text)
    return {"locations": int(loc.group(1)) if loc else (0 if "not self-intersecting" in text else None),
            "end_reached": bool(re.search(r"^End\s*$", text, re.M)), "fatal": "FOAM FATAL" in text,
            "closed": "Surface is closed" in text, "illegal_triangles": "Surface has no illegal triangles" not in text,
            "unconnected_parts": int(re.search(r"unconnected parts : (\d+)", text).group(1)) if re.search(r"unconnected parts : (\d+)", text) else None,
            "sc_min_quality": float(q.group(1)) if q else None}


def surfacecheck_results() -> dict:
    out = {}
    root = HERE / "sc" / "attempts"
    for d in sorted(root.glob("sc-*-*")) if root.exists() else []:
        name = d.name.split("-")[1]
        rec = parse_sc((d / "result.log").read_text(encoding="utf-8", errors="replace"))
        rec["attempt_dir"] = d.name
        rec["sha256_input"] = (d / "before.sha256").read_text().split()[0]
        rec["wrapper_wall_seconds"] = float((d / "wall.txt").read_text().split()[1])
        out[name] = rec  # sorted by name, the last attempt per surface wins
    return out


def gate_rows(rep: dict, sc: dict | None, label: str) -> list[dict]:
    co, qa, gr = rep["closure_orientation"], rep["quality"], rep["grading"]
    q, a, ar = qa["q_of"], qa["min_angle_deg"], qa["aspect_ratio_longest_edge_over_shortest_altitude"]
    si = rep["self_intersection"]
    faces_valence = rep.get("_max_valence")
    row = lambda m, v, lim, ok: {"metric": m, "value": v, "limit": lim, "pass": None if ok is None else bool(ok)}
    rows = [
        row("G1 watertight [boundary, nonmanifold, components, Euler]", [co["boundary_edges"], co["nonmanifold_edges"], co["connected_components"], co["euler_characteristic"]],
            "[0,0,1,2]", co["watertight_manifold"] and co["boundary_edges"] == 0 and co["nonmanifold_edges"] == 0 and co["connected_components"] == 1 and co["euler_characteristic"] == 2),
        row("G2 winding consistent / outward / volume m3", [co["winding_consistent"], co["outward_normals"], co["signed_volume_total_m3"]], "consistent, outward, V>0",
            co["winding_consistent"] and co["outward_normals"] and co["signed_volume_total_m3"] > 0),
        row("G3 locator pairs", si["locator"]["intersecting_pairs"], 0, si["locator"]["intersecting_pairs"] == 0),
        row("G3 PyMeshLab selected faces", si["meshlab"]["selected_faces"], 0, si["meshlab"]["selected_faces"] == 0),
        row("G3 surfaceCheck locations", None if sc is None else sc["locations"], 0, None if sc is None else (sc["locations"] == 0 and sc["end_reached"] and not sc["fatal"])),
        row("G5 Q_OF min", q["min"], f">= {V['Q_MIN']}", q["min"] >= V["Q_MIN"]),
        row("G5 Q_OF p1", q["p1"], f">= {V['Q_P1_MIN']}", q["p1"] >= V["Q_P1_MIN"]),
        row("G5 min angle min (deg)", a["min"], f">= {V['ANGLE_MIN_DEG']}", a["min"] >= V["ANGLE_MIN_DEG"]),
        row("G5 min angle p5 (deg)", a["p5"], f">= {V['ANGLE_P5_MIN_DEG']}", a["p5"] >= V["ANGLE_P5_MIN_DEG"]),
        row("G5 aspect max", ar["max"], f"<= {V['ASPECT_MAX']}", ar["max"] <= V["ASPECT_MAX"]),
        row("G5 aspect p99", ar["p99"], f"<= {V['ASPECT_P99_MAX']}", ar["p99"] <= V["ASPECT_P99_MAX"]),
        row("G5 adjacent area ratio max", gr["area_ratio_max_over_min"]["max"], f"<= {V['GRADE_AREA_MAX']}", gr["area_ratio_max_over_min"]["max"] <= V["GRADE_AREA_MAX"]),
        row("G5 adjacent area ratio p99", gr["area_ratio_max_over_min"]["p99"], f"<= {V['GRADE_AREA_P99_MAX']}", gr["area_ratio_max_over_min"]["p99"] <= V["GRADE_AREA_P99_MAX"]),
        row("G5 adjacent longest-edge ratio p99", gr["longest_edge_ratio_max_over_min"]["p99"], f"<= {V['GRADE_EDGE_P99_MAX']}", gr["longest_edge_ratio_max_over_min"]["p99"] <= V["GRADE_EDGE_P99_MAX"]),
    ]
    return rows


def valence_max(tri: np.ndarray) -> int:
    _, f = weld(tri)
    e = np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
    return int(np.bincount(e.ravel()).max())


def triangle_q(tri: np.ndarray) -> np.ndarray:
    a = np.linalg.norm(tri[:, 1] - tri[:, 2], axis=1)
    b = np.linalg.norm(tri[:, 0] - tri[:, 2], axis=1)
    c = np.linalg.norm(tri[:, 0] - tri[:, 1], axis=1)
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = a * b * c / (4 * area)
        q = 4 * area / (3 * np.sqrt(3) * r * r)
    return np.nan_to_num(q)


def slice_extent(tri: np.ndarray, axis: int, value: float) -> tuple[float, float] | None:
    pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        da, db = tri[:, a, axis] - value, tri[:, b, axis] - value
        m = da * db < 0
        t = da[m] / (da[m] - db[m])
        pts.append(tri[:, a][m] + t[:, None] * (tri[:, b][m] - tri[:, a][m]))
    p = np.vstack(pts)
    return (float(p[:, 0].min()), float(p[:, 0].max())) if len(p) else None


def slice_points(tri: np.ndarray, axis: int, value: float) -> np.ndarray:
    pts = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        da, db = tri[:, a, axis] - value, tri[:, b, axis] - value
        m = da * db < 0
        t = da[m] / (da[m] - db[m])
        pts.append(tri[:, a][m] + t[:, None] * (tri[:, b][m] - tri[:, a][m]))
    return np.vstack(pts)


def barrel_profile(fus: np.ndarray) -> dict:
    """Constant-section crown, lowest point and height from x-slices of the barrel (R3 and OpenVSP both have x 8 - 29 constant)."""
    ext = []
    for x in np.linspace(8.0, 29.0, 8):
        p = slice_points(fus, 0, float(x))
        ext.append((p[:, 2].min(), p[:, 2].max(), 2 * np.abs(p[:, 1]).max()))
    e = np.array(ext)
    return {"barrel_height_m": float((e[:, 1] - e[:, 0]).max()), "barrel_crown_z_m": float(e[:, 1].max()), "barrel_belly_z_m": float(e[:, 0].min()),
            "barrel_width_m": float(e[:, 2].max())}


def dimensions(models: dict[str, dict[str, np.ndarray]]) -> dict:
    """Printed-dimension measurements from per-component triangles; models: label -> component -> triangles."""
    out = {}
    for label, comp in models.items():
        f, w, h, v = (comp[n].reshape(-1, 3) for n in NAMES)
        bp = barrel_profile(comp["fuselage"])
        wing_root = slice_extent(comp["wing"], 1, 2.2)
        wing_tip = slice_extent(comp["wing"], 1, float(w[:, 1].max()) - 1e-4)
        ht_root = slice_extent(comp["horizontal"], 1, 1.475)
        ht_tip = slice_extent(comp["horizontal"], 1, float(h[:, 1].max()) - 1e-4)
        out[label] = {"length_m": float(f[:, 0].max() - f[:, 0].min()), "max_width_m": float(2 * np.abs(f[:, 1]).max()), "max_height_m": bp["barrel_height_m"],
                      "wing_half_span_m": float(np.abs(w[:, 1]).max()), "horizontal_half_span_m": float(np.abs(h[:, 1]).max()),
                      "fin_tip_minus_fuselage_top_m": float(v[:, 2].max() - bp["barrel_crown_z_m"]), "fin_tip_minus_fuselage_lowest_m": float(v[:, 2].max() - bp["barrel_belly_z_m"]),
                      "wing_root_chord_y2.2_m": None if wing_root is None else wing_root[1] - wing_root[0],
                      "wing_tip_chord_m": None if wing_tip is None else wing_tip[1] - wing_tip[0],
                      "horizontal_root_chord_y1.475_m": None if ht_root is None else ht_root[1] - ht_root[0],
                      "horizontal_tip_chord_m": None if ht_tip is None else ht_tip[1] - ht_tip[0],
                      "fuselage_bbox_z_extent_m_informational": float(f[:, 2].max() - f[:, 2].min()), "fuselage_bbox_zmax_m_informational": float(f[:, 2].max()),
                      "volumes_m3": {n: float(signed_volume(comp[n])) for n in NAMES}, "areas_m2": {n: float(area(comp[n])) for n in NAMES}}
    return out


def signed_volume(tri: np.ndarray) -> float:
    return float(np.einsum("ij,ij->", np.cross(tri[:, 0], tri[:, 1]), tri[:, 2]) / 6)


def area(tri: np.ndarray) -> float:
    return float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())


def symmetry(tri: np.ndarray, half_tri: np.ndarray | None) -> dict:
    verts, faces = weld(tri)
    mir = verts * np.array([1.0, -1.0, 1.0])
    tree = cKDTree(verts)
    dv, _ = tree.query(mir)
    d_surf, pts = dense_one_way(tri * np.array([1.0, -1.0, 1.0]), tri)
    out = {"vertices": int(len(verts)), "vertex_mirror_max_m": float(dv.max()), "vertex_mirror_p99_m": float(np.percentile(dv, 99)),
           "vertex_mirror_fraction_within_1e-6": float((dv <= 1e-6).mean()),
           "surface_mirror": summarise(d_surf, pts * np.array([1.0, -1.0, 1.0]), 1e-6),
           "surface_symmetric_within_1e-6": bool(d_surf.max() <= 1e-6)}
    if half_tri is not None:
        out["half_mesh_triangles"] = int(len(half_tri))
        out["full_mesh_triangles"] = int(len(tri))
        out["half_area_times_2_minus_full_area_m2"] = float(2 * area(half_tri) - area(tri))
        out["half_min_y_m"] = float(half_tri[:, :, 1].min())
    return out


def junctions(union: np.ndarray, comps: dict[str, np.ndarray]) -> dict:
    """Label union triangles by the nearest component surface (wing/horizontal folded to |y|), then count label-boundary loops."""
    cen = union.mean(axis=1)
    dist = {}
    for n in NAMES:
        q = cen.copy()
        if n in ("wing", "horizontal"):
            q[:, 1] = np.abs(q[:, 1])
        m = mesh_of(comps[n])
        d = np.empty(len(q))
        for s0 in range(0, len(q), 20000):  # chunked: one big closest_point call needs tens of GB
            _, d[s0:s0 + 20000], _ = trimesh.proximity.closest_point(m, q[s0:s0 + 20000])
        dist[n] = d
    D = np.stack([dist[n] for n in NAMES], axis=1)
    label = D.argmin(axis=1)
    sep = np.sort(D, axis=1)
    verts, faces = weld(union)
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi, f in enumerate(faces):
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            edge_faces.setdefault((min(a, b), max(a, b)), []).append(fi)
    pairs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for e, fl in edge_faces.items():
        if len(fl) == 2 and label[fl[0]] != label[fl[1]]:
            pairs.setdefault(tuple(sorted((int(label[fl[0]]), int(label[fl[1]])))), []).append(e)
    out = {"label_counts": {n: int((label == i).sum()) for i, n in enumerate(NAMES)},
           "max_nearest_distance_m": float(sep[:, 0].max()), "ambiguous_triangles_second_distance_below_1e-5": int((sep[:, 1] < 1e-5).sum()), "pairs": {}}
    for (la, lb), edges in pairs.items():
        adj: dict[int, list[int]] = {}
        for a, b in edges:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        seen: set[int] = set()
        loops = []
        for s in adj:
            if s in seen:
                continue
            stack, comp = [s], []
            seen.add(s)
            while stack:
                u = stack.pop()
                comp.append(u)
                for w in adj[u]:
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            deg = [len(adj[u]) for u in comp]
            pts = verts[comp]
            loops.append({"vertices": len(comp), "all_degree_2": bool(all(d == 2 for d in deg)), "max_degree": int(max(deg)),
                          "bbox_min": pts.min(axis=0).round(3).tolist(), "bbox_max": pts.max(axis=0).round(3).tolist()})
        out["pairs"][f"{NAMES[la]}|{NAMES[lb]}"] = {"edges": len(edges), "loop_count": len(loops), "all_closed": all(lp["all_degree_2"] for lp in loops), "loops": loops}
    jv = np.array([verts[a] for e in sum(pairs.values(), []) for a in e]) if pairs else np.zeros((0, 3))
    q = triangle_q(union)
    if len(jv):
        tree = cKDTree(jv)
        near, _ = tree.query(cen)
        bad = q < 0.01
        out["bad_triangles_q_below_0.01"] = {"total": int(bad.sum()), "within_0.05m_of_junction": int((bad & (near < 0.05)).sum()),
                                             "within_0.20m_of_junction": int((bad & (near < 0.20)).sum())}
        worst = np.argsort(q)[:10]
        out["worst_10_q"] = [{"q": float(q[i]), "centroid": cen[i].round(3).tolist(), "dist_to_junction_m": float(near[i]), "label": NAMES[int(label[i])]} for i in worst]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-dense", action="store_true")
    args = ap.parse_args()
    t0 = time.perf_counter()
    sc = surfacecheck_results()
    union_tri = read_stl(WORKTMP / "openvsp_union.stl")
    comps = {n: read_stl(WORKTMP / f"openvsp_{n}.stl") for n in NAMES}
    half_path = WORKTMP / "openvsp_union_half.stl"
    half = read_stl(half_path) if half_path.exists() else None
    r3 = {n: read_stl(R3_DIR / f"{n}.stl") for n in NAMES}
    r6c = {n: read_stl(R6C / f"{n}.stl") for n in NAMES}
    import hashlib
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    out: dict = {"stl_sha256": {p.name: sha(p) for p in sorted(WORKTMP.glob("openvsp_*.stl"))}, "surfacecheck": sc}
    gate_u = json.loads((HERE / "gate/union-report.json").read_text(encoding="utf-8"))["openvsp_union"]
    gate_c = json.loads((HERE / "gate/components-report.json").read_text(encoding="utf-8"))
    out["gate_union"] = gate_rows(gate_u, sc.get("union"), "union")
    out["gate_union_valence_max"] = valence_max(union_tri)
    out["gate_components"] = {n: gate_rows(gate_c[f"openvsp_{n}"], sc.get(n), n) for n in NAMES}
    for n in NAMES:
        out["gate_components"][n].append({"metric": "G5 max vertex valence", "value": valence_max(comps[n]), "limit": f"<= {V['VALENCE_MAX']}", "pass": valence_max(comps[n]) <= V["VALENCE_MAX"]})
    out["smoothness_raw"] = {"union": gate_u["smoothness"]["all_edges"], **{n: gate_c[f"openvsp_{n}"]["smoothness"]["all_edges"] for n in NAMES}}
    out["sensitivity_tessellation"] = {}
    for tag, label in (("_t0.5", "tess x0.5"), ("", "tess x1 (production)"), ("_t2.0", "tess x2")):
        tri = read_stl(WORKTMP / f"openvsp_union{tag}.stl")
        v, f = weld(tri)
        e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        _, cnt = np.unique(e, axis=0, return_counts=True)
        q = triangle_q(tri)
        out["sensitivity_tessellation"][label] = {"triangles": int(len(tri)), "boundary_edges": int((cnt == 1).sum()), "nonmanifold_edges": int((cnt > 2).sum()),
                                                  "q_of_min": float(q.min()), "q_of_p1": float(np.percentile(q, 1)), "count_q_below_1e-3": int((q < 1e-3).sum()),
                                                  "count_q_below_1e-2": int((q < 1e-2).sum()), "surfacecheck_locations": sc.get(f"union{tag}", {}).get("locations")}
    out["surfacecheck_record_locations"] = {}
    for nm in ("fuselage_obj", "union_obj"):
        dd = sc.get(nm, {}).get("attempt_dir")
        obj = HERE / "sc" / "attempts" / dd / "selfInterPoints.obj" if dd else None
        if obj is not None and obj.exists():
            pts = np.array([[float(t) for t in ln.split()[1:4]] for ln in obj.read_text().splitlines() if ln.startswith("v ")])
            out["surfacecheck_record_locations"][nm] = {"records": int(len(pts)), "x_min": float(pts[:, 0].min()), "x_max": float(pts[:, 0].max()),
                                                        "in_constant_barrel_x_7.2_29.8": int(((pts[:, 0] >= 7.2) & (pts[:, 0] <= 29.8)).sum()),
                                                        "z_within_5mm_of_belly_or_crown": int(((pts[:, 2] < 1.955) | (pts[:, 2] > 6.085)).sum())}
    out["dimensions"] = dimensions({"openvsp": comps, "r3": r3, "r6c": r6c})
    out["symmetry"] = symmetry(union_tri, half)
    print("symmetry done", round(time.perf_counter() - t0, 1), "s", flush=True)
    out["junctions"] = junctions(union_tri, comps)
    print("junctions done", round(time.perf_counter() - t0, 1), "s", flush=True)
    if not args.skip_dense:
        dev: dict = {}
        for n in NAMES:
            ref = r3["fuselage"] if n == "fuselage" else r6c[n]
            ref_name = "r3_fuselage" if n == "fuselage" else f"r6c_{n}"
            src = comps[n]
            fwd_src = drop_cap(src, 1, 0.0) if n in ("wing", "horizontal") else src
            if n == "vertical":
                fwd_src = drop_cap(src, 2, 5.5)  # root cap lies inside the fuselage and is not part of the lifting surface
            fwd_d, fwd_p = dense_one_way(fwd_src, ref)
            bwd_ref = ref
            ref_s = ref if n not in ("wing", "horizontal") else ref[ref.mean(axis=1)[:, 1] >= -1e-9]
            if n == "vertical":
                ref_s = drop_cap(ref, 2, 5.5)
            bwd_d, bwd_p = dense_one_way(ref_s, src)
            row = {"reference": ref_name, "limit_m": FID_LIMIT[n], "openvsp_to_reference": summarise(fwd_d, fwd_p, FID_LIMIT[n]),
                   "reference_to_openvsp": summarise(bwd_d, bwd_p, FID_LIMIT[n])}
            row["dense_max_m"] = max(row["openvsp_to_reference"]["max_m"], row["reference_to_openvsp"]["max_m"])
            row["note"] = ("openvsp samples exclude the flat root cap (y = 0 or fin root z = 5.5); reference samples are the y >= 0 half" if n != "fuselage" else "")
            dev[n] = row
            print(n, "dense", round(row["dense_max_m"] * 1000, 2), "mm", round(time.perf_counter() - t0, 1), "s", flush=True)
        r3u = read_stl(R3_DIR / "A321_AIRFRAME_SHELL_R3.stl")
        d1, p1 = dense_one_way(union_tri, r3u)
        d2, p2 = dense_one_way(r3u, union_tri)
        dev["union_vs_r3_union"] = {"openvsp_to_r3": summarise(d1, p1, None), "r3_to_openvsp": summarise(d2, p2, None)}
        out["dense_deviation"] = dev
    out["wall_seconds_total"] = time.perf_counter() - t0
    args.out.write_text(json.dumps(out, indent=1, default=str, allow_nan=False), encoding="utf-8")
    print("written", args.out, round(out["wall_seconds_total"], 1), "s")


if __name__ == "__main__":
    main()

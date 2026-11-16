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
"""Evaluate one R7 fuselage attempt against contract 03 / 03a (measures with the gate suite, judges here).

Reads <attempt>/gate/fuselage-report.json (r6_gate.py), <attempt>/sc/fuselage-surfacecheck.json (r7_sc.py),
<attempt>/g7-readback.json, <attempt>/dense/dense.json (r7_dense.py), <attempt>/junctions/*.json, <attempt>/a3.json.
No threshold is invented here: 02a values, 03 / 03a locked numbers.

How to run: uv run --no-project r7_check.py --attempt <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np
from scipy.spatial import cKDTree

import r7_common

r7_common.add_paths()
import r6_io  # noqa: E402
import r6_mesh  # noqa: E402
import r6_metrics  # noqa: E402

T = json.loads((r7_common.PLANS / "r6-geometry-contract-02a.json").read_text(encoding="utf-8"))["thresholds_per_component"]
V = {k: v["value"] for k, v in T.items()}
PRINTED = {"length_m": 44.51, "width_m": 3.95, "height_m": 4.14}
PRINT_TOL = 1e-5
A5_MARGIN, A2_MIN_DEG = 0.075, 5.0


def row(name: str, value, limit, ok, text: str = "") -> dict:
    return {"metric": name, "value": value, "limit": limit, "pass": None if ok is None else bool(ok), "note": text}


class Part:
    axis, mirrored = 0, False

    def __init__(self, stations) -> None:
        self.stations = np.asarray(stations, dtype=np.float64)


def station_ratios(vertices, faces, edges, part, features):
    ids, angles = r6_metrics.interior_dihedral(vertices, faces, edges)
    q = r6_metrics.triangle_quality(vertices, faces)["q_of"]
    angles = np.where((q[edges.face_a[ids]] >= 1e-9) & (q[edges.face_b[ids]] >= 1e-9), angles, np.nan)
    p0, p1 = vertices[edges.vertices[ids, 0]], vertices[edges.vertices[ids, 1]]
    length = np.linalg.norm(p1 - p0, axis=1)
    a0, a1 = p0[:, 0], p1[:, 0]
    ringlike = np.abs(p1[:, 0] - p0[:, 0]) <= 0.05 * length
    tree = cKDTree(part.stations[:, None])
    d0, s0 = tree.query(a0[:, None])
    d1, s1 = tree.query(a1[:, None])
    at = (d0 <= 1e-3) & (d1 <= 1e-3) & (s0 == s1)
    away = (d0 > 1e-3) & (d1 > 1e-3)
    ok = np.isfinite(angles)
    sa, sb = ringlike & at & ok, ringlike & away & ok
    on_feature = r6_metrics.feature_mask(vertices, edges, ids, features)
    sa_excl = sa & ~on_feature
    mean = lambda m: float(angles[m].mean()) if m.any() else None  # noqa: E731
    out = {"A_count": int(sa.sum()), "B_count": int(sb.sum()), "mean_A": mean(sa), "mean_B": mean(sb), "A_excl_count": int(sa_excl.sum()), "mean_A_excl": mean(sa_excl),
           "p99_A_excl": float(np.percentile(angles[sa_excl], 99)) if sa_excl.any() else None, "A_feature_edges_removed": int((sa & on_feature).sum())}
    for key, num in (("ratio_raw", out["mean_A"]), ("ratio_without_features", out["mean_A_excl"])):
        out[key] = num / out["mean_B"] if num is not None and out["mean_B"] and out["mean_B"] >= 0.01 else None
    return out


def loop_end_gaps(report: dict) -> list:
    """Per connected loop of the surfaceBooleanFeatures edge mesh: distance between its two open ends (None when it has no open end)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    txt = Path(report["edge_mesh_obj"]).read_text(encoding="utf-8").splitlines()
    pts = np.array([list(map(float, line.split()[1:4])) for line in txt if line.startswith("v ")])
    ln = np.array([[int(a) - 1 for a in line.split()[1:3]] for line in txt if line.startswith("l ")])
    deg = np.bincount(ln.ravel(), minlength=len(pts))
    g = coo_matrix((np.ones(len(ln)), (ln[:, 0], ln[:, 1])), shape=(len(pts), len(pts)))
    _, lab = connected_components(g, directed=False)
    out = []
    for c in range(lab.max() + 1):
        ends = np.flatnonzero((deg == 1) & (lab == c))
        out.append(float(np.linalg.norm(pts[ends[0]] - pts[ends[1]])) if len(ends) == 2 else None)
    return out


def a5_depths(att: Path) -> dict:
    import trimesh

    import r7_embed as E

    tri = r6_io.read_stl(att / "fuselage.stl")
    v, f = r6_io.weld(tri)
    mesh = trimesh.Trimesh(v, f, process=False)
    out = {}
    for name in ("wing", "horizontal", "vertical"):
        ring, _ = E.root_ring(name)
        sd = trimesh.proximity.signed_distance(mesh, ring)
        i = int(np.argmin(sd))
        out[name] = {"min_depth_m": float(sd[i]), "location_xyz_m": [float(q) for q in ring[i]], "n_outside": int((sd < 0).sum()), "n_vertices": int(len(ring)), "margin_m": A5_MARGIN, "pass": bool(sd[i] >= A5_MARGIN)}
    return out


def evaluate(att: Path) -> dict:
    rep = json.loads((att / "gate/fuselage-report.json").read_text(encoding="utf-8"))["fuselage"]
    manifest = json.loads((att / "feature-manifest.json").read_text(encoding="utf-8"))
    sc = json.loads((att / "sc/fuselage-surfacecheck.json").read_text(encoding="utf-8"))
    dense = json.loads((att / "dense/dense.json").read_text(encoding="utf-8"))
    tri = r6_io.read_stl(att / "fuselage.stl")
    vertices, faces = r6_io.weld(tri)
    topo, edges = r6_mesh.closure_and_orientation(vertices, faces)
    rows: list[dict] = []
    co = rep["closure_orientation"]
    rows.append(row("G1 watertight, boundary/nonmanifold edges, components, Euler", [co["boundary_edges"], co["nonmanifold_edges"], co["connected_components"], co["euler_characteristic"]], "[0,0,1,2] (genus 0)",
                    co["watertight_manifold"] and co["boundary_edges"] == 0 and co["nonmanifold_edges"] == 0 and co["connected_components"] == 1 and co["euler_characteristic"] == 2))
    rows.append(row("G2 winding consistent / outward / volume m3", [co["winding_consistent"], co["outward_normals"], co["signed_volume_total_m3"]], "consistent, outward, V>0", co["winding_consistent"] and co["outward_normals"] and co["signed_volume_total_m3"] > 0))
    si = rep["self_intersection"]
    rows.append(row("G3 locator pairs", si["locator"]["intersecting_pairs"], 0, si["locator"]["intersecting_pairs"] == 0))
    rows.append(row("G3 PyMeshLab selected faces", si["meshlab"]["selected_faces"], 0, si["meshlab"]["selected_faces"] == 0))
    rows.append(row("G3 surfaceCheck v1912 locations (valid parse: End reached, no FATAL, no non-zero exit)", sc["locations"], 0, sc["locations"] == 0 and sc["valid"]))
    # G4R
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    npz = np.load(att / "fuselage.npz")
    row_of, v_npz = npz["row"], npz["vertices"]
    ring_heights = [float(np.ptp(v_npz[row_of == r][:, 2])) for r in range(row_of.max() + 1)]
    printed = {"length_m": float(hi[0] - lo[0]), "width_m": float(hi[1] - lo[1]), "height_m": float(max(ring_heights))}
    for k, label in (("length_m", "length"), ("width_m", "max width"), ("height_m", "max ring height")):
        rows.append(row(f"G4R printed {label} (m)", printed[k], f"{PRINTED[k]} +- {PRINT_TOL}", abs(printed[k] - PRINTED[k]) <= PRINT_TOL,
                        f"bbox height {float(hi[2] - lo[2]):.6f} (crown bulge at the fin root); bounds lo {lo.tolist()} hi {hi.tolist()}" if k == "height_m" else ""))
    rows.append(row("G4R (L6) dense two-sided own-curve deviation, max (m)", dense["L6_max_m"], 0.0025, dense["L6_pass"],
                    f"surface->analytic {dense['L6_surface_to_analytic']['max_m']:.6f} at {dense['L6_surface_to_analytic']['worst_xyz_m']}; analytic->surface {dense['L6_analytic_to_surface']['max_m']:.6f} at {dense['L6_analytic_to_surface']['worst_xyz_m']}"))
    rows.append(row("G4R (L7) top-view outline band, max over both edges (m)", dense["L7"]["top_view"]["max_m"], 0.0244, dense["L7"]["top_view"]["max_m"] <= 0.0244,
                    f"upper {dense['L7']['top_view']['vs_upper_edge_max_m']:.5f} lower {dense['L7']['top_view']['vs_lower_edge_max_m']:.5f}; vs drawn centreline (not gated) {dense['L7']['top_view']['reported_not_gated_vs_drawn_centreline_max_m']:.5f}"))
    sv = dense["L7"]["side_view"]
    rows.append(row("G4R (L7) side-view outline band, crown/belly max (m)", sv["max_m"], 0.0445, sv["max_m"] <= 0.0445,
                    f"crown {sv['crown']['max_m']:.5f} at x {sv['crown']['x_of_max_m']:.3f}; belly {sv['belly']['max_m']:.5f} at x {sv['belly']['x_of_max_m']:.3f}; bridges reported separately: crown {sv['crown_bridge_reported_separately']['max_deviation_to_straight_bridge_m']:.5f}, belly {sv['belly_bridge_reported_separately']['max_deviation_to_straight_bridge_m']:.5f}"))
    # G5
    q, a, ar, gr = rep["quality"]["q_of"], rep["quality"]["min_angle_deg"], rep["quality"]["aspect_ratio_longest_edge_over_shortest_altitude"], rep["grading"]
    rows += [row("G5 Q_OF min", q["min"], f">= {V['Q_MIN']}", q["min"] >= V["Q_MIN"]), row("G5 Q_OF p1", q["p1"], f">= {V['Q_P1_MIN']}", q["p1"] >= V["Q_P1_MIN"]),
             row("G5 min angle min (deg)", a["min"], f">= {V['ANGLE_MIN_DEG']}", a["min"] >= V["ANGLE_MIN_DEG"]), row("G5 min angle p5 (deg)", a["p5"], f">= {V['ANGLE_P5_MIN_DEG']}", a["p5"] >= V["ANGLE_P5_MIN_DEG"]),
             row("G5 aspect max", ar["max"], f"<= {V['ASPECT_MAX']}", ar["max"] <= V["ASPECT_MAX"]), row("G5 aspect p99", ar["p99"], f"<= {V['ASPECT_P99_MAX']}", ar["p99"] <= V["ASPECT_P99_MAX"]),
             row("G5 adjacent area ratio max", gr["area_ratio_max_over_min"]["max"], f"<= {V['GRADE_AREA_MAX']}", gr["area_ratio_max_over_min"]["max"] <= V["GRADE_AREA_MAX"]),
             row("G5 adjacent area ratio p99", gr["area_ratio_max_over_min"]["p99"], f"<= {V['GRADE_AREA_P99_MAX']}", gr["area_ratio_max_over_min"]["p99"] <= V["GRADE_AREA_P99_MAX"]),
             row("G5 adjacent longest-edge ratio p99", gr["longest_edge_ratio_max_over_min"]["p99"], f"<= {V['GRADE_EDGE_P99_MAX']}", gr["longest_edge_ratio_max_over_min"]["p99"] <= V["GRADE_EDGE_P99_MAX"])]
    e = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    val = np.bincount(e.ravel(), minlength=len(vertices))
    rows.append(row("G5 max vertex valence", int(val.max()), f"<= {V['VALENCE_MAX']}", val.max() <= V["VALENCE_MAX"]))
    # G6
    sm = rep["smoothness"]["all_edges_excluding_features"]
    rows.append(row("G6 non-feature dihedral max (deg)", sm["distribution_deg"]["max"], f"<= {V['DIHEDRAL_MAX_DEG_NONFEATURE']}", sm["distribution_deg"]["max"] <= V["DIHEDRAL_MAX_DEG_NONFEATURE"],
                    f"feature edges excluded: {rep['smoothness']['feature_edges_excluded_count']}; edges >30 deg: {sm['count_above_deg']['30']}"))
    rows.append(row("G6 non-feature dihedral p99 (deg)", sm["distribution_deg"]["p99"], f"<= {V['DIHEDRAL_P99_MAX_DEG_NONFEATURE']}", sm["distribution_deg"]["p99"] <= V["DIHEDRAL_P99_MAX_DEG_NONFEATURE"]))
    stations = json.loads((att / "stations-fuselage.json").read_text(encoding="utf-8"))["parts"][0]["stations_m"]
    kr = station_ratios(vertices, faces, edges, Part(stations), json.loads((att / "features-fuselage.json").read_text(encoding="utf-8")))
    ratio = kr["ratio_without_features"] if kr["ratio_without_features"] is not None else kr["ratio_raw"]
    base = f"raw {kr['ratio_raw']}, A={kr['A_count']} B={kr['B_count']} meanA {kr['mean_A']} meanB {kr['mean_B']}; stations {len(stations)}"
    if ratio is None:
        ma, pa = kr["mean_A_excl"], kr["p99_A_excl"]
        rows.append(row("G6 station-edge turning (02d fallback: ratio denominator < 0.01 deg): mean / p99 (deg)", [ma, pa], "mean <= 0.05, p99 <= 0.5", ma is not None and ma <= 0.05 and pa <= 0.5, "ratio undefined, 02d fallback applied; " + base))
    else:
        rows.append(row("G6 station-kink ratio (declared feature rows excluded from A)", ratio, f"<= {V['KINK_MAX']}", ratio <= V["KINK_MAX"], base))
    g7 = json.loads((att / "g7-readback.json").read_text(encoding="utf-8"))["objects"]["fuselage"]
    ok7 = g7["modifiers"] == 0 and g7["world_equals_npz"] and g7["triangles_equal_npz"] and (g7["triangles_equal_stl_in_order"] or g7.get("triangles_equal_stl_as_set", False))
    rows.append(row("G7 fresh-process .blend reopen equals exported STL", ok7, "equal", ok7))
    # assembly
    asm = []
    expected_loops = {"wing": 2, "horizontal": 2, "vertical": 1}
    for name, n_loops in expected_loops.items():
        j = json.loads((att / f"junctions/{name}.json").read_text(encoding="utf-8"))
        gaps = loop_end_gaps(j)
        closed = j["loop_count"] == n_loops and all(g is None or g < 1e-6 for g in gaps)
        asm.append(row(f"A1 junction {name}: closed loops", {"loops": j["loop_count"], "loop_end_gaps_m": gaps}, f"{n_loops} closed loops (end gap < 1e-6 m)", closed,
                       f"edges {j['edges']}; r6 junction_analysis all_closed={j['all_closed']} (it merges only ends of DIFFERENT arcs; here the end gap inside each loop is evaluated from the edge mesh)"))
        asm.append(row(f"A2 junction {name}: min surface angle (deg)", j["min_surface_angle_deg"], f">= {A2_MIN_DEG}", j["min_surface_angle_deg"] is not None and j["min_surface_angle_deg"] >= A2_MIN_DEG))
    a3 = json.loads((att / "a3.json").read_text(encoding="utf-8"))
    for r in a3["rows"]:
        asm.append(row("A3 " + r["item"], r["r6_m"], "printed +- 0.1 m", r["within_band_0.1"], f"printed {r['reference_printed_m']}, delta {r['delta_m']}"))
    a5 = a5_depths(att)
    for name, d in a5.items():
        asm.append(row(f"A5 root embedment {name}: min depth on the tessellated R7 surface (m)", d["min_depth_m"], f">= {A5_MARGIN}", d["pass"], f"at {d['location_xyz_m']}, outside vertices {d['n_outside']}/{d['n_vertices']}"))
    fp = [r["metric"] for r in rows if r["pass"] is False]
    return {"attempt": str(att), "fuselage": {"triangles": len(faces), "rows": rows, "pass_all": not fp, "failed": fp, "kink_detail": kr, "edge_flip": {k: v for k, v in manifest["surface"]["flip"].items()}},
            "assembly": {"rows": asm, "A5_detail": a5, "A4": "renders listed in the report (Blender orthographic); Ego Lite Studio see report"}, "info_vs_r3": dense.get("info_vs_r3")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    res = evaluate(args.attempt)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(res, stream, indent=1, default=float)
    print("fuselage", "PASS" if res["fuselage"]["pass_all"] else "FAIL", res["fuselage"]["failed"])
    for r in res["assembly"]["rows"]:
        print(" ", r["metric"][:70], r["value"], "PASS" if r["pass"] else ("FAIL" if r["pass"] is False else "n/a"))


if __name__ == "__main__":
    main()

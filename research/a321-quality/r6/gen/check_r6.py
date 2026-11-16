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
"""Evaluate one R6 candidate attempt against contract 02 / 02a / 02b / 02c (measures with the gate suite, judges here).

Reads <attempt>/gate/<name>-report.json (r6_gate.py), <attempt>/sc/<name>-result.log (surfaceCheck),
<attempt>/g7-readback.json and junction reports; adds own checks (station points, bounds, volume, valence, kink ratio
without declared kink rows). No threshold is invented here: values come from 02a; fidelity limits from 02/01.

How to run: uv run check_r6.py --attempt <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "checks"))
import r6_io
import r6_ledger
import r6_mesh
import r6_metrics

NAMES = ("fuselage", "wing", "horizontal", "vertical")
T = json.loads((HERE.parent / "plans/r6-geometry-contract-02a.json").read_text())["thresholds_per_component"]
V = {k: v["value"] for k, v in T.items()}
LIM_FIDELITY = {"fuselage": 0.025, "wing": 0.010, "horizontal": 0.010, "vertical": 0.010}
BOUNDS_M, STATION_M, VOLUME_REL = 1e-5, 1e-5, 0.01


def row(name: str, value, limit, ok: bool, text: str = "") -> dict:
    return {"metric": name, "value": value, "limit": limit, "pass": None if ok is None else bool(ok), "note": text}


def parse_surfacecheck(path: Path) -> dict:
    text = path.read_text(errors="replace")
    m = re.search(r"self-intersecting at (\d+) locations", text)
    return {"locations": int(m.group(1)) if m else 0, "end_reached": bool(re.search(r"^End\s*$", text, re.M)),
            "fatal": "FATAL" in text, "closed": "Surface is closed" in text,
            "min_quality": float(re.search(r"min ([\d.e+-]+) for triangle", text).group(1))}


def kink_ratio(vertices, faces, edges, stations, exclude_idx, band=1e-3, ring_like=0.05):
    """mean(A)/mean(B) of ring-like dihedrals; A excludes the stations listed in exclude_idx (declared kink rows)."""
    ids, angles = r6_metrics.interior_dihedral(vertices, faces, edges)
    q = r6_metrics.triangle_quality(vertices, faces)["q_of"]
    angles = np.where((q[edges.face_a[ids]] >= 1e-9) & (q[edges.face_b[ids]] >= 1e-9), angles, np.nan)
    p0, p1 = vertices[edges.vertices[ids, 0]], vertices[edges.vertices[ids, 1]]
    return p0, p1, angles, ids


def station_ratios(vertices, faces, edges, part, kink_stations, features=None):
    """Raw ratio and the ratio with declared kink stations removed from set A (B unchanged)."""
    axis = part.axis
    p0, p1, angles, ids = kink_ratio(vertices, faces, edges, None, None)
    length = np.linalg.norm(p1 - p0, axis=1)
    fold = (lambda c: np.abs(c)) if part.mirrored else (lambda c: c)
    a0, a1 = fold(p0[:, axis]), fold(p1[:, axis])
    ringlike = np.abs(p1[:, axis] - p0[:, axis]) <= 0.05 * length
    tree = cKDTree(part.stations[:, None])
    d0, s0 = tree.query(a0[:, None])
    d1, s1 = tree.query(a1[:, None])
    band = 1e-3
    at = (d0 <= band) & (d1 <= band) & (s0 == s1)
    away = (d0 > band) & (d1 > band)
    ok = np.isfinite(angles)
    sa, sb = ringlike & at & ok, ringlike & away & ok
    kink_set = set(kink_stations)
    on_feature = r6_metrics.feature_mask(vertices, edges, ids, features)  # declared kink rows, cap boundaries, closure-band rows
    sa_excl = sa & ~np.isin(s0, list(kink_set)) & ~on_feature
    mean = lambda m: float(angles[m].mean()) if m.any() else None  # noqa: E731
    out = {"A_count": int(sa.sum()), "B_count": int(sb.sum()), "mean_A": mean(sa), "mean_B": mean(sb),
           "A_excl_count": int(sa_excl.sum()), "mean_A_excl": mean(sa_excl), "p99_A_excl": float(np.percentile(angles[sa_excl], 99)) if sa_excl.any() else None, "A_feature_edges_removed": int((sa & on_feature).sum())}
    for key, num in (("ratio_raw", out["mean_A"]), ("ratio_without_kink_rows", out["mean_A_excl"])):
        out[key] = num / out["mean_B"] if num is not None and out["mean_B"] and out["mean_B"] >= 0.01 else None
    return out


def evaluate_part(att: Path, name: str, parts, manifest) -> dict:
    rep = json.loads((att / f"gate/{name}-report.json").read_text())[name]
    tri = r6_io.read_stl(att / f"{name}.stl")
    vertices, faces = r6_io.weld(tri)
    topo, edges = r6_mesh.closure_and_orientation(vertices, faces)
    part = parts[name]
    rows: list[dict] = []
    co = rep["closure_orientation"]
    rows.append(row("G1 watertight, boundary/nonmanifold edges, components, Euler", [co["boundary_edges"], co["nonmanifold_edges"], co["connected_components"], co["euler_characteristic"]],
                    "[0,0,1,2] (genus 0)", co["watertight_manifold"] and co["boundary_edges"] == 0 and co["nonmanifold_edges"] == 0 and co["connected_components"] == 1 and co["euler_characteristic"] == 2))
    rows.append(row("G2 winding consistent / outward / volume m3", [co["winding_consistent"], co["outward_normals"], co["signed_volume_total_m3"]], "consistent, outward, V>0", co["winding_consistent"] and co["outward_normals"] and co["signed_volume_total_m3"] > 0))
    si = rep["self_intersection"]
    sc = json.loads((att / f"sc/{name}-surfacecheck.json").read_text())
    rows.append(row("G3 locator pairs", si["locator"]["intersecting_pairs"], 0, si["locator"]["intersecting_pairs"] == 0))
    rows.append(row("G3 PyMeshLab selected faces", si["meshlab"]["selected_faces"], 0, si["meshlab"]["selected_faces"] == 0))
    rows.append(row("G3 surfaceCheck locations (End reached, no FATAL)", sc["locations"], 0, sc["locations"] == 0 and sc["end_reached"] and not sc["fatal"]))
    # G4
    ledger = parts[name]
    pts = ledger.points.reshape(-1, 3)
    if ledger.mirrored:
        m = ledger.points[1:].copy()
        m[..., 1] *= -1
        pts = np.concatenate([pts, m.reshape(-1, 3)])
    tree = cKDTree(vertices)
    dist, _ = tree.query(pts.astype(np.float32).astype(np.float64))
    rows.append(row("G4 station points: max distance ledger point -> nearest vertex (m)", float(dist.max()), STATION_M, dist.max() <= STATION_M, f"{len(pts)} ledger points; vertices include every ledger point"))
    r3 = r6_io.read_stl(r6_ledger.R3_DIR / f"{name}.stl").reshape(-1, 3).astype(np.float64)
    lo3, hi3 = r3.min(axis=0), r3.max(axis=0)
    if ledger.mirrored:
        lo3 = lo3.copy()
        lo3[1] = -hi3[1]
    bd = max(np.abs(vertices.min(axis=0) - lo3).max(), np.abs(vertices.max(axis=0) - hi3).max())
    rows.append(row("G4 bounds vs R3 (m)", float(bd), BOUNDS_M, bd <= BOUNDS_M, f"R6 lo {vertices.min(axis=0).tolist()} hi {vertices.max(axis=0).tolist()}"))
    dev = rep["geometry"]["deviation_to_reference"]["max_two_sided_m"]
    rows.append(row("G4 between-station sampled deviation vs R3 (m)", dev, LIM_FIDELITY[name], dev <= LIM_FIDELITY[name], "two-sided 20000-sample max (lower bound of Hausdorff)"))
    k = 2.0 if ledger.mirrored else 1.0
    v3 = float(rep["geometry"]["signed_volume_m3"])
    ref_v = {"fuselage": 466.313355645582, "wing": 2 * 21.31890238091243, "horizontal": 2 * 2.9234116399436836, "vertical": 5.186223034331625}[name]
    rel = abs(v3 - ref_v) / ref_v
    rows.append(row("G4 relative volume change vs R3 (x2 for mirrored)", rel, VOLUME_REL, rel <= VOLUME_REL, f"R6 {v3:.6f} m3 vs R3 {ref_v:.6f}"))
    # G5
    q, a, ar, gr = rep["quality"]["q_of"], rep["quality"]["min_angle_deg"], rep["quality"]["aspect_ratio_longest_edge_over_shortest_altitude"], rep["grading"]
    rows += [row("G5 Q_OF min", q["min"], f">= {V['Q_MIN']}", q["min"] >= V["Q_MIN"]),
             row("G5 Q_OF p1", q["p1"], f">= {V['Q_P1_MIN']}", q["p1"] >= V["Q_P1_MIN"]),
             row("G5 min angle min (deg)", a["min"], f">= {V['ANGLE_MIN_DEG']}", a["min"] >= V["ANGLE_MIN_DEG"]),
             row("G5 min angle p5 (deg)", a["p5"], f">= {V['ANGLE_P5_MIN_DEG']}", a["p5"] >= V["ANGLE_P5_MIN_DEG"]),
             row("G5 aspect max", ar["max"], f"<= {V['ASPECT_MAX']}", ar["max"] <= V["ASPECT_MAX"]),
             row("G5 aspect p99", ar["p99"], f"<= {V['ASPECT_P99_MAX']}", ar["p99"] <= V["ASPECT_P99_MAX"]),
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
    center = len(ledger.stations) - 1 if ledger.mirrored else None
    kink_stations = [abs(kk["index"] - center) if center is not None else kk["index"] for kk in manifest["parts"][name]["kinks_detected"]]
    kr = station_ratios(vertices, faces, edges, part, kink_stations, json.loads((att / f"features-{name}.json").read_text()))
    ratio = kr["ratio_without_kink_rows"] if kr["ratio_without_kink_rows"] is not None else kr["ratio_raw"]
    undefined = ratio is None  # B below the 0.01 deg float32 floor: ratio undefined
    d02 = "r6-geometry-contract-02d" in manifest["contract"]
    base = f"raw {kr['ratio_raw']}, A={kr['A_count']} B={kr['B_count']} meanA {kr['mean_A']} meanB {kr['mean_B']}; declared kink stations {sorted(set(kink_stations))}"
    if undefined and d02:  # 02d fallback: station-edge turning mean <= 0.05 deg and p99 <= 0.5 deg
        ma, pa = kr["mean_A_excl"], kr["p99_A_excl"]
        ok = ma is not None and ma <= 0.05 and pa <= 0.5
        rows.append(row("G6 station-edge turning (02d fallback: ratio denominator < 0.01 deg): mean / p99 (deg)", [ma, pa], "mean <= 0.05, p99 <= 0.5", ok,
                        "ratio undefined, 02d fallback applied; " + base))
    else:
        rows.append(row("G6 station-kink ratio (declared feature rows excluded from A)", "undefined" if undefined else ratio, f"<= {V['KINK_MAX']}",
                        None if undefined else ratio <= V["KINK_MAX"],
                        ("UNDEFINED (mean B below 0.01 deg float32 floor; mean A excl. features %s deg); " % kr["mean_A_excl"] if undefined else "") + base))
    lm = [x for x in manifest["parts"][name].get("line_interpolation_per_segment", []) if "fc_max_deviation_m" in x]
    if lm:  # 02d dense line deviation (reported next to the sampled G4 row; the 25 mm limit applies to the Fritsch-Carlson result)
        worst = max((x["fc_max_deviation_m"] if x["fc_max_deviation_m"] is not None else x["c2_max_deviation_m"]) for x in lm)
        rows.append(row("G4 (02d) longitudinal-line max deviation vs R3, dense line sampling (m)", worst, LIM_FIDELITY[name], worst <= LIM_FIDELITY[name],
                        "deterministic 8 samples per interval on every grid line; the random-surface G4 row above can miss tiny regions"))
    g7 = json.loads((att / "g7-readback.json").read_text())["objects"][name]
    ok7 = g7["modifiers"] == 0 and g7["world_equals_npz"] and g7["triangles_equal_npz"] and (g7["triangles_equal_stl_in_order"] or g7.get("triangles_equal_stl_as_set", False))
    rows.append(row("G7 fresh-process .blend reopen equals exported STL", ok7, "equal", ok7))
    return {"name": name, "triangles": len(faces), "rows": rows, "pass_all": all(r["pass"] is not False for r in rows), "undefined_rows": [r["metric"] for r in rows if r["pass"] is None], "edge_flip": {k: v for k, v in manifest["parts"][name].get("edge_flip", {}).items() if k not in ("flips", "refusals", "limits_used")}, "kink_detail": kr}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    parts = r6_ledger.load_parts()
    manifest = json.loads((args.attempt / "feature-manifest.json").read_text())
    result = {"attempt": str(args.attempt), "parts": {}}
    for name in NAMES:
        result["parts"][name] = evaluate_part(args.attempt, name, parts, manifest)
        print(name, "PASS" if result["parts"][name]["pass_all"] else "FAIL", [r["metric"][:28] for r in result["parts"][name]["rows"] if r["pass"] is False])
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=1, default=float)


if __name__ == "__main__":
    main()

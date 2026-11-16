# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Print markdown tables for OPENVSP_COMPARE_KO.md from openvsp-compare.json, r6 baselines.json and the R6-c gate table.

How to run (system interpreter, standard library only): python3 print_tables.py > tables.md"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R6 = HERE.parents[1] / "r6"
cmp = json.loads((HERE / "openvsp-compare.json").read_text(encoding="utf-8"))
base = json.loads((R6 / "checks/baselines.json").read_text(encoding="utf-8"))["surfaces"]
r6c = json.loads((R6 / "candidates/r6-c/attempt01/gate-table.json").read_text(encoding="utf-8"))["parts"]


def g(v, nd=4):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}g}"
    return str(v)


def base_vals(rep: dict, sc: int | None) -> dict:
    q, a, ar, gr = rep["quality"]["q_of"], rep["quality"]["min_angle_deg"], rep["quality"]["aspect_ratio_longest_edge_over_shortest_altitude"], rep["grading"]
    si = rep["self_intersection"]
    return {"G3 locator pairs": si["locator"]["intersecting_pairs"], "G3 PyMeshLab selected faces": si["meshlab"]["selected_faces"], "G3 surfaceCheck locations": sc,
            "G5 Q_OF min": q["min"], "G5 Q_OF p1": q["p1"], "G5 min angle min (deg)": a["min"], "G5 min angle p5 (deg)": a["p5"], "G5 aspect max": ar["max"], "G5 aspect p99": ar["p99"],
            "G5 adjacent area ratio max": gr["area_ratio_max_over_min"]["max"], "G5 adjacent area ratio p99": gr["area_ratio_max_over_min"]["p99"],
            "G5 adjacent longest-edge ratio p99": gr["longest_edge_ratio_max_over_min"]["p99"]}


def r6c_vals(name: str) -> dict:
    rows = {r["metric"]: r["value"] for r in r6c[name]["rows"]}
    key = {"G3 locator pairs": "G3 locator pairs", "G3 PyMeshLab selected faces": "G3 PyMeshLab selected faces", "G3 surfaceCheck locations": "G3 surfaceCheck locations (End reached, no FATAL)"}
    out = {}
    for k in ("G3 locator pairs", "G3 PyMeshLab selected faces", "G3 surfaceCheck locations", "G5 Q_OF min", "G5 Q_OF p1", "G5 min angle min (deg)", "G5 min angle p5 (deg)", "G5 aspect max", "G5 aspect p99",
              "G5 adjacent area ratio max", "G5 adjacent area ratio p99", "G5 adjacent longest-edge ratio p99", "G5 max vertex valence"):
        out[k] = rows.get(key.get(k, k))
    return out


def table(title: str, rows: list[dict], b: dict, c: dict | None, names: tuple[str, str]) -> None:
    print(f"\n### {title}\n")
    print(f"| 지표 | 한계 | OpenVSP | {names[0]} | {names[1]} | OpenVSP 판정 |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        m = r["metric"]
        if not (m.startswith("G3") or m.startswith("G5")):
            continue
        verdict = "-" if r["pass"] is None else ("통과" if r["pass"] else "실패")
        print(f"| {m} | {r['limit']} | {g(r['value'])} | {g(b.get(m))} | {g(None if c is None else c.get(m))} | {verdict} |")


union_b = base_vals(base["r3_union"], 72)
union_rows = cmp["gate_union"] + [{"metric": "G5 max vertex valence", "value": cmp["gate_union_valence_max"], "limit": "<= 8", "pass": cmp["gate_union_valence_max"] <= 8}]
table("합집합(OpenVSP CompGeom 대 R3 합집합)", union_rows, union_b, None, ("R3 합집합", "-"))
sc_base = {"fuselage": 255, "wing": 0, "horizontal": 0, "vertical": 0}
for n in ("fuselage", "wing", "horizontal", "vertical"):
    table(f"부품 {n}", cmp["gate_components"][n], base_vals(base[f"r3_{n}"], sc_base[n]), r6c_vals(n), ("R3", "R6-c"))
print("\n### 치수\n")
d = cmp["dimensions"]
keys = [k for k in d["openvsp"] if k not in ("volumes_m3", "areas_m2")]
print("| 항목 | 인쇄값 | OpenVSP | R3 | R6-c |\n|---|---|---|---|---|")
printed = {"length_m": 44.51, "max_width_m": 3.95, "max_height_m": 4.14, "wing_half_span_m": 16.29, "horizontal_half_span_m": 6.225, "fin_tip_minus_fuselage_top_m": 5.87,
           "fin_tip_minus_fuselage_lowest_m": 10.01, "wing_root_chord_y2.2_m": 6.07, "wing_tip_chord_m": 1.64, "horizontal_root_chord_y1.475_m": 3.31, "horizontal_tip_chord_m": 1.24}
for k in keys:
    print(f"| {k} | {printed.get(k, '-')} | {g(d['openvsp'][k], 6)} | {g(d['r3'][k], 6)} | {g(d['r6c'][k], 6)} |")
for n in ("fuselage", "wing", "horizontal", "vertical"):
    print(f"| 부피 {n} m3 | - | {g(d['openvsp']['volumes_m3'][n], 6)} | {g(d['r3']['volumes_m3'][n], 6)} | {g(d['r6c']['volumes_m3'][n], 6)} |")
for n in ("fuselage", "wing", "horizontal", "vertical"):
    print(f"| 면적 {n} m2 | - | {g(d['openvsp']['areas_m2'][n], 6)} | {g(d['r3']['areas_m2'][n], 6)} | {g(d['r6c']['areas_m2'][n], 6)} |")
if "dense_deviation" in cmp:
    print("\n### 조밀 양방향 편차\n")
    print("| 부품 | 기준 | 한계 mm | OpenVSP→기준 최대 mm | 기준→OpenVSP 최대 mm | p99 mm (양쪽 큰 값) | 최악 위치 |")
    print("|---|---|---|---|---|---|---|")
    for n, r in cmp["dense_deviation"].items():
        if n == "union_vs_r3_union":
            a, b = r["openvsp_to_r3"], r["r3_to_openvsp"]
            print(f"| 합집합 | R3 합집합 | - | {a['max_m'] * 1000:.2f} | {b['max_m'] * 1000:.2f} | {max(a['p99_m'], b['p99_m']) * 1000:.2f} | {a['worst_xyz_m']} / {b['worst_xyz_m']} |")
            continue
        a, b = r["openvsp_to_reference"], r["reference_to_openvsp"]
        print(f"| {n} | {r['reference']} | {r['limit_m'] * 1000:.0f} | {a['max_m'] * 1000:.2f} | {b['max_m'] * 1000:.2f} | {max(a['p99_m'], b['p99_m']) * 1000:.2f} | {a['worst_xyz_m']} / {b['worst_xyz_m']} |")

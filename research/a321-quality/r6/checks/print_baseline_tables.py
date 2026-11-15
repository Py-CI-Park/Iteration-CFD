# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Print markdown tables from baselines.json (stdlib only). How to run: python print_baseline_tables.py > logs/tables.md"""
from __future__ import annotations

import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent / "baselines.json").read_text(encoding="utf-8"))
SURF = DATA["surfaces"]
NAMES = [n for n in SURF if n != "r3_union_artifact_copy"]


def g(x: float | None, digits: int = 3) -> str:
    return "-" if x is None else f"{x:.{digits}g}"


def table(title: str, header: list[str], rows: list[list[str]]) -> None:
    print(f"\n### {title}\n")
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        print("| " + " | ".join(row) + " |")


def structural() -> None:
    rows = []
    for n in NAMES:
        s = SURF[n]
        c = s["closure_orientation"]
        rows.append([n, f"{s['triangles']:,}", f"{c['welded_vertices']:,}", str(c["boundary_edges"]), str(c["nonmanifold_edges"]),
                     str(c["connected_components"]), str(c["euler_characteristic"]), str(c["winding_inconsistent_edges"]),
                     "예" if c["outward_normals"] else "아니오", f"{c['signed_volume_total_m3']:.6f}"])
    table("구조(폐합·방향)", ["표면", "삼각형", "용접 정점", "경계 변", "비다양체 변", "성분", "오일러", "감김 불일치 변", "바깥 법선", "부피 m3"], rows)


def selfint() -> None:
    rows = []
    for n in NAMES:
        s = SURF[n]["self_intersection"]
        a, f = s["agreement"], s.get("followup_obj_matching")
        pos = s.get("surfacecheck_point_positions")
        where = "-" if not pos else f"바닥 {pos['belly_z_lt_2.03']} / 윗면 {pos['crown_z_gt_6.08']} / 기타 {pos['other']}"
        rows.append([n, f"{s['locator']['intersecting_pairs']} 쌍 / {s['locator']['faces_involved']} 면", f"{a['meshlab_faces']} 면",
                     str(a["surfacecheck_locations"]), str(SURF[n]["handoff_recorded_surfacecheck_locations"] or "-"), where,
                     "-" if not f else f"{f['points_near_meshlab_faces']}/{f['obj_points']}"])
    table("자기교차: 세 검사기", ["표면", "(a) locator", "(b) PyMeshLab", "(c) surfaceCheck 위치", "핸드오프 기록", "(c) 점의 z 위치", "(c) 점이 (b) 면 100um 안"], rows)


def quality() -> None:
    rows = []
    for n in NAMES:
        q = SURF[n]["quality"]
        d, a, ar = q["q_of"], q["min_angle_deg"], q["aspect_ratio_longest_edge_over_shortest_altitude"]
        rows.append([n, g(d["min"], 3), g(d["p0.1"]), g(d["p1"]), g(d["p5"]), g(d["p50"]),
                     f"{q['count_q_of_below']['1e-06']}/{q['count_q_of_below']['0.001']}/{q['count_q_of_below']['0.01']}/{q['count_q_of_below']['0.05']}"])
    table("삼각형 품질 Q_OF (OpenFOAM 방식, 정삼각형=1)", ["표면", "min", "p0.1", "p1", "p5", "중앙값", "개수 <1e-6/<1e-3/<0.01/<0.05"], rows)
    rows = []
    for n in NAMES:
        q = SURF[n]["quality"]
        a, ar = q["min_angle_deg"], q["aspect_ratio_longest_edge_over_shortest_altitude"]
        c = q["count_min_angle_below_deg"]
        k = q["count_aspect_above"]
        rows.append([n, g(a["min"]), g(a["p0.1"]), g(a["p1"]), g(a["p5"]), g(a["p50"]), f"{c['0.1']}/{c['1']}/{c['5']}",
                     g(ar["p50"]), g(ar["p99"]), g(ar["max"]), f"{k['20']}/{k['100']}/{k['1000']}"])
    table("최소 내각(도)과 종횡비(가장 긴 변 / 가장 짧은 높이)", ["표면", "각 min", "p0.1", "p1", "p5", "중앙값", "개수 <0.1°/<1°/<5°", "종횡비 중앙", "p99", "max", "개수 >20/>100/>1000"], rows)


def grading() -> None:
    rows = []
    for n in NAMES:
        s = SURF[n]["grading"]
        a, e = s["area_ratio_max_over_min"], s["longest_edge_ratio_max_over_min"]
        rows.append([n, g(a["p50"]), g(a["p95"]), g(a["p99"]), g(a["max"]), str(s["count_area_ratio_above"]["10"]), g(e["p95"]), g(e["p99"]), g(e["max"]),
                     str(s["count_edge_ratio_above"]["5"])])
    table("크기 변화(인접 삼각형 쌍)", ["표면", "면적비 중앙", "p95", "p99", "max", "쌍 >10", "최장변비 p95", "p99", "max", "쌍 >5"], rows)


def smooth() -> None:
    rows = []
    for n in NAMES:
        s = SURF[n]["smoothness"]
        a, nd, ex = s["all_edges"], s["non_degenerate_faces_only"], s["all_edges_excluding_features"]
        d = a["distribution_deg"]
        c, ce = a["count_above_deg"], ex["count_above_deg"]
        rows.append([n, g(d["p50"]), g(d["p95"]), g(d["p99"]), g(d["max"]), f"{c['10']}/{c['20']}/{c['30']}", f"{ce['10']}/{ce['20']}/{ce['30']}",
                     str(s["feature_edges_excluded_count"]), str(a["edges_with_a_zero_area_face_excluded"]), str(nd["edges_with_a_zero_area_face_excluded"])])
    table("이면각(법선 꺾임, 도)", ["표면", "중앙", "p95", "p99", "max", "변 수 >10/>20/>30 (전체)", "(특징선 제외)", "제외된 특징 변", "영면적 면 제외", "Q<1e-9 면 제외"], rows)


def kink() -> None:
    rows = []
    for n in NAMES:
        for p in SURF[n]["station_kink"]["parts"]:
            a, b = p["A_station_ring_edges"], p["B_nonstation_ring_like_edges"]
            rows.append([n, p["part"], str(a["count"]), g(a["mean_deg"]), g(a["distribution_deg"].get("p95")), str(b["count"]), g(b["mean_deg"]),
                         g(p["mean_A_over_mean_B"]), g(p["context_non_ring_like_edges"]["mean_deg"])])
    table("스테이션 꺾임", ["표면", "부품", "A 변 수", "A 평균°", "A p95°", "B 변 수", "B 평균°", "평균 A/B", "참고: 비링 변 평균°"], rows)


def deviation() -> None:
    rows = []
    for n in NAMES:
        d = SURF[n]["geometry"].get("deviation_to_reference")
        if d:
            rows.append([n, g(d["surface_to_reference_m"]["p50"]), g(d["surface_to_reference_m"]["max"]), g(d["reference_to_surface_m"]["max"]), g(d["max_two_sided_m"])])
    table("R3 합집합 대비 표본 이탈(m)", ["표면", "표면→R3 중앙", "표면→R3 max", "R3→표면 max", "양방향 max"], rows)


def crosscheck() -> None:
    rows = []
    for n in SURF:
        c = SURF[n]["crosscheck_vs_surfacecheck"]
        rows.append([n, "일치" if c["welded_vertices_equal"] and c["triangles_equal"] else "불일치", "일치" if c["parts_equal_components"] else "불일치",
                     g(c["min_quality_surfacecheck"]["value"], 6), g(c["min_quality_gate"]["value"], 6), "일치" if c["min_quality_triangle_equal"] else f"다름({c['min_quality_surfacecheck']['triangle']} vs {c['min_quality_gate']['triangle']})"])
    table("게이트 대 surfaceCheck 교차 확인", ["표면", "정점·삼각형 수", "부분 수=성분 수", "surfaceCheck min Q", "게이트 min Q", "최저 삼각형 번호"], rows)


def timing() -> None:
    rows = []
    for n in SURF:
        r, si = SURF[n], SURF[n]["self_intersection"]
        rows.append([n, f"{r['triangles']:,}", g(r["wall_seconds"], 4), g(si["locator"]["wall_seconds"], 4), g(si["meshlab"]["wall_seconds"], 3),
                     g(si["surfacecheck"]["checker_real_seconds"], 3), g(si["surfacecheck"]["wrapper_wall_seconds"], 3)])
    table("실제 벽시계 시간(초, 9개 프로세스 병렬 실행 중 측정)", ["표면", "삼각형", "게이트 전체", "(a) locator", "(b) PyMeshLab", "(c) surfaceCheck 본체", "(c) WSL 래퍼"], rows)


if __name__ == "__main__":
    for fn in (timing, structural, selfint, quality, grading, smooth, kink, deviation, crosscheck):
        fn()

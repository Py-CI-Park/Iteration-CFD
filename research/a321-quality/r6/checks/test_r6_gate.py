# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Synthetic tests for the R6 gate suite (pytest).

How to run, from this directory:
  uv run --no-project --with pytest --with numpy --with scipy --with trimesh --with rtree --with pymeshlab \
      python -m pytest -p no:cacheprovider -v test_r6_gate.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from r6_mesh import closure_and_orientation, weld
from r6_metrics import grading_report, quality_report, smoothness_report, station_kink_report, triangle_quality
from r6_selfint import locator_check, meshlab_check_triangles, parse_surfacecheck

HERE = Path(__file__).resolve().parent


def tris(vertices: np.ndarray, faces: list[list[int]]) -> np.ndarray:
    """Face list to (N,3,3) triangles."""
    return np.asarray(vertices, dtype=np.float64)[np.asarray(faces)]


def outward(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Flip every face if the signed volume is negative so normals point outward."""
    t = vertices[faces]
    volume = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0
    return faces if volume > 0 else faces[:, ::-1]


def tetra() -> np.ndarray:
    v = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
    f = outward(v, np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]]))  # consistently wound
    return v[f]


def icosphere(levels: int = 2) -> np.ndarray:
    t = (1 + 5**0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    verts = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(levels):
        cache: dict[tuple[int, int], int] = {}

        def mid(a: int, b: int) -> int:
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[key] = len(verts) - 1
            return cache[key]

        new = []
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = new
    verts_a = np.array(verts)
    return verts_a[outward(verts_a, np.array(f))]


def analyse(triangles: np.ndarray) -> tuple[dict, object, np.ndarray, np.ndarray]:
    vertices, faces = weld(triangles)
    topo, edges = closure_and_orientation(vertices, faces)
    return topo, edges, vertices, faces


def test_tetra_and_icosphere_pass_closure_and_orientation() -> None:
    for case in (tetra(), icosphere(2)):
        topo, *_ = analyse(case)
        assert topo["watertight_manifold"] and topo["boundary_edges"] == 0 and topo["nonmanifold_edges"] == 0
        assert topo["connected_components"] == 1 and topo["euler_characteristic"] == 2
        assert topo["components"][0]["genus_if_closed_orientable"] == 0
        assert topo["winding_consistent"] and topo["outward_normals"]
    assert analyse(tetra())[0]["faces"] == 4


def test_sphere_with_one_face_removed_fails_closure() -> None:
    topo, *_ = analyse(icosphere(2)[1:])
    assert not topo["watertight_manifold"] and topo["boundary_edges"] == 3 and not topo["outward_normals"]


def test_inverted_sphere_fails_orientation_but_stays_consistent() -> None:
    topo, *_ = analyse(icosphere(2)[:, ::-1])
    assert topo["winding_consistent"] and not topo["outward_normals"] and topo["signed_volume_total_m3"] < 0


def test_one_flipped_face_breaks_winding_consistency() -> None:
    sphere = icosphere(2).copy()
    sphere[0] = sphere[0][::-1]
    topo, *_ = analyse(sphere)
    assert topo["winding_inconsistent_edges"] == 3 and not topo["outward_normals"]


def test_two_disjoint_components_and_signed_negative_zero_weld() -> None:
    far = tetra() + np.array([5.0, 0.0, 0.0])
    topo, *_ = analyse(np.concatenate([tetra(), far]))
    assert topo["connected_components"] == 2 and topo["euler_characteristic"] == 4
    quad = np.array([[[0.0, 0.0, 0.0], [1, 0, 0], [0, 1, 0]], [[-0.0, 1, 0], [1, 0, 0], [1, 1, 0]]])
    vertices, _ = weld(quad)
    assert len(vertices) == 4  # -0.0 and +0.0 merged


CROSSING = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0.2, 0.2, -1], [0.2, 0.2, 1], [1.2, 0.2, 0.5]]], dtype=np.float64)
EDGE_SHARING = np.array([[[0, 0, 0], [1, 0, 0], [1, 1, 0]], [[0, 0, 0], [1, 1, 0], [0, 1, 0]]], dtype=np.float64)


def test_crossing_triangles_detected_by_both_checkers() -> None:
    locator = locator_check(CROSSING)
    meshlab = meshlab_check_triangles(CROSSING)
    assert locator["intersecting_pairs"] == 1 and locator["face_ids"] == [0, 1]
    assert meshlab["selected_faces"] == 2 and meshlab["selected_face_ids"] == [0, 1]


def test_edge_sharing_triangles_not_detected_by_either_checker() -> None:
    assert locator_check(EDGE_SHARING)["intersecting_pairs"] == 0
    assert meshlab_check_triangles(EDGE_SHARING)["selected_faces"] == 0


def test_clean_icosphere_has_no_self_intersection_in_either_checker() -> None:
    sphere = icosphere(2)
    assert locator_check(sphere)["faces_involved"] == 0
    assert meshlab_check_triangles(sphere)["selected_faces"] == 0


def test_sliver_triangle_is_flagged_by_quality() -> None:
    sphere = icosphere(1)
    a, b, c = sphere[0]
    sliver = np.array([[a, b, a + 1e-6 * (b - a) + 1e-9 * (c - a)]])  # near-collinear, tiny height
    vertices, faces = weld(np.concatenate([sphere[1:], sliver]))
    report = quality_report(vertices, faces)
    assert report["count_q_of_below"]["0.001"] >= 1 and report["count_min_angle_below_deg"]["0.1"] >= 1
    assert report["count_aspect_above"]["1000"] >= 1 and report["q_of"]["min"] < 1e-3


def test_quality_formula_equilateral_is_one_and_right_isoceles_known_value() -> None:
    eq = np.array([[[0, 0, 0], [1, 0, 0], [0.5, 3**0.5 / 2, 0]]], dtype=np.float64)
    iso = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=np.float64)
    q_eq = triangle_quality(*weld(eq))
    q_iso = triangle_quality(*weld(iso))
    assert q_eq["q_of"][0] == pytest.approx(1.0, abs=1e-12) and q_eq["min_angle_deg"][0] == pytest.approx(60.0)
    assert q_iso["q_of"][0] == pytest.approx(2.0 / (3.0 * 3**0.5 * 0.5), rel=1e-12)  # 4A/(3 sqrt3 R^2), A=.5, R^2=.5
    assert q_iso["min_angle_deg"][0] == pytest.approx(45.0) and q_iso["aspect"][0] == pytest.approx(2**0.5 / (1 / 2**0.5))


def test_grading_ratio_on_graded_fan() -> None:
    # two triangles sharing an edge, second one 4x the area with a 2x longer longest edge
    pair = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[1, 0, 0], [0, 0, 0], [0, -4, 0]]], dtype=np.float64)
    vertices, faces = weld(pair)
    _, edges, *_ = analyse(pair)
    report = grading_report(vertices, faces, edges)
    assert report["pairs"] == 1 and report["area_ratio_max_over_min"]["max"] == pytest.approx(4.0)


def cube() -> np.ndarray:
    v = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], dtype=np.float64)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    f = np.array([tri for q in quads for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))])
    return v[outward(v, f)]


def test_feature_edge_exclusion_removes_only_the_listed_edge() -> None:
    topo, edges, vertices, faces = analyse(cube())
    assert topo["watertight_manifold"] and topo["outward_normals"]
    plain = smoothness_report(vertices, faces, edges, None)
    assert plain["all_edges"]["count_above_deg"]["30"] == 12  # twelve 90 degree cube edges
    features = {"tolerance_m": 1e-3, "features": [{"name": "one edge", "polyline": [[0, 0, 0], [0, 0, 1]]}]}
    with_features = smoothness_report(vertices, faces, edges, features)
    assert with_features["feature_edges_excluded_count"] == 1
    assert with_features["all_edges_excluding_features"]["count_above_deg"]["30"] == 11
    assert with_features["all_edges"]["count_above_deg"]["30"] == 12  # reported both ways


def lofted_cylinder(radius_at, stations: np.ndarray, sides: int = 32) -> np.ndarray:
    """Open polyline-loft cylinder along x; rings at `stations`, quads split by a fixed diagonal."""
    angle = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    rings = [np.column_stack([np.full(sides, x), radius_at(x) * np.cos(angle), radius_at(x) * np.sin(angle)]) for x in stations]
    out = []
    for r0, r1 in zip(rings[:-1], rings[1:], strict=True):
        for k in range(sides):
            n = (k + 1) % sides
            out += [[r0[k], r0[n], r1[n]], [r0[k], r1[n], r1[k]]]
    return np.array(out)


def test_station_kink_metric_separates_slope_break_from_smooth_cylinder() -> None:
    xs = np.linspace(0.0, 1.0, 11)  # rings every 0.1; the only declared station is x = 0.5
    part = [{"name": "demo", "axis": 0, "stations_m": [0.5]}]

    def kink(x: float) -> float:
        return 1.0 + 0.8 * max(x - 0.5, 0.0)  # slope break exactly at the station

    def smooth(x: float) -> float:
        return 1.0 + 0.0 * x

    reports = {}
    for label, profile in (("kink", kink), ("smooth", smooth)):
        vertices, faces = weld(lofted_cylinder(profile, xs))
        _, edges = closure_and_orientation(vertices, faces)
        reports[label] = station_kink_report(vertices, faces, edges, part)["parts"][0]
    a_kink, a_smooth = reports["kink"]["A_station_ring_edges"], reports["smooth"]["A_station_ring_edges"]
    b_kink = reports["kink"]["B_nonstation_ring_like_edges"]
    assert a_kink["count"] == 32 and a_smooth["count"] == 32
    assert a_smooth["mean_deg"] == pytest.approx(0.0, abs=1e-3)
    assert a_kink["mean_deg"] > 20.0  # ~ atan(0.8/0.1)-ish normal turning at the break
    assert b_kink["count"] > 0 and b_kink["mean_deg"] == pytest.approx(0.0, abs=1e-3)  # float32 STL rounding noise
    assert reports["smooth"]["mean_A_over_mean_B"] is None  # 0/0 is reported as undefined, not as a number


def test_parse_surfacecheck_log_from_calibration_run() -> None:
    text = (HERE / "attempts" / "calibration-r3fuselage-writeSets" / "result.log").read_text(encoding="utf-8")
    parsed = parse_surfacecheck(text)
    assert parsed["self_intersection_locations"] == 255 and parsed["end_reached"] and not parsed["fatal"]
    assert parsed["quality_min"] == {"value": 0.000801611, "triangle": 410} and parsed["closed"]
    assert parsed["triangles"] == 46592 and parsed["vertices"] == 23298 and parsed["zones"] == 1


def test_station_region_and_exclusion_boxes_drop_edges() -> None:
    xs = np.linspace(0.0, 1.0, 11)
    vertices, faces = weld(lofted_cylinder(lambda x: 1.0, xs))
    _, edges = closure_and_orientation(vertices, faces)
    base = {"name": "demo", "axis": 0, "stations_m": [0.5]}
    whole = station_kink_report(vertices, faces, edges, [base])["parts"][0]["A_station_ring_edges"]["count"]
    cover = {**base, "exclude_bboxes_m": [[[0.4, -2, -2], [0.6, 2, 2]]]}
    away = {**base, "region_bbox_m": [[0.7, -2, -2], [1.0, 2, 2]]}
    assert whole == 32
    assert station_kink_report(vertices, faces, edges, [cover])["parts"][0]["A_station_ring_edges"]["count"] == 0
    assert station_kink_report(vertices, faces, edges, [away])["parts"][0]["A_station_ring_edges"]["count"] == 0

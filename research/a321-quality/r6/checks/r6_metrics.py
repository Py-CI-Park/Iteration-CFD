# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""R6 gate suite: triangle quality, size grading, smoothness, station kinks, geometry deltas.

Measurements only. Floors and angle cuts are reporting parameters, not acceptance limits.
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from r6_mesh import EdgeTable, face_geometry

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

PERCENTILES = (0.1, 1.0, 5.0, 50.0)
QUALITY_FLOORS = (1e-6, 1e-3, 0.01, 0.05, 0.1)  # reporting floors for Q_OF
MIN_ANGLE_FLOORS_DEG = (0.1, 1.0, 5.0, 10.0)
ASPECT_CEILINGS = (20.0, 50.0, 100.0, 1000.0)
DIHEDRAL_CUTS_DEG = (10.0, 20.0, 30.0)
NEAR_DEGENERATE_Q = 1e-9  # reporting cut used to split "noise-normal" faces from the rest


def distribution(values: FloatArray) -> dict:
    """min, p0.1, p1, p5, median, max of finite values; counts of non-finite values."""
    finite = values[np.isfinite(values)]
    out: dict = {"count": int(len(values)), "nonfinite": int(len(values) - len(finite))}
    if len(finite) == 0:
        return out
    out["min"] = float(finite.min())
    for p in PERCENTILES:
        out[f"p{p:g}"] = float(np.percentile(finite, p))
    out["p95"] = float(np.percentile(finite, 95.0))
    out["p99"] = float(np.percentile(finite, 99.0))
    out["p99.9"] = float(np.percentile(finite, 99.9))
    out["max"] = float(finite.max())
    return out


def triangle_quality(vertices: FloatArray, faces: IntArray) -> dict[str, FloatArray]:
    """Per-triangle Q_OF, minimum interior angle (deg) and aspect ratio.

    Q_OF = 4*A / (3*sqrt(3)*R^2), R the circumradius: triangle area over the area of the
    equilateral triangle inscribed in the same circumcircle (equilateral = 1, collapsed = 0).
    This was fitted empirically against the per-triangle `quality` array that OpenFOAM v1912
    surfaceCheck writes with -writeSets vtk (ratio 1 +/- 6e-8 over 46,592 triangles; see
    calibrate_quality_vs_surfacecheck.py and logs); OpenFOAM source was not read.
    Aspect ratio = longest edge / shortest altitude (shortest altitude = 2A / longest edge).
    """
    area, _, sides = face_geometry(vertices, faces)
    a, b, c = sides[:, 0], sides[:, 1], sides[:, 2]
    longest = sides.max(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        circum = a * b * c / (4.0 * area)
        q_of = 4.0 * area / (3.0 * np.sqrt(3.0) * circum**2)
        q_of = np.where(area > 0, q_of, 0.0)
        cos = np.stack([(b**2 + c**2 - a**2) / (2 * b * c), (c**2 + a**2 - b**2) / (2 * c * a),
                        (a**2 + b**2 - c**2) / (2 * a * b)], axis=1)
        angles = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
        min_angle = np.where(area > 0, np.nanmin(angles, axis=1), 0.0)
        aspect = np.where(area > 0, longest / (2.0 * area / longest), np.inf)
    return {"q_of": q_of, "min_angle_deg": min_angle, "aspect": aspect, "area": area}


def quality_report(vertices: FloatArray, faces: IntArray) -> dict:
    """Metric 4: distributions of Q_OF, min angle and aspect ratio plus floor counts."""
    t = triangle_quality(vertices, faces)
    worst = np.argsort(t["q_of"])[:10]
    return {
        "q_of_formula": "4*A/(3*sqrt(3)*R^2), R = circumradius = abc/(4A); fitted to surfaceCheck v1912 quality array",
        "q_of": distribution(t["q_of"]),
        "min_angle_deg": distribution(t["min_angle_deg"]),
        "aspect_ratio_longest_edge_over_shortest_altitude": distribution(t["aspect"]),
        "count_q_of_below": {f"{f:g}": int(np.sum(t["q_of"] < f)) for f in QUALITY_FLOORS},
        "count_min_angle_below_deg": {f"{f:g}": int(np.sum(t["min_angle_deg"] < f)) for f in MIN_ANGLE_FLOORS_DEG},
        "count_aspect_above": {f"{f:g}": int(np.sum(t["aspect"] > f)) for f in ASPECT_CEILINGS},
        "zero_area_faces": int(np.sum(t["area"] == 0)),
        "near_degenerate_faces_q_below_1e-9": int(np.sum(t["q_of"] < NEAR_DEGENERATE_Q)),
        "worst_ten_triangles": [{"triangle": int(i), "q_of": float(t["q_of"][i])} for i in worst],
    }


def pair_arrays(edges: EdgeTable) -> tuple[IntArray, IntArray, IntArray]:
    """Edge ids, and the two faces, for every interior (exactly two faces) edge."""
    interior = np.flatnonzero(edges.count == 2)
    return interior, edges.face_a[interior], edges.face_b[interior]


def grading_report(vertices: FloatArray, faces: IntArray, edges: EdgeTable) -> dict:
    """Metric 5: area ratio and longest-edge ratio across every edge-adjacent triangle pair."""
    area, _, sides = face_geometry(vertices, faces)
    _, fa, fb = pair_arrays(edges)
    longest = sides.max(axis=1)
    both_positive = (area[fa] > 0) & (area[fb] > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        area_ratio = np.maximum(area[fa], area[fb]) / np.minimum(area[fa], area[fb])
        edge_ratio = np.maximum(longest[fa], longest[fb]) / np.minimum(longest[fa], longest[fb])
    area_ratio = np.where(both_positive, area_ratio, np.nan)
    edge_ratio = np.where(both_positive, edge_ratio, np.nan)
    return {
        "pairs": int(len(fa)), "pairs_with_a_zero_area_face_excluded": int(np.sum(~both_positive)),
        "area_ratio_max_over_min": distribution(area_ratio),
        "longest_edge_ratio_max_over_min": distribution(edge_ratio),
        "count_area_ratio_above": {str(k): int(np.nansum(area_ratio > k)) for k in (2, 5, 10, 100)},
        "count_edge_ratio_above": {str(k): int(np.nansum(edge_ratio > k)) for k in (2, 5, 10, 100)},
    }


def interior_dihedral(vertices: FloatArray, faces: IntArray, edges: EdgeTable) -> tuple[IntArray, FloatArray]:
    """Normal turning angle (deg) per interior edge; NaN when either face has zero area.

    When the two faces traverse the shared edge in the same direction (inconsistent winding)
    the second normal is flipped so the angle reflects geometry and not the winding fault.
    """
    ids, fa, fb = pair_arrays(edges)
    _, normal, _ = face_geometry(vertices, faces)
    flip = np.where(np.abs(edges.direction_sum[ids]) == 2, -1.0, 1.0)
    dot = np.einsum("ij,ij->i", normal[fa], normal[fb] * flip[:, None])
    return ids, np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))


def edge_midpoints(vertices: FloatArray, edges: EdgeTable, ids: IntArray) -> FloatArray:
    """Midpoint of each listed edge."""
    return 0.5 * (vertices[edges.vertices[ids, 0]] + vertices[edges.vertices[ids, 1]])


def feature_mask(vertices: FloatArray, edges: EdgeTable, ids: IntArray, features: dict | None) -> FloatArray:
    """True for edges whose two endpoints both lie within tolerance of a feature polyline.

    Feature JSON: {"tolerance_m": 0.0005, "features": [{"name": "...", "polyline": [[x,y,z],...]}]}.
    Polylines are resampled at tolerance/2 and matched with a KD-tree (match error <= tolerance/4).
    """
    if not features or not features.get("features"):
        return np.zeros(len(ids), bool)
    tol = float(features.get("tolerance_m", 5e-4))
    samples = []
    for item in features["features"]:
        pts = np.asarray(item["polyline"], dtype=np.float64)
        for p, q in zip(pts[:-1], pts[1:], strict=True):
            n = max(int(np.ceil(np.linalg.norm(q - p) / (tol / 2))), 1)
            samples.append(p + (q - p) * (np.arange(n + 1) / n)[:, None])
    tree = cKDTree(np.concatenate(samples))
    end0, _ = tree.query(vertices[edges.vertices[ids, 0]], distance_upper_bound=tol)
    end1, _ = tree.query(vertices[edges.vertices[ids, 1]], distance_upper_bound=tol)
    return np.isfinite(end0) & np.isfinite(end1)


def dihedral_summary(angles: FloatArray, vertices: FloatArray, edges: EdgeTable, ids: IntArray, keep_top: int = 20) -> dict:
    """Distribution, counts above the 10/20/30 degree cuts, and the largest edges with coordinates."""
    valid = np.isfinite(angles)
    out = {"edges": int(len(angles)), "edges_with_a_zero_area_face_excluded": int(np.sum(~valid)),
           "distribution_deg": distribution(angles),
           "count_above_deg": {f"{c:g}": int(np.sum(angles[valid] > c)) for c in DIHEDRAL_CUTS_DEG}}
    order = np.argsort(np.where(valid, angles, -1.0))[::-1][:keep_top]
    mids = edge_midpoints(vertices, edges, ids[order])
    out["largest"] = [{"edge_midpoint_m": mids[k].tolist(), "angle_deg": float(angles[o])}
                      for k, o in enumerate(order) if valid[o]]
    return out


def smoothness_report(vertices: FloatArray, faces: IntArray, edges: EdgeTable, features: dict | None) -> dict:
    """Metrics 6 and 7: dihedral statistics with and without feature-edge exclusion.

    The `non_degenerate` view additionally drops faces with Q_OF < 1e-9, whose normals are noise.
    """
    ids, angles = interior_dihedral(vertices, faces, edges)
    q = triangle_quality(vertices, faces)["q_of"]
    ok = (q[edges.face_a[ids]] >= NEAR_DEGENERATE_Q) & (q[edges.face_b[ids]] >= NEAR_DEGENERATE_Q)
    on_feature = feature_mask(vertices, edges, ids, features)
    angles_nd = np.where(ok, angles, np.nan)
    return {
        "feature_polylines_supplied": bool(features and features.get("features")),
        "feature_edges_excluded_count": int(on_feature.sum()),
        "all_edges": dihedral_summary(angles, vertices, edges, ids),
        "all_edges_excluding_features": dihedral_summary(angles[~on_feature], vertices, edges, ids[~on_feature]),
        "non_degenerate_faces_only": dihedral_summary(angles_nd, vertices, edges, ids),
        "non_degenerate_faces_only_excluding_features": dihedral_summary(angles_nd[~on_feature], vertices, edges, ids[~on_feature]),
    }


def _station_value(coord: FloatArray, axis: int) -> FloatArray:
    """Position along a station axis; the span axis (y) is folded because wing/tail are mirrored."""
    return np.abs(coord) if axis == 1 else coord


def station_kink_report(vertices: FloatArray, faces: IntArray, edges: EdgeTable, parts: list[dict],
                        band_m: float = 1e-3, ring_like: float = 0.05, b_floor_deg: float = 0.01) -> dict:
    """Metric 6 (station kinks): ring-edge dihedral at station planes vs ring-like edges elsewhere.

    parts: [{"name", "axis", "stations_m", optional "region_bbox_m": [[lo],[hi]], optional "exclude_bboxes_m": [[[lo],[hi]], ...]}].
    Edges whose midpoint is outside the region, or inside any exclusion box, are ignored (union surfaces:
    the other parts' bounds are excluded so their edges do not pollute this part's station planes).
    A ring-like edge has |component along the station axis| <= ring_like * edge length.
    A = ring-like interior edges with both endpoints within band_m of one station plane;
    B = ring-like interior edges with no endpoint within band_m of any station plane.
    ratio = mean(A)/mean(B) is None when B is empty or mean(B) < b_floor_deg (0.01 deg, the float32 STL
    resolution floor: noise/noise is not a ratio); both means are always given.
    Edges that are not ring-like (longitudinal/diagonal) are reported only as context because their
    turning is circumferential, a different quantity.
    """
    ids, angles = interior_dihedral(vertices, faces, edges)
    q = triangle_quality(vertices, faces)["q_of"]
    angles = np.where((q[edges.face_a[ids]] >= NEAR_DEGENERATE_Q) & (q[edges.face_b[ids]] >= NEAR_DEGENERATE_Q), angles, np.nan)
    p0, p1 = vertices[edges.vertices[ids, 0]], vertices[edges.vertices[ids, 1]]
    length = np.linalg.norm(p1 - p0, axis=1)
    results = []
    for part in parts:
        axis = int(part["axis"])
        stations = np.asarray(part["stations_m"], dtype=np.float64)
        inside = np.ones(len(ids), bool)
        if part.get("region_bbox_m"):
            lo, hi = np.asarray(part["region_bbox_m"], dtype=np.float64)
            inside = np.all((0.5 * (p0 + p1) >= lo) & (0.5 * (p0 + p1) <= hi), axis=1)
        for box in part.get("exclude_bboxes_m", []):
            lo, hi = np.asarray(box, dtype=np.float64)
            inside &= ~np.all((0.5 * (p0 + p1) >= lo) & (0.5 * (p0 + p1) <= hi), axis=1)
        along0, along1 = _station_value(p0[:, axis], axis), _station_value(p1[:, axis], axis)
        ringlike = np.abs(p1[:, axis] - p0[:, axis]) <= ring_like * length
        tree = cKDTree(stations[:, None])
        d0, s0 = tree.query(along0[:, None])
        d1, s1 = tree.query(along1[:, None])
        at_station = (d0 <= band_m) & (d1 <= band_m) & (s0 == s1)
        away = (d0 > band_m) & (d1 > band_m)
        set_a, set_b = inside & ringlike & at_station & np.isfinite(angles), inside & ringlike & away & np.isfinite(angles)
        other = inside & ~ringlike & np.isfinite(angles)
        mean_a = float(angles[set_a].mean()) if set_a.any() else None
        mean_b = float(angles[set_b].mean()) if set_b.any() else None
        ratio = mean_a / mean_b if (mean_a is not None and mean_b is not None and mean_b >= b_floor_deg) else None
        results.append({
            "part": part["name"], "axis": axis, "stations": int(len(stations)), "band_m": band_m, "b_floor_deg": b_floor_deg,
            "ring_like_tolerance": ring_like, "region_bbox_m": part.get("region_bbox_m"), "exclude_bboxes_m": part.get("exclude_bboxes_m", []),
            "A_station_ring_edges": {"count": int(set_a.sum()), "mean_deg": mean_a, "distribution_deg": distribution(angles[set_a])},
            "B_nonstation_ring_like_edges": {"count": int(set_b.sum()), "mean_deg": mean_b, "distribution_deg": distribution(angles[set_b])},
            "mean_A_over_mean_B": ratio,
            "ratio_note": None if ratio is not None else "no non-station ring-like edges, or their mean is below the 0.01 deg float32 floor; ratio undefined, use the A distribution",
            "context_non_ring_like_edges": {"count": int(other.sum()), "mean_deg": float(angles[other].mean()) if other.any() else None},
        })
    return {"parts": results}


def bbox_and_volume(vertices: FloatArray, total_volume: float) -> dict:
    """Metric 8 (absolute part): bounding box and signed volume."""
    return {"bbox_min_m": vertices.min(axis=0).tolist(), "bbox_max_m": vertices.max(axis=0).tolist(),
            "signed_volume_m3": total_volume}


def sample_surface(vertices: FloatArray, faces: IntArray, count: int, seed: int) -> FloatArray:
    """Area-weighted uniform random points on a triangle surface (seeded)."""
    area, _, _ = face_geometry(vertices, faces)
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(faces), size=count, p=area / area.sum())
    u, v = rng.random(count), rng.random(count)
    flip = u + v > 1
    u, v = np.where(flip, 1 - u, u), np.where(flip, 1 - v, v)
    a, b, c = (vertices[faces[pick, k]] for k in range(3))
    return a + u[:, None] * (b - a) + v[:, None] * (c - a)


def deviation_report(vertices: FloatArray, faces: IntArray, ref_vertices: FloatArray, ref_faces: IntArray,
                     samples: int = 20000, seed: int = 20261116) -> dict:
    """Metric 8 (relative part): sampled two-sided deviation to a reference surface (exact point-triangle)."""
    import trimesh  # local import: only needed when a reference is supplied

    def one_way(src_v, src_f, dst_v, dst_f) -> FloatArray:
        mesh = trimesh.Trimesh(dst_v, dst_f, process=False)
        points = sample_surface(src_v, src_f, samples, seed)
        _, distance, _ = trimesh.proximity.closest_point(mesh, points)
        return distance

    forward = one_way(vertices, faces, ref_vertices, ref_faces)
    backward = one_way(ref_vertices, ref_faces, vertices, faces)
    return {"samples_each_way": samples, "seed": seed,
            "surface_to_reference_m": distribution(forward), "reference_to_surface_m": distribution(backward),
            "max_two_sided_m": float(max(forward.max(), backward.max()))}

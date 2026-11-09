#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "matplotlib", "pydantic"]
# ///
# How to run: uv run assemble_map.py (from the repository root).
from __future__ import annotations

import hashlib
import importlib.metadata
import itertools
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
from matplotlib.collections import PolyCollection

matplotlib.use("Agg")
import numpy as np
from exact_contacts import audit_contact
from inspect_locations import TriangleMetrics
from locate_intersections import DiagnosticError, load_stl
from pydantic import BaseModel, ConfigDict

ROOT = Path("research/a321-quality")
OUT = ROOT / "m3/c15-map"
INPUT = ROOT / "rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl"


class Part(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    axis: int
    stations_m: list[float]
    bounds_m: list[list[float]]


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)
    parts: list[Part]


class ContactPair(BaseModel):
    model_config = ConfigDict(frozen=True)
    triangles: list[int]
    shared_vertices: int


class LocalLocation(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    id: int
    world_m: list[float]
    triangles: list[TriangleMetrics]
    ray_pairs: list[ContactPair]


class Inspection(BaseModel):
    model_config = ConfigDict(frozen=True)
    locations: list[LocalLocation]


class ScanResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256_before: str
    sha256_after: str
    pair_count: int
    cluster_count: int


@dataclass(frozen=True, slots=True)
class PairGeometry:
    triangles: tuple[int, int]
    shared_vertex_count: int
    normal_angle_deg: float
    dihedral_definition: str = "angle between oriented facet normals; 0 = coplanar aligned"
    status: str = "local adjacent contact candidate, not an independently confirmed crossing"
    rational_beyond_shared_topology: bool = False
    exact_contact_vertices_m: tuple[tuple[float, ...], ...] = ()


def main() -> None:
    started = time.perf_counter()
    source_path = Path("research/a321-integration/evidence/reconstruction-r3.json")
    source = Source.model_validate_json(source_path.read_bytes())
    inspection = Inspection.model_validate_json((OUT / "local-inspection.json").read_bytes())
    independent = ScanResult.model_validate_json((OUT / "independent-scan.json").read_bytes())
    unique_count = len({tuple(loc.world_m) for loc in inspection.locations})
    if len(inspection.locations) != 15 or unique_count != 14 or independent.pair_count != 0 or independent.cluster_count != 0:
        raise DiagnosticError("Evidence differs from this diagnostic's declared 15/14/0 contract")
    if inspection.locations[0].world_m != inspection.locations[1].world_m:
        raise DiagnosticError("Expected duplicate OBJ records 1 and 2 differ")
    triangles = load_stl(INPUT)
    locations = []
    for loc in inspection.locations:
        point = np.array(loc.world_m)
        inside = []
        for part in source.parts:
            probe = point.copy()
            if part.axis == 1:
                probe[1] = abs(probe[1])
            if np.all(probe >= np.array(part.bounds_m[0]) - 1e-4) and np.all(probe <= np.array(part.bounds_m[1]) + 1e-4):
                inside.append(part.name)
        fuselage = next(part for part in source.parts if part.name == "fuselage")
        station_index = int(np.argmin(np.abs(np.array(fuselage.stations_m) - point[0])))
        by_id = {t.index: t for t in loc.triangles if t.point_distance_m <= 1e-4}
        adjacent = []
        for a, b in itertools.combinations(by_id.values(), 2):
            va, vb = np.array(a.vertices_m), np.array(b.vertices_m)
            shared = int(np.any(np.all(va[:, None] == vb[None, :], axis=2), axis=1).sum())
            if shared:
                angle = float(np.degrees(np.arccos(np.clip(np.dot(a.normal, b.normal), -1, 1))))
                beyond, exact_points = audit_contact(va, vb)
                adjacent.append(asdict(PairGeometry((a.index, b.index), shared, angle,
                                  rational_beyond_shared_topology=beyond,
                                  exact_contact_vertices_m=tuple(tuple(p) for p in exact_points))))
        if len(by_id) == 2:
            group = "A_shared_diagonal_contact"
            feature = "other"
            cause = "Shared-edge coplanar/near-coplanar facet contact; likely edge/face numerical classification sensitivity, not a non-adjacent crossing (unconfirmed)."
        elif abs(point[1]) < 1e-10:
            group = "B_mirror_centerline_seam"
            feature = "section ring seam"
            cause = "Mirrored fuselage crown meets at the shared centerline seam; likely endpoint/edge classification sensitivity (unconfirmed)."
        else:
            group = "C_ring_vertex_fan"
            feature = "section ring seam"
            cause = "Station/shoulder ring vertex fan; likely shared-vertex edge/face classification sensitivity (unconfirmed)."
        locations.append({
            "id": loc.id, "world_coordinates_m": loc.world_m,
            "coordinate_authority": "surfacecheck-nMM86x/selfInterPoints.obj; six significant digits; duplicate rows retained",
            "duplicate_of": 1 if loc.id == 2 else None,
            "component": inside[0] if len(inside) == 1 else "unknown", "component_candidates_from_m1_bounds": inside,
            "side_convention": "not applicable: fuselage; no L/R wing/tail events",
            "feature_class": feature, "feature_confidence": "geometric inference, not a preserved generator face tag",
            "nearest_original_station": {"index": station_index, "x_m": fuselage.stations_m[station_index], "delta_x_m": float(point[0] - fuselage.stations_m[station_index])},
            "intersecting_triangle_pairs": [],
            "pair_identity_status": "UNKNOWN: OBJ omits edge/facet IDs; no non-adjacent independent crossing; adjacent candidate identities below are not authoritative surfaceCheck hit IDs",
            "adjacent_triangle_pair_candidates": adjacent,
            "triangle_metrics": [asdict(t) for t in by_id.values()],
            "quality_definitions": {"equilateral_quality": "4*sqrt(3)*area/sum(edge^2)", "radius_ratio_quality": "2*inradius/circumradius = 16*area^2/(perimeter*a*b*c); analytic metric; equivalence to OpenFOAM printed quality NOT established"},
            "cause_group": group, "likely_cause": cause,
            "independent_cluster_ids": [],
        })
    before = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    if before != independent.sha256_before or before != independent.sha256_after:
        raise DiagnosticError("Candidate SHA differs from independent scan")
    result = {
        "status": "M3_FAIL_RETAINED; DIAGNOSTIC_DISCREPANCY_UNRESOLVED", "candidate": "R5-C",
        "input_sha256_before": independent.sha256_before, "input_sha256_after": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "input": str(INPUT), "units": "metres, world STL coordinates",
        "stl_indexing": "zero-based binary STL facet order; no welding/reordering",
        "source_ledger": str(ROOT / "evidence/r5-m1-source-ledger.json"),
        "source_station_and_bbox_file": str(source_path), "source_station_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "surfacecheck_reported_count": 15, "surfacecheck_obj_rows": len(locations), "unique_printed_coordinates": unique_count,
        "independent_pair_count": independent.pair_count, "independent_cluster_count": independent.cluster_count,
        "method": "See independent-scan.json: rtree AABB + plane cuts/interval overlap, exact shared-vertex exclusion, fixed 1e-12 m epsilon; authoritative OBJ matched to local AABBs within fixed 1e-4 m for six-digit text rounding; closest-point filter; all adjacent candidate pairs retained",
        "tool_versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "trimesh", "rtree", "matplotlib", "pydantic")},
        "surfacecheck_version": "OpenFOAM 1912 patch=200626, label32 scalar64",
        "cause_groups_are_hypotheses": True,
        "cause_groups": {name: sum(l["cause_group"] == name for l in locations) for name in ("A_shared_diagonal_contact", "B_mirror_centerline_seam", "C_ring_vertex_fan")},
        "locations": locations,
    }
    if (OUT / "c15-map.svg").exists() or (OUT / "c15-map.png").exists():
        raise FileExistsError("Map already exists; preserve the attempt before rerunning")
    with (OUT / "c15-locations.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), constrained_layout=True)
    for ax, coordinate, title in zip(axes, (1, 2), ("Top view (X/Y)", "Side view (X/Z)")):
        collection = PolyCollection(triangles[:, :, [0, coordinate]], facecolors="#c4ced6", edgecolors="none", rasterized=True)
        ax.add_collection(collection)
        ax.autoscale_view()
        unique = [loc for loc in locations if loc["id"] != 2]
        ordered = sorted(unique, key=lambda loc: loc["world_coordinates_m"][0])
        for k, loc in enumerate(ordered):
            p = loc["world_coordinates_m"]
            label = "1 / 2" if loc["id"] == 1 else str(loc["id"])
            text_y = (20 if coordinate == 1 else 14) + (1.5 if k % 2 else 0)
            ax.plot(p[0], p[coordinate], "o", color="#c62828", ms=4)
            ax.annotate(label, (p[0], p[coordinate]), (1 + k * 2.35, text_y), ha="center", fontsize=10,
                        bbox={"boxstyle": "round,pad=.2", "fc": "white", "ec": "#c62828"},
                        arrowprops={"arrowstyle": "-", "color": "#a84b4b", "lw": .7})
        ax.set(xlim=(-1, 46), ylim=(-18 if coordinate == 1 else 0, 24 if coordinate == 1 else 17), xlabel="X [m]", ylabel=f"{'Y' if coordinate == 1 else 'Z'} [m]", title=title)
        ax.set_aspect("equal")
        ax.grid(alpha=.2)
    fig.suptitle("R5-C: 15 surfaceCheck records / 14 printed coordinates\nIndependent non-adjacent intersections: 0; discrepancy unresolved; M3 FAIL retained", fontsize=15)
    fig.savefig(OUT / "c15-map.svg", dpi=180)
    fig.savefig(OUT / "c15-map.png", dpi=180)
    plt.close(fig)
    print(f"Mapped {len(locations)} records. Cause groups: {result['cause_groups']}. Wall seconds: {time.perf_counter() - started:.3f}")


if __name__ == "__main__":
    main()

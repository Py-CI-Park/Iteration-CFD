#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "pymeshlab"]
# ///
"""R6 surface gate suite: measures closure, orientation, self-intersection (3 checkers),
triangle quality, size grading, smoothness, station kinks, feature exclusion and geometry deltas.

It measures; it does not set thresholds. Structural facts (closed, outward, zero intersections)
are reported as booleans next to the counts they come from.

How to run: uv run --no-project r6_gate.py --surface name=path.stl [--surface ...] --out report.json
  --checkers locator,meshlab,surfacecheck   (default: all three; "not run" is recorded as null)
  --features features.json                   feature polylines (see r6_metrics.feature_mask)
  --stations reconstruction-r3.json          station parts (name, axis, stations_m, reference_bounds_m)
  --deviation name=reference.stl             sampled two-sided deviation for that surface
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from r6_mesh import GateError, closure_and_orientation, load_stl, sha256_file, weld
from r6_metrics import (bbox_and_volume, deviation_report, grading_report, quality_report, smoothness_report,
                        station_kink_report)
from r6_selfint import (agreement, locator_check, meshlab_check, obj_points, points_covered_by_faces,
                        surfacecheck_run)

CHECKERS = ("locator", "meshlab", "surfacecheck")


def parse_pairs(items: list[str]) -> dict[str, Path]:
    """name=path arguments."""
    out: dict[str, Path] = {}
    for item in items:
        name, _, path = item.partition("=")
        if not name or not path:
            raise GateError(f"Expected name=path, got {item!r}")
        out[name] = Path(path)
    return out


def part_box(part: dict, pad: float = 1e-3) -> list[list[float]]:
    """Padded bounds of a part; the span axis (y) is mirrored about zero for wing and horizontal tail."""
    lo, hi = (np.array(b, dtype=float) for b in part["reference_bounds_m"])
    if part["axis"] == 1:
        lo[1] = -hi[1]
    return [(lo - pad).tolist(), (hi + pad).tolist()]


def station_parts(path: Path | None, surface_name: str) -> list[dict]:
    """Station parts for a surface. A surface whose name contains a part name uses only that part with no
    region; any other (union/other) surface uses every part restricted to its own bounds minus the other
    parts' bounds (approximate: shared bounds mean edges in the overlap are dropped, not attributed)."""
    if path is None:
        return []
    parts = json.loads(path.read_text(encoding="utf-8"))["parts"]
    named = [p for p in parts if p["name"] in surface_name]
    out = []
    for part in named or parts:
        item = {"name": part["name"], "axis": part["axis"], "stations_m": part["stations_m"]}
        if not named:
            item["region_bbox_m"] = part_box(part)
            item["exclude_bboxes_m"] = [part_box(o) for o in parts if o is not part]
        out.append(item)
    return out


def run_selfint(name: str, path: Path, triangles: np.ndarray, checkers: list[str], log_dir: Path) -> dict:
    """Run the requested checkers; unrequested ones are None. Raw face-id lists go to a side file."""
    locator = locator_check(triangles) if "locator" in checkers else None
    meshlab = meshlab_check(path, log_dir / f"{name}-meshlab.json") if "meshlab" in checkers else None
    surface = surfacecheck_run(name, path) if "surfacecheck" in checkers else None
    result = {"locator": locator, "meshlab": meshlab, "surfacecheck": surface,
              "agreement": agreement(locator, meshlab, surface, len(triangles))}
    if surface is not None and surface["obj_points_m"]:
        points = np.array(surface["obj_points_m"])
        cover = {}
        if locator is not None:
            cover["obj_points_near_locator_faces"] = points_covered_by_faces(points, triangles, locator["face_ids"])
        if meshlab is not None:
            cover["obj_points_near_meshlab_faces"] = points_covered_by_faces(points, triangles, meshlab["selected_face_ids"])
        cover["obj_points_total"] = len(points)
        cover["radius_m"] = 1e-4
        result["agreement"]["surfacecheck_point_coverage"] = cover
    return result


def analyse(name: str, path: Path, args: argparse.Namespace) -> dict:
    """All metrics for one surface file, with SHA before and after."""
    started = time.perf_counter()
    sha_before = sha256_file(path)
    triangles = load_stl(path)
    vertices, faces = weld(triangles)
    topo, edges = closure_and_orientation(vertices, faces)
    features = json.loads(args.features.read_text(encoding="utf-8")) if args.features else None
    report: dict = {"name": name, "path": str(path), "triangles": len(triangles), "closure_orientation": topo,
                    "quality": quality_report(vertices, faces), "grading": grading_report(vertices, faces, edges),
                    "smoothness": smoothness_report(vertices, faces, edges, features),
                    "station_kink": station_kink_report(vertices, faces, edges, station_parts(args.stations, name)),
                    "geometry": bbox_and_volume(vertices, topo["signed_volume_total_m3"])}
    if name in args.deviation:
        ref_vertices, ref_faces = weld(load_stl(args.deviation[name]))
        report["geometry"]["deviation_to_reference"] = deviation_report(vertices, faces, ref_vertices, ref_faces)
        report["geometry"]["reference_path"] = str(args.deviation[name])
    report["self_intersection"] = run_selfint(name, path, triangles, args.checkers, args.log_dir)
    sha_after = sha256_file(path)
    report.update({"sha256_before": sha_before, "sha256_after": sha_after, "sha256_unchanged": sha_before == sha_after,
                   "wall_seconds": time.perf_counter() - started})
    if sha_before != sha_after:
        raise GateError(f"Input SHA changed for {name}")
    return report


def slim_for_summary(report: dict) -> dict:
    """Drop the large face-id lists from a copy of the report (they stay in the side files)."""
    out = json.loads(json.dumps(report))
    selfint = out["self_intersection"]
    if selfint["locator"] is not None:
        selfint["locator"].pop("face_ids", None)
    if selfint["meshlab"] is not None:
        selfint["meshlab"].pop("selected_face_ids", None)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--surface", action="append", required=True, help="name=path.stl (repeatable)")
    parser.add_argument("--features", type=Path)
    parser.add_argument("--stations", type=Path)
    parser.add_argument("--deviation", action="append", default=[], help="name=reference.stl")
    parser.add_argument("--checkers", default=",".join(CHECKERS))
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.deviation = parse_pairs(args.deviation)
    args.checkers = [c for c in args.checkers.split(",") if c]
    if not set(args.checkers) <= set(CHECKERS):
        raise GateError(f"Unknown checker in {args.checkers}")
    args.log_dir.mkdir(parents=True, exist_ok=True)
    reports = {name: analyse(name, path, args) for name, path in parse_pairs(args.surface).items()}
    for name, report in reports.items():
        side = args.log_dir / f"{name}-full-report.json"
        with side.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, allow_nan=False)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump({n: slim_for_summary(r) for n, r in reports.items()}, stream, indent=1, allow_nan=False)
    for name, report in reports.items():
        print(name, "triangles", report["triangles"], "wall", round(report["wall_seconds"], 1), "s")


if __name__ == "__main__":
    main()

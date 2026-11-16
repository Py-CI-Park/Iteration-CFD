#!/usr/bin/env -S uv run --script
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
"""R6-a generator: station ledger -> four closed component surfaces (npz) + feature manifest.

Method: contract r6-geometry-contract-02 as clarified by 02b. Ledger points stay vertices; circumferential
insertions, graded rows, C2-unless-overshoot-then-Fritsch-Carlson lines, planar caps without pole fans.

How to run: python build_r6.py --out-dir <new dir> [--aspect-fuselage 12 --aspect-wing 22 ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_dev
import r6_flip
import r6_grid
import r6_io
import r6_ledger
import r6_tess

NAMES = ("fuselage", "wing", "horizontal", "vertical")
FEATURE_TOL_M = 1e-4


def _boundary_directed(faces: np.ndarray, boundary: np.ndarray) -> set:
    """Directed edges of faces whose undirected edge is a consecutive pair of the boundary loop."""
    big = int(max(faces.max(), boundary.max())) + 1
    keys = np.minimum(boundary, np.roll(boundary, -1)) * big + np.maximum(boundary, np.roll(boundary, -1))
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    ekey = np.minimum(edges[:, 0], edges[:, 1]) * big + np.maximum(edges[:, 0], edges[:, 1])
    hit = edges[np.isin(ekey, keys)]
    return {(int(u), int(v)) for u, v in hit}


def orient_cap(grid_faces: np.ndarray, cap_faces: list, boundary: np.ndarray) -> list:
    """Flip a cap's faces if it traverses a shared boundary edge in the same direction as the grid does."""
    grid_dir = _boundary_directed(grid_faces, boundary)
    cap_dir = _boundary_directed(np.asarray(cap_faces, dtype=np.int64), boundary)
    return [(f[0], f[2], f[1]) for f in cap_faces] if grid_dir & cap_dir else cap_faces


def ring_ids_of_row(row: int, n_col: int) -> np.ndarray:
    return row * n_col + np.arange(n_col)


def add_caps(grid: r6_grid.Grid, vertices: np.ndarray, faces: np.ndarray, cap_density: float = 1.0):
    """Append planar caps at the first and last row. Returns vertices, faces, cap records."""
    part, n_col = grid.part, grid.plane.shape[1]
    records, all_faces = [], [faces]
    for label, row in (("first", 0), ("last", len(grid.t_rows) - 1)):
        ids = ring_ids_of_row(row, n_col)
        if part.name == "fuselage":
            new, cap = r6_tess.round_cap(vertices, ids)
            cols = None
        else:
            te_col = int(np.flatnonzero(np.isclose(grid.taus, part.corners[0]))[0])
            new, cap, cols = r6_tess.airfoil_cap(vertices, ids, te_col, max_rows=int(round(12 * cap_density)), density=cap_density)
        cap = orient_cap(np.vstack(all_faces), cap, ids)
        start = len(vertices)
        vertices = np.vstack([vertices, new])
        all_faces.append(np.asarray(cap, dtype=np.int64))
        records.append({"label": label, "row": row, "boundary_ids": ids.tolist(), "new_vertices": [start, len(vertices)],
                        "triangles": len(cap), "kind": "round" if cols is None else "airfoil-strip"})
    return vertices, np.vstack(all_faces), records


def signed_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    tri = vertices[faces]
    return float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)


def valence(faces: np.ndarray, count: int) -> np.ndarray:
    """Number of distinct edge neighbours of every vertex."""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    return np.bincount(e.ravel(), minlength=count)


def feature_sets(grid: r6_grid.Grid, caps: list) -> list[dict]:
    """Declared feature lines as vertex-index polylines (TE, tip/cap boundaries, kink rows, closure rows)."""
    part, n_col = grid.part, grid.plane.shape[1]
    out = []
    if part.corners:
        te_col = int(np.flatnonzero(np.isclose(grid.taus, part.corners[0]))[0])
        out.append({"name": "trailing_edge", "kind": "TE", "ids": (np.arange(len(grid.t_rows)) * n_col + te_col).tolist(), "closed": False})
    for cap in caps:
        out.append({"name": f"cap_boundary_{cap['label']}", "kind": "cap_boundary", "ids": cap["boundary_ids"], "closed": True})
    for k in grid.kinks:
        row = grid.station_rows[k["index"]]
        out.append({"name": f"planform_kink_station_{k['index']}", "kind": "planform_kink", "span_m": k["span_m"],
                    "slope_change_deg": k["curves"], "ids": ring_ids_of_row(row, n_col).tolist(), "closed": True})
    for i, row in zip(grid.records["closure_station_indices"], grid.closure_rows, strict=True):
        out.append({"name": f"closure_band_boundary_station_{i}", "kind": "closure_band", "ids": ring_ids_of_row(row, n_col).tolist(), "closed": True})
    return out


def cap_end_spacing(vertices: np.ndarray, faces: np.ndarray, caps: list, n_grid_faces: int) -> list[np.ndarray]:
    """Per cap: for every boundary edge j the strip height h_j = 2 * A_cap_j / e_j that would match the cap triangle on it."""
    out, start = [], n_grid_faces
    for cap in caps:
        cap_faces = faces[start:start + cap["triangles"]]
        start += cap["triangles"]
        ring = np.asarray(cap["boundary_ids"])
        nxt = np.roll(ring, -1)
        tri = vertices[cap_faces]
        area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        big = len(vertices)
        area_of = {}
        for (a, b, c), ar in zip(cap_faces, area, strict=True):
            for u, w in ((a, b), (b, c), (c, a)):
                area_of[min(u, w) * big + max(u, w)] = ar
        e = np.linalg.norm(vertices[nxt] - vertices[ring], axis=1)
        a_j = np.array([area_of[min(u, w) * big + max(u, w)] for u, w in zip(ring, nxt, strict=True)])
        h = 2.0 * a_j / e
        out.append(h)
    return out


def load_limits() -> dict:
    """02a per-triangle limits used by the 02d flip rule."""
    th = json.loads((Path(__file__).resolve().parents[1] / "plans/r6-geometry-contract-02a.json").read_text())["thresholds_per_component"]
    return {k: th[k]["value"] for k in ("Q_MIN", "ANGLE_MIN_DEG", "ASPECT_MAX", "GRADE_AREA_MAX", "VALENCE_MAX")}


def apply_flip(built: dict) -> dict:
    """Contract 02d edge flip on a finished component; connectivity only (vertices untouched)."""
    manifest = built["manifest"]
    feature_edges = set()
    for f in manifest["features"]:
        ids = list(f["ids"]) + ([f["ids"][0]] if f["closed"] else [])
        feature_edges |= {(min(a, b), max(a, b)) for a, b in zip(ids[:-1], ids[1:], strict=True)}
    faces, record = r6_flip.flip_axis_parallel(built["vertices"], built["faces"], feature_edges, load_limits())
    val = valence(faces, len(built["vertices"]))
    manifest.update({"max_valence": int(val.max()), "valence_histogram": np.bincount(val).tolist(), "edge_flip": record})
    return {**built, "faces": faces}


def build_component(part: r6_ledger.Part, params: r6_grid.GridParams, tess: str = "quad", flip: bool = False, surface=None) -> dict:
    built = _build_component(part, params, tess, surface)
    return apply_flip(built) if flip else built


def _build_component(part: r6_ledger.Part, params: r6_grid.GridParams, tess: str = "quad", surface=None) -> dict:
    if part.name != "fuselage" and params.end_h == (-1.0, -1.0):  # auto: measure the caps on a first pass, rebuild with matched ends
        first = _build_component(part, replace(params, end_h=(0.0, 0.0)), tess)
        n_faces = first["manifest"]["grid_triangles"]
        h_j = cap_end_spacing(first["vertices"], first["faces"], first["manifest"]["caps"], n_faces)
        guess = [float(np.sqrt(h.min() * h.max())) for h in h_j]
        end_h, best = list(guess), None
        for attempt in range(6):  # strip height per column differs (line speed), so rescale the imposed spacing from the realised strips
            built = _build_component(part, replace(params, end_h=(end_h[0], end_h[1])), tess)
            pts = built["grid"].points3d()
            length = [np.linalg.norm(pts[1] - pts[0], axis=1), np.linalg.norm(pts[-2] - pts[-1], axis=1)]
            ratio = [0.5 * (L + np.roll(L, -1)) / h for L, h in zip(length, h_j, strict=True)]  # realised strip height / matching height, per edge
            factor = [1.0 / np.sqrt(r.max() * r.min()) for r in ratio]
            err = max(abs(np.log(f)) for f in factor)
            spread = max(np.sqrt(r.max() / r.min()) for r in ratio)
            if best is None or err < best[0]:
                best = (err, built, list(end_h), spread)
            if err < 0.08:
                break
            end_h = [h * f for h, f in zip(end_h, factor, strict=True)]
        target = guess
        if params.end_bias != 1.0:  # deliberate shift of the balanced end spacing toward taller strips (angle gate vs area-ratio gate)
            built = _build_component(part, replace(params, end_h=(best[2][0] * params.end_bias, best[2][1] * params.end_bias)), tess)
            best = (best[0], built, [h * params.end_bias for h in best[2]], best[3])
        built = best[1]
        built["manifest"]["end_spacing_m"] = {"initial_first_last": target, "imposed_first_last": best[2], "column_spread_sqrt_max_over_min": best[3], "passes": attempt + 1,
                                              "rule": "start sqrt(min*max) of h_j=2*A_cap/edge; rescale so sqrt(max*min) of realised first-strip height / h_j over boundary edges is 1"}
        return built
    grid = r6_grid.build_grid(part, params, surface)
    points = grid.points3d()
    leaning: list[int] = []
    if tess == "lean":
        vertices, faces, leaning = r6_tess.lean_triangles(points)
    else:
        vertices, faces = r6_tess.grid_triangles(points)
    n_grid_vertices, n_grid_faces = len(vertices), len(faces)
    vertices, faces, caps = add_caps(grid, vertices, faces, params.cap_density)
    vertices = vertices.astype(np.float32).astype(np.float64)  # float32-exact (Blender stores float32)
    if signed_volume(vertices, faces) < 0:
        faces = faces[:, ::-1].copy()
    val = valence(faces, len(vertices))
    features = feature_sets(grid, caps)
    manifest = {
        "name": part.name, "vertices": len(vertices), "triangles": len(faces), "grid_rows": len(grid.t_rows),
        "grid_columns": int(grid.plane.shape[1]), "tessellation": tess, "leaning_strips": len(leaning),
        "leaning_strip_rows": leaning if len(leaning) <= 400 else f"{len(leaning)} strips (list omitted)", "grid_vertices": n_grid_vertices, "grid_triangles": n_grid_faces,
        "max_valence": int(val.max()), "valence_histogram": np.bincount(val).tolist(),
        "signed_volume_m3": signed_volume(vertices, faces),
        "ring_curve_kinds": grid.records["ring_curve_kinds"], "inserted_points_per_ledger_segment": grid.records["inserted_per_segment"],
        "line_interpolation_per_segment": grid.records["line_method"],
        "kinks_detected": grid.records["kinks"], "caps": caps, "features": features,
        "te": "sharp trailing-edge vertex per section (ledger chord_hull layout); declared feature line" if part.corners else "none (smooth closed rings)",
    }
    return {"vertices": vertices, "faces": faces, "manifest": manifest, "grid": grid}


def to_gate_features(vertices: np.ndarray, features: list[dict]) -> dict:
    """Coordinate polylines for r6_gate.py --features."""
    items = []
    for f in features:
        ids = list(f["ids"]) + ([f["ids"][0]] if f["closed"] else [])
        items.append({"name": f["name"], "polyline": vertices[ids].tolist()})
    return {"tolerance_m": FEATURE_TOL_M, "origin": "R6-a feature manifest (vertex polylines resolved to coordinates)", "features": items}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--aspect-fuselage", type=float, default=1.0)
    ap.add_argument("--aspect-wing", type=float, default=1.0)  # wing and horizontal tail
    ap.add_argument("--aspect-vertical", type=float, default=1.0)
    ap.add_argument("--percentile-fuselage", type=float, default=5.0)
    ap.add_argument("--percentile-wing", type=float, default=5.0)
    ap.add_argument("--hard-factor", type=float, default=30.0)
    ap.add_argument("--insertion-cap", type=int, default=3)
    ap.add_argument("--turn-limit", type=float, default=10.0)
    ap.add_argument("--grade", type=float, default=1.25)
    ap.add_argument("--h-max", type=float, default=0.125)
    ap.add_argument("--end-match", action="store_true", help="airfoil parts: measure the planar caps and set the end row spacing so strip and cap faces match")
    ap.add_argument("--flip", action="store_true", help="02d: flip exactly axis-parallel edges to the other diagonal where the 02d rule allows")
    ap.add_argument("--dev-limit", type=float, default=0.0, help="02d: fuselage lines use Fritsch-Carlson when C2 deviates more than this (m) from R3; 0 = off")
    ap.add_argument("--long-turn", type=float, default=0.0, help="max turning (deg) of a grid line between rows; 0 = off")
    ap.add_argument("--end-bias", type=float, default=1.0)
    ap.add_argument("--cap-density", type=float, default=1.0)
    ap.add_argument("--tess", choices=("quad", "lean"), default="quad", help="quad: max-min-angle diagonal (02); lean: leaning strip (02c)")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    parts = r6_ledger.load_parts()
    base = r6_grid.GridParams(turn_limit_deg=args.turn_limit, grade=args.grade, h_max=args.h_max,
                              hard_factor=args.hard_factor, insertion_cap=args.insertion_cap, cap_density=args.cap_density, end_bias=args.end_bias, long_turn_deg=args.long_turn, dev_limit_m=args.dev_limit)
    contracts = ["r6-geometry-contract-02", "r6-geometry-contract-02a", "r6-geometry-contract-02b"]
    contracts += ["r6-geometry-contract-02c"] if args.tess == "lean" else []
    contracts += ["r6-geometry-contract-02d"] if (args.flip or args.dev_limit > 0) else []
    r3_fuselage = None
    if args.dev_limit > 0:
        tri = r6_io.read_stl(r6_ledger.R3_DIR / "fuselage.stl").astype(np.float64)
        r3_fuselage = r6_dev.TriangleSurface(tri)
    manifest = {"contract": contracts, "tessellation": args.tess,
                "ledger_sha256": r6_ledger.LEDGER_SHA, "parts": {}, "params": {}}
    for name in NAMES:
        params = replace(base, aspect_factor={"fuselage": args.aspect_fuselage, "vertical": args.aspect_vertical}.get(name, args.aspect_wing),
                         ref_percentile=args.percentile_fuselage if name == "fuselage" else args.percentile_wing,
                         end_h=(-1.0, -1.0) if args.end_match else (0.0, 0.0))
        built = build_component(parts[name], params, args.tess, flip=args.flip, surface=r3_fuselage if name == "fuselage" else None)
        np.savez_compressed(args.out_dir / f"{name}.npz", vertices=built["vertices"], faces=built["faces"])
        manifest["parts"][name] = built["manifest"]
        manifest["params"][name] = asdict(params)
        (args.out_dir / f"features-{name}.json").write_text(json.dumps(to_gate_features(built["vertices"], built["manifest"]["features"])), encoding="utf-8")
        m = built["manifest"]
        print(name, "vertices", m["vertices"], "triangles", m["triangles"], "max valence", m["max_valence"], "volume", round(m["signed_volume_m3"], 6))
    (args.out_dir / "feature-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("sha256 feature-manifest", hashlib.sha256((args.out_dir / "feature-manifest.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()

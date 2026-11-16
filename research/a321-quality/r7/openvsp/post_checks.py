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
"""Follow-up checks: (a) distance of the surfaceCheck record points to the junction components, (b) R3 and OpenVSP
fuselage lower contour near the 188 mm deviation, (c) location of the worst vertex mirror error.
How to run: uv run --no-project ../../r7/openvsp/post_checks.py --out ../../r7/openvsp/post-checks.json"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
W = REPO / ".worktmp" / "r7-openvsp"


def read_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    n = int.from_bytes(raw[80:84], "little")
    dt = np.dtype([("n", "<f4", (3,)), ("t", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(raw, dtype=dt, count=n, offset=84)["t"].astype(np.float64)


def mesh_of(tri: np.ndarray) -> trimesh.Trimesh:
    return trimesh.Trimesh(vertices=tri.reshape(-1, 3), faces=np.arange(len(tri) * 3).reshape(-1, 3), process=False)


def slice_x(tri: np.ndarray, c: float) -> np.ndarray:
    out = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        pa, pb = tri[:, a], tri[:, b]
        da, db = pa[:, 0] - c, pb[:, 0] - c
        m = da * db < 0
        t = da[m] / (da[m] - db[m])
        out.append(pa[m] + t[:, None] * (pb[m] - pa[m]))
    return np.vstack(out)


def lower_z_at(points: np.ndarray, y: float) -> float:
    """Lower contour z at y by linear interpolation of the slice points below the slice mid-height."""
    low = points[points[:, 2] < 0.5 * (points[:, 2].min() + points[:, 2].max())]
    order = np.argsort(low[:, 1])
    return float(np.interp(y, low[order, 1], low[order, 2]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out: dict = {}
    print("start", flush=True)
    # (a) surfaceCheck record points vs the junction components
    attempts = sorted((HERE / "sc" / "attempts").glob("sc-union_obj-*"))
    pts = np.array([[float(t) for t in ln.split()[1:4]] for ln in (attempts[-1] / "selfInterPoints.obj").read_text().splitlines() if ln.startswith("v ")])
    dist = {}
    for name in ("wing", "horizontal", "vertical"):
        tri = read_stl(W / f"openvsp_{name}.stl")
        q = pts.copy()
        if name in ("wing", "horizontal"):
            q[:, 1] = np.abs(q[:, 1])
        _, d, _ = trimesh.proximity.closest_point(mesh_of(tri), q)
        dist[name] = d
    print("distances done", flush=True)
    dmin = np.min(np.stack(list(dist.values())), axis=0)
    out["surfacecheck_union_records"] = {"records": int(len(pts)), "min_distance_to_wing_horizontal_vertical_surface_m": {"min": float(dmin.min()), "p50": float(np.median(dmin)), "max": float(dmin.max())},
                                         "within_5mm": int((dmin < 0.005).sum()), "within_50mm": int((dmin < 0.05).sum()), "within_100mm": int((dmin < 0.1).sum()),
                                         "per_component_within_50mm": {k: int((v < 0.05).sum()) for k, v in dist.items()},
                                         "x_range_of_points_within_50mm": [float(pts[dmin < 0.05][:, 0].min()), float(pts[dmin < 0.05][:, 0].max())] if (dmin < 0.05).any() else None}
    # (b) lower fuselage contour, R3 vs OpenVSP, at the station of the worst 20-24 m deviation and two reference stations
    r3 = read_stl(REPO / "research/a321-integration/artifacts/shell-r3/fuselage.stl")
    ov = read_stl(W / "openvsp_fuselage.stl")
    rows = []
    for x in (15.0, 21.75, 25.0):
        for y in (-0.94, -0.5, 0.0, 0.5, 0.94, 1.5):
            rows.append({"x": x, "y": y, "r3_lower_z": lower_z_at(slice_x(r3, x), y), "openvsp_lower_z": lower_z_at(slice_x(ov, x), y)})
    out["lower_contour_r3_vs_openvsp"] = rows
    print("slices done", flush=True)
    # (c) worst vertex mirror error
    u = read_stl(W / "openvsp_union.stl").reshape(-1, 3)
    v = np.unique(u, axis=0)
    d, _ = cKDTree(v).query(v * np.array([1.0, -1.0, 1.0]))
    j = int(np.argmax(d))
    out["worst_vertex_mirror_error"] = {"max_m": float(d[j]), "location_xyz_m": v[j].round(4).tolist(), "float32_step_at_x_m": float(np.spacing(np.float32(v[j][0])))}
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

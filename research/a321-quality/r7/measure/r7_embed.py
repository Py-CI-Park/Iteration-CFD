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
"""A5 root embedment and junction-loop analysis against the ANALYTIC R7 fuselage (task 6). The reused component STLs
are only read. The fuselage is the implicit function of r7_model, so no fuselage surface exists yet."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from r7_model import X_HI, X_LO, FuselageModel

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research/a321-quality/r6/gen"))
import r6_io  # noqa: E402
import r6_ledger  # noqa: E402

FloatArray = NDArray[np.float64]
CANDIDATE = REPO / "research/a321-quality/r6/candidates/r6-c/attempt01"
R3_FUSELAGE = REPO / "research/a321-integration/artifacts/shell-r3/fuselage.stl"


def exact_distance(model: FuselageModel, p: FloatArray) -> float:
    """Euclidean distance from p to the analytic surface (positive inside), by local minimisation over (x, theta)."""
    def surf(v: FloatArray) -> FloatArray:
        x, th = float(np.clip(v[0], X_LO, X_HI)), v[1]
        a, zw, bu, bl = (float(q[0]) for q in model.section(np.array([x])))
        b = bu if np.cos(th) >= 0 else bl
        return np.array([x, a * np.sin(th), zw + b * np.cos(th)])

    a, zw, bu, bl = (float(q[0]) for q in model.section(np.array([p[0]])))
    th0 = np.arctan2(p[1] / a, (p[2] - zw) / (bu if p[2] >= zw else bl))
    best = None
    for dx in (0.0, 0.05, -0.05, 0.3, -0.3):
        r = minimize(lambda v: float(np.sum((surf(v) - p) ** 2)), np.array([p[0] + dx, th0]), method="Nelder-Mead", options={"xatol": 1e-9, "fatol": 1e-16, "maxiter": 800})
        if best is None or r.fun < best.fun:
            best = r
    d = float(np.sqrt(best.fun))
    return d if model.implicit(p[None, :])[0] < 0 else -d


def root_station_depth(model: FuselageModel, ring: FloatArray) -> dict:
    """Exact (local minimisation) depth of every root-section vertex; first-order estimate kept for comparison."""
    est = model.signed_distance_estimate(ring)
    exact = np.array([exact_distance(model, q) for q in ring])
    i = int(np.argmin(exact))
    zc_above = model.crown(ring[:, 0])
    return {"n_vertices": int(len(ring)), "min_depth_exact_m": float(exact[i]), "min_depth_first_order_m": float(est.min()),
            "location_xyz_m": [float(v) for v in ring[i]], "n_outside": int((exact < 0).sum()),
            "vertical_overlap_below_crown_min_m": float((zc_above - ring[:, 2]).min()),
            "vertical_overlap_x_of_min_m": float(ring[int(np.argmin(zc_above - ring[:, 2])), 0])}


def station_profile(model: FuselageModel, points: FloatArray, max_stations: int = 14) -> list[dict]:
    """Per-station min depth until the first station with an outside vertex (root portion ledger stations)."""
    out = []
    for k in range(min(max_stations, len(points))):
        est = model.signed_distance_estimate(points[k])
        out.append({"station": k, "min_depth_m": float(est.min()), "n_outside": int((est < 0).sum()), "n": int(len(est))})
        if (est < 0).any():
            break
    return out


def r3_depth(ring: FloatArray) -> dict:
    import trimesh

    mesh = trimesh.Trimesh(*_mesh_arrays(R3_FUSELAGE), process=False)
    sd = trimesh.proximity.signed_distance(mesh, ring)  # positive inside
    i = int(np.argmin(sd))
    return {"min_depth_m": float(sd[i]), "location_xyz_m": [float(v) for v in ring[i]], "n_outside": int((sd < 0).sum()),
            "sign_check_inside_point": float(trimesh.proximity.signed_distance(mesh, np.array([[20.0, 0.0, 4.0]]))[0])}


def _mesh_arrays(path: Path) -> tuple[FloatArray, np.ndarray]:
    tris = r6_io.read_stl(path)
    v, f = r6_io.weld(tris)
    return v, f


# ----------------------------------------------------------------------------------------------- junction loops
def _components(n_nodes: int, edges: list[tuple[int, int]]) -> NDArray[np.int64]:
    parent = np.arange(n_nodes)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return np.array([find(i) for i in range(n_nodes)])


def junction_loops(model: FuselageModel, name: str) -> dict:
    """Closed intersection loops of the component surface with the analytic fuselage and the angle between the surfaces."""
    tris = r6_io.read_stl(CANDIDATE / f"{name}.stl")
    v, f = r6_io.weld(tris)
    fv = model.implicit(v)
    inside = fv < 0
    s = inside[f]
    cross = s.any(axis=1) & ~s.all(axis=1)
    cf = f[cross]
    seg_nodes: dict[tuple[int, int], int] = {}
    edges_pairs: list[tuple[int, int]] = []
    seg_points = []
    seg_face = []
    for fi, tri in zip(np.where(cross)[0], cf, strict=True):
        sg = inside[tri]
        # the vertex whose side differs from the other two
        lone = [i for i in range(3) if sum(sg[j] == sg[i] for j in range(3)) == 1][0]
        others = [i for i in range(3) if i != lone]
        nodes, pts = [], []
        for o in others:
            a, b = int(tri[lone]), int(tri[o])
            key = (min(a, b), max(a, b))
            if key not in seg_nodes:
                seg_nodes[key] = len(seg_nodes)
            t = fv[a] / (fv[a] - fv[b])
            nodes.append(seg_nodes[key])
            pts.append(v[a] + t * (v[b] - v[a]))
        edges_pairs.append((nodes[0], nodes[1]))
        seg_points.append(0.5 * (pts[0] + pts[1]))
        seg_face.append(fi)
    n_nodes = len(seg_nodes)
    comp = _components(n_nodes, edges_pairs)
    labels = comp[[e[0] for e in edges_pairs]]
    uniq = np.unique(labels)
    seg_points = np.array(seg_points)
    face_tri = v[f[np.array(seg_face)]]
    nrm = np.cross(face_tri[:, 1] - face_tri[:, 0], face_tri[:, 2] - face_tri[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-300)
    nf = model.normal(seg_points)
    ang = np.degrees(np.arccos(np.clip(np.abs((nrm * nf).sum(1)), 0.0, 1.0)))
    i = int(np.argmin(ang))
    loops = []
    for u in uniq:
        m = labels == u
        pts = seg_points[m]
        loops.append({"n_segments": int(m.sum()), "x_range_m": [float(pts[:, 0].min()), float(pts[:, 0].max())],
                      "y_range_m": [float(pts[:, 1].min()), float(pts[:, 1].max())], "z_range_m": [float(pts[:, 2].min()), float(pts[:, 2].max())],
                      "min_angle_deg": float(ang[m].min()), "x_of_min_angle_m": float(pts[np.argmin(ang[m]), 0])})
    return {"component": name, "n_vertices": int(len(v)), "n_triangles": int(len(f)), "n_crossing_triangles": int(cross.sum()),
            "n_loops": int(len(uniq)), "loops": loops, "min_surface_angle_deg": float(ang.min()),
            "min_angle_location_xyz_m": [float(q) for q in seg_points[i]], "p1_angle_deg": float(np.percentile(ang, 1)),
            "n_segments_below_5deg": int((ang < 5.0).sum())}


def root_ring(name: str) -> tuple[FloatArray, FloatArray]:
    part = r6_ledger.load_parts()[name]
    return part.points[0].reshape(-1, 3), part.points

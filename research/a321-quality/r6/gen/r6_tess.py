# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Tessellation of the R6 structured grids and the planar cap meshes (numpy only)."""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def min_angle_deg(a: FloatArray, b: FloatArray, c: FloatArray) -> FloatArray:
    """Smallest interior angle of triangles (a, b, c), vectorised over leading dimension."""
    def angle(p: FloatArray, q: FloatArray, r: FloatArray) -> FloatArray:
        u, v = q - p, r - p
        cos = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-300)
        return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))

    return np.minimum(np.minimum(angle(a, b, c), angle(b, c, a)), angle(c, a, b))


def grid_triangles(points: FloatArray) -> tuple[FloatArray, IntArray]:
    """Vertices (R*C, 3) and triangles of an R x C grid, columns periodic.

    Each quad (r,c),(r,c+1),(r+1,c+1),(r+1,c) is split along the diagonal that maximises the minimum
    interior angle of the two resulting triangles (ties go to the (r,c)-(r+1,c+1) diagonal).
    """
    rows, cols, _ = points.shape
    vid = np.arange(rows * cols).reshape(rows, cols)
    p00, p01 = vid[:-1, :], np.roll(vid, -1, axis=1)[:-1, :]
    p10, p11 = vid[1:, :], np.roll(vid, -1, axis=1)[1:, :]
    v = points.reshape(-1, 3)
    a, b, c, d = (x.ravel() for x in (p00, p01, p11, p10))
    split_ac = np.minimum(min_angle_deg(v[a], v[b], v[c]), min_angle_deg(v[a], v[c], v[d]))
    split_bd = np.minimum(min_angle_deg(v[a], v[b], v[d]), min_angle_deg(v[b], v[c], v[d]))
    use_ac = split_ac >= split_bd
    t1 = np.where(use_ac[:, None], np.stack([a, b, c], 1), np.stack([a, b, d], 1))
    t2 = np.where(use_ac[:, None], np.stack([a, c, d], 1), np.stack([b, c, d], 1))
    tris = np.empty((2 * len(a), 3), dtype=np.int64)
    tris[0::2], tris[1::2] = t1, t2
    return v.copy(), tris


def _axis_parallel(v32: FloatArray, tris: IntArray, ring_edges_only: bool, cols: int) -> bool:
    """True if any triangle edge that joins two different rings has two exactly equal coordinates (float32 values)."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    if ring_edges_only:
        e = e[(e[:, 0] // cols) != (e[:, 1] // cols)]
    same = (v32[e[:, 0]] == v32[e[:, 1]]).sum(axis=1)
    return bool((same >= 2).any())


def lean_triangles(points: FloatArray) -> tuple[FloatArray, IntArray, list[int]]:
    """Hybrid tessellation of an R x C periodic grid (contract 02c); returns vertices, triangles, leaning strips.

    Every strip first gets the 02 quad split (max-min-angle diagonal). If any of its ring-to-ring edges is exactly
    parallel to a coordinate axis (two equal float32 coordinates), the whole strip is replaced by a leaning strip:
    triangles (b_j, t_{j+s}, t_{j+2s}) and (b_j, t_{j+2s}, b_{j+s}), s = +1 or -1 chosen for the larger minimum
    interior angle, oriented like the quad split. No ring-to-ring edge of a leaning strip repeats a column.
    """
    rows, cols, _ = points.shape
    v, quad = grid_triangles(points)
    v32 = v.astype(np.float32)
    vid = np.arange(rows * cols).reshape(rows, cols)
    j = np.arange(cols)
    out, leaning = quad.copy(), []
    for i in range(rows - 1):
        sl = slice(i * 2 * cols, (i + 1) * 2 * cols)
        if not _axis_parallel(v32, quad[sl], True, cols):
            continue
        b, t = vid[i], vid[i + 1]
        ref = np.cross(v[b[(j + 1) % cols]] - v[b], v[t] - v[b])
        best = None
        for s in (1, -1):
            first = np.stack([b, t[(j + s) % cols], t[(j + 2 * s) % cols]], 1)
            second = np.stack([b, t[(j + 2 * s) % cols], b[(j + s) % cols]], 1)
            strip = np.concatenate([first, second])
            n = np.cross(v[strip[:, 1]] - v[strip[:, 0]], v[strip[:, 2]] - v[strip[:, 0]])
            if (n * np.concatenate([ref, ref])).sum() < 0:
                strip = strip[:, ::-1]
            score = min_angle_deg(v[strip[:, 0]], v[strip[:, 1]], v[strip[:, 2]]).min()
            if best is None or score > best[0]:
                best = (score, strip)
        out[sl] = best[1]
        leaning.append(i)
    return v, out, leaning


def merge_chains(pos_a: FloatArray, pos_b: FloatArray, closed: bool) -> list[tuple[int, int, int]]:
    """Triangulate between two chains by advancing along whichever has the smaller next position.

    Returns triples (kind, i, j): kind 0 = triangle (A[i], A[i+1], B[j]); kind 1 = (A[i], B[j+1], B[j]).
    closed: both are loops with positions in [0,1) and wrap to 1.0; open: chains with positions in [0,1].
    """
    na, nb = len(pos_a), len(pos_b)
    i = j = 0
    out = []
    last_a, last_b = (na, nb) if closed else (na - 1, nb - 1)
    while i < last_a or j < last_b:
        next_a = (pos_a[i + 1] if i + 1 < na else 1.0) if i < last_a else np.inf
        next_b = (pos_b[j + 1] if j + 1 < nb else 1.0) if j < last_b else np.inf
        if next_a <= next_b:
            out.append((0, i, j))
            i += 1
        else:
            out.append((1, i, j))
            j += 1
    return out


def strip_faces(ids_a: IntArray, ids_b: IntArray, pos_a: FloatArray, pos_b: FloatArray, closed: bool) -> list[tuple[int, int, int]]:
    """Triangles between vertex id chains A and B (see merge_chains)."""
    na, nb = len(ids_a), len(ids_b)
    faces = []
    for kind, i, j in merge_chains(pos_a, pos_b, closed):
        ia1, jb1 = ids_a[(i + 1) % na], ids_b[(j + 1) % nb]
        faces.append((ids_a[i % na], ia1, ids_b[j % nb]) if kind == 0 else (ids_a[i % na], jb1, ids_b[j % nb]))
    return faces


def loop_fraction(points: FloatArray) -> FloatArray:
    """Normalised cumulative arc-length position in [0,1) of each vertex of a closed polygon."""
    seg = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    return cum[:-1] / cum[-1]


def round_cap(vertices: FloatArray, ring_ids: IntArray, final_max: int = 8, inner_radius: float = 0.3):
    """Concentric-ring cap closing a planar closed ring (no pole fan).

    Ring counts halve (ceil) until <= final_max; the last ring is closed by a centre vertex (valence <= final_max).
    Radii shrink about the ring centroid with widths proportional to the edge scale of each level.
    Returns (new_vertices (m,3), faces list of global ids, levels list of id arrays); new ids start at len(vertices).
    """
    ring = vertices[ring_ids]
    centre = ring.mean(axis=0)
    counts = [len(ring_ids)]
    while counts[-1] > final_max:
        counts.append(-(-counts[-1] // 2))
    levels = len(counts) - 1
    weights = 2.0 ** np.arange(levels)
    radii = np.concatenate([[1.0], 1.0 - (1.0 - inner_radius) * np.cumsum(weights) / weights.sum()])
    frac_outer = loop_fraction(ring)
    new_pts, faces = [], []
    prev_ids, prev_frac = ring_ids, frac_outer
    next_id = len(vertices)
    for k in range(1, levels + 1):
        idx = np.arange(counts[k]) * 2**k  # every 2^k-th boundary vertex: inner rings follow the outer vertex distribution
        pts = centre + radii[k] * (ring[idx] - centre)
        ids = np.arange(next_id, next_id + counts[k])
        next_id += counts[k]
        new_pts.append(pts)
        faces += strip_faces(prev_ids, ids, prev_frac, frac_outer[idx], closed=True)
        prev_ids, prev_frac = ids, frac_outer[idx]
    centre_id = next_id
    new_pts.append(centre[None, :])
    n = len(prev_ids)
    faces += [(prev_ids[i], prev_ids[(i + 1) % n], centre_id) for i in range(n)]
    return np.vstack(new_pts), faces


def airfoil_cap(vertices: FloatArray, ring_ids: IntArray, te_col: int, max_rows: int = 12, le_rows: int = 2, density: float = 1.0):
    """Planar cap of an airfoil-like ring (LE column 0, TE vertex at te_col, symmetric column pairing).

    Column u (1..te_col-1) joins upper vertex u with lower vertex n-u; interior points are equally spaced between
    them (count from thickness / local edge length, neighbouring columns differ by at most one, LE column <= le_rows).
    Returns (new_vertices (m,3), faces, ordered column id lists).
    """
    n = len(ring_ids)
    ring = vertices[ring_ids]
    edge = np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)
    cols = list(range(1, te_col))
    rows = []
    for u in cols:
        thick = np.linalg.norm(ring[u] - ring[n - u])
        local = 0.5 * (edge[u - 1] + edge[u])
        rows.append(int(np.clip(round(density * thick / max(local, 1e-12)), 1, max_rows)))
    rows = np.asarray(rows)
    rows[0] = min(rows[0], le_rows)
    for _ in range(len(rows)):
        rows[1:] = np.minimum(rows[1:], rows[:-1] + 1)
        rows[:-1] = np.minimum(rows[:-1], rows[1:] + 1)
    rows[-1] = min(rows[-1], 1 + 1)
    new_pts, next_id = [], len(vertices)
    columns = [[ring_ids[0]]]
    for u, m in zip(cols, rows, strict=True):
        ids = [ring_ids[n - u]]
        for k in range(1, m):
            ids.append(next_id)
            new_pts.append(ring[n - u] + (ring[u] - ring[n - u]) * k / m)
            next_id += 1
        ids.append(ring_ids[u])
        columns.append(ids)
    columns.append([ring_ids[te_col]])
    faces = []
    for ca, cb in zip(columns[:-1], columns[1:], strict=True):
        fa = np.linspace(0, 1, len(ca)) if len(ca) > 1 else np.zeros(1)
        fb = np.linspace(0, 1, len(cb)) if len(cb) > 1 else np.zeros(1)
        faces += strip_faces(np.asarray(ca), np.asarray(cb), fa, fb, closed=False)
    return (np.vstack(new_pts) if new_pts else np.zeros((0, 3))), faces, columns

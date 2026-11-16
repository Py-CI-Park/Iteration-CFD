# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pytest"]
# ///
"""Tests of the R6 generator building blocks (synthetic inputs only).

How to run: PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -v test_build_r6.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_r6
import r6_kinks
import r6_splines as sp
import r6_tess


def test_periodic_spline_reproduces_nodes_and_is_c2():
    rng = np.random.default_rng(3)
    n, period = 24, 9.0
    t = np.sort(rng.random(n)) * 8.9
    v = np.c_[np.cos(2 * np.pi * t / period), np.sin(2 * np.pi * t / period) * 1.5]
    curve = sp.periodic_spline(t, v, period)
    assert np.abs(sp.evaluate(curve, t) - v).max() < 1e-12
    eps = 1e-7
    for knots in (t, np.array([t[0] + period])):  # interior nodes and the wrap node
        for deriv in (1, 2):
            left = sp.evaluate(curve, knots - eps, deriv)
            right = sp.evaluate(curve, knots + eps, deriv)
            assert np.abs(left - right).max() < 1e-4, f"derivative {deriv} jumps at a node"
    assert np.abs(sp.evaluate(curve, t[:1] + period) - v[:1]).max() < 1e-12  # periodic


def test_open_spline_is_c2_and_exact_on_a_line():
    t = np.array([0.0, 0.3, 1.0, 1.4, 2.9, 3.0])
    line = 2.0 * t[:, None] + 1.0
    curve = sp.open_spline(t, line)
    q = np.linspace(0, 3, 50)
    assert np.abs(sp.evaluate(curve, q) - (2 * q[:, None] + 1)).max() < 1e-10
    wavy = sp.open_spline(t, np.sin(t)[:, None])
    inner = t[1:-1]
    assert np.abs(sp.evaluate(wavy, inner - 1e-7, 2) - sp.evaluate(wavy, inner + 1e-7, 2)).max() < 1e-4


def test_fritsch_carlson_has_no_overshoot_where_c2_does():
    t = np.arange(8.0)
    step = np.array([0, 0, 0, 1, 1, 1, 1, 1.0])[:, None]
    c2, fc = sp.open_spline(t, step), sp.fc_curve(t, step)
    q = np.linspace(0, 7, 701)
    assert sp.overshoots(c2, tol=1e-6)[0]
    y = sp.evaluate(fc, q)[:, 0]
    assert y.min() >= -1e-12 and y.max() <= 1 + 1e-12
    assert np.all(np.diff(y) >= -1e-12)  # monotone through the monotone data
    assert not sp.overshoots(fc, tol=1e-9)[0]
    assert np.abs(sp.evaluate(fc, t) - step).max() < 1e-12  # still interpolates every node


def test_fritsch_carlson_periodic_stays_inside_node_range():
    t = np.arange(12.0)
    v = np.array([0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0.0])[:, None]
    curve = sp.fc_periodic(t, v, 12.0)
    y = sp.evaluate(curve, np.linspace(0, 12, 481))[:, 0]
    assert y.min() >= -1e-12 and y.max() <= 1 + 1e-12


def test_diagonal_choice_maximises_minimum_angle():
    # a parallelogram whose short diagonal is a-c: splitting along b-d would create 2 needles
    pts = np.array([[[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], [[1.0, 1.0, 0.0], [11.0, 1.0, 0.0]]])
    # columns are periodic, so use a 2-column grid and inspect the first quad only
    v, tris = r6_tess.grid_triangles(pts)
    first = tris[:2]
    chosen = r6_tess.min_angle_deg(v[first[:, 0]], v[first[:, 1]], v[first[:, 2]]).min()
    a, b, c, d = 0, 1, 3, 2  # quad (r,c),(r,c+1),(r+1,c+1),(r+1,c)
    options = [[(a, b, c), (a, c, d)], [(a, b, d), (b, c, d)]]
    best = max(min(r6_tess.min_angle_deg(v[[t[0]]], v[[t[1]]], v[[t[2]]]).min() for t in opt) for opt in options)
    assert chosen >= best - 1e-9


def test_kink_detector_flags_five_degrees_and_ignores_one():
    span = np.linspace(0.0, 10.0, 11)
    base = np.tan(np.radians(25.0)) * span
    for jump, expect in ((5.0, True), (1.0, False)):
        x = base.copy()
        x[6:] += (np.tan(np.radians(25.0 + jump)) - np.tan(np.radians(25.0))) * (span[6:] - span[5])
        found = r6_kinks.detect_kinks(span, {"LE": x})
        assert bool(found) is expect
        if expect:
            assert [k["index"] for k in found] == [5]


def _ring(n: int = 200) -> np.ndarray:
    th = np.arange(n) * 2 * np.pi / n
    pts = np.zeros((n, 3))
    pts[:, 1], pts[:, 2] = 0.2 * np.cos(th) + 0.003 * np.cos(3 * th), 0.15 * np.sin(th)
    return pts


def _valence(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    return build_r6.valence(faces, len(vertices))


def test_round_cap_has_no_pole_fan_and_is_closed():
    ring = _ring()
    cap_vertices, cap = r6_tess.round_cap(ring, np.arange(len(ring)))
    vertices = np.vstack([ring, cap_vertices])
    faces = np.asarray(cap, dtype=np.int64)
    assert _valence(vertices, faces).max() <= 8
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.sum(counts == 1) == len(ring) and counts.max() <= 2  # only the boundary ring is open


def test_airfoil_cap_valence_and_boundary():
    n = 96
    s = np.linspace(0, np.pi, n // 2 + 1)
    x = (1 - np.cos(s)) / 2 * 1.5
    z = 0.06 * np.sin(s) * (1 - 0.4 * x / 1.5)
    ring = np.zeros((n, 3))
    ring[: n // 2 + 1, 0], ring[: n // 2 + 1, 2] = x, z
    ring[n // 2 + 1:, 0], ring[n // 2 + 1:, 2] = x[-2:0:-1], -z[-2:0:-1]
    new, faces, _ = r6_tess.airfoil_cap(ring, np.arange(n), te_col=n // 2)
    vertices = np.vstack([ring, new])
    f = np.asarray(faces, dtype=np.int64)
    assert _valence(vertices, f).max() <= 8
    edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    assert np.sum(counts == 1) == n and counts.max() <= 2


def test_lean_triangles_removes_exactly_axis_parallel_ring_edges():
    theta = np.arange(32) * 2 * np.pi / 32
    pts = np.stack([np.stack([np.full(32, x), 2 * np.cos(theta), 2 * np.sin(theta) + 4], axis=1) for x in np.linspace(0, 40, 50)])
    v, faces, leaning = r6_tess.lean_triangles(pts)
    assert len(leaning) > 0  # the plain tube has ring-to-ring edges parallel to x: those strips lean
    v32 = v.astype(np.float32)
    e = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    d = v32[e[:, 1]] - v32[e[:, 0]]
    ring_to_ring = np.abs(v32[e[:, 1], 0] - v32[e[:, 0], 0]) > 0
    assert not np.any(ring_to_ring & ((d[:, 1] == 0) & (d[:, 2] == 0)))  # no ring-to-ring edge exactly parallel to an axis remains on y/z


def test_cap_end_spacing_returns_one_height_per_boundary_edge():
    ring = np.array([[0, np.cos(a), np.sin(a)] for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)])
    faces = np.array([[0, k, k + 1] for k in range(1, 7)])  # a fan: valid enough to measure per-edge cap areas
    caps = [{"triangles": len(faces), "boundary_ids": list(range(8))}]
    # edge 7->0 and 0->1 belong to the fan; edges 1..6 belong to one fan triangle each; the fan closes edge (7,0) with face (0,6,7) absent
    faces = np.vstack([faces, [[0, 7, 1]]])[:, :]
    caps[0]["triangles"] = len(faces)
    h = build_r6.cap_end_spacing(ring, np.vstack([np.zeros((0, 3), dtype=int), faces]), caps, 0)
    assert len(h) == 1 and h[0].shape == (8,) and np.all(h[0] > 0)

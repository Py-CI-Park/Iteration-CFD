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
"""Structured vertex grid of one R6 component: columns, kink/closure segments, graded rows."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

import r6_kinks
import r6_ledger
import r6_lines
import r6_sections

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class GridParams:
    """Tunable generator parameters of one attempt (recorded in the receipt)."""

    turn_limit_deg: float = 10.0  # circumferential insertion target
    aspect_factor: float = 1.0  # multiplier on the balanced row spacing sqrt(P_p * P_(100-p)) of ring edge / grid-line speed
    ref_percentile: float = 5.0  # reference ring edge = this percentile of ring edge lengths
    hard_factor: float = 35.0  # row spacing never exceeds hard_factor * shortest ring edge (bounds the worst aspect)
    insertion_cap: int = 3
    h_max: float = 0.125
    grade: float = 1.25  # max growth of row spacing per unit arc (Lipschitz size field)
    samples_per_interval: int = 96
    closure_stations: int = 1  # fuselage: stations treated as closure band at each end
    cap_density: float = 1.0  # airfoil caps: interior rows per column = round(cap_density * thickness / local ring edge)
    long_turn_deg: float = 0.0  # max turning (deg) of any grid line between consecutive rows (0 = off): bounds the dihedral across ring edges
    end_bias: float = 1.0  # multiplier applied to the balanced end spacing after it is solved
    end_h: tuple = (0.0, 0.0)  # airfoil parts: grid-line spacing (m) imposed at the first/last capped end, then graded by `grade` (0 = off)


@dataclass
class Grid:
    """Rows x columns of in-plane coordinates for one part; axis coordinate per row."""

    part: r6_ledger.Part
    t_rows: FloatArray  # (n_rows,) axis coordinate of each row (mirrored span included)
    plane: FloatArray  # (n_rows, n_col, 2) in-plane coordinates
    taus: FloatArray
    station_rows: dict  # ledger station index (in t_full numbering) -> row index
    kinks: list = field(default_factory=list)
    closure_rows: list = field(default_factory=list)  # fuselage rows bounding the closure bands
    records: dict = field(default_factory=dict)  # method choices etc.

    @property
    def axes(self) -> tuple[int, int]:
        return r6_sections._plane_axes(self.part.axis)

    def points3d(self) -> FloatArray:
        """(n_rows, n_col, 3) absolute coordinates."""
        a, b = self.axes
        out = np.zeros(self.plane.shape[:2] + (3,))
        out[..., self.part.axis] = self.t_rows[:, None]
        out[..., a], out[..., b] = self.plane[..., 0], self.plane[..., 1]
        return out


def full_stations(part: r6_ledger.Part) -> tuple[FloatArray, FloatArray]:
    """Axis stations and ring points, mirrored through y = 0 for wing and horizontal (y = 0 station once)."""
    if not part.mirrored:
        return part.stations.copy(), part.points.copy()
    mirror = part.points[:0:-1].copy()
    mirror[..., 1] *= -1.0
    return np.concatenate([-part.stations[:0:-1], part.stations]), np.concatenate([mirror, part.points])


def part_kinks(part: r6_ledger.Part, t: FloatArray, rings: FloatArray) -> list[dict]:
    """Planform kinks (LE/TE x vs span slope change > 2 deg); the fuselage has none by the contract rule."""
    if part.name == "fuselage":
        return []
    x = rings[:, :, 0]
    return r6_kinks.detect_kinks(t, {"LE": x.min(axis=1), "TE": x.max(axis=1)})


def ring_columns(part: r6_ledger.Part, rings: FloatArray, params: GridParams):
    """Insert circumferential points and evaluate every station ring; returns (taus, plane (n_st, n_col, 2), kinds)."""
    corner = part.corners[0] if part.corners else None
    inserted = r6_sections.insertion_counts(rings, part.axis, corner, params.turn_limit_deg, cap=params.insertion_cap,
                                            symmetric=part.mirrored or part.root_cap)
    taus = r6_sections.tau_list(rings.shape[1], inserted)
    a, b = r6_sections._plane_axes(part.axis)
    plane, kinds = [], []
    for ring in rings:
        ev = r6_sections.ring_evaluator(ring, part.axis, corner)
        pts = ev(taus)
        plane.append(pts[:, [a, b]])
        kinds.append(ev.kind)
    return taus, np.stack(plane), kinds, inserted


def _sample_axis(t_nodes: FloatArray, count: int) -> FloatArray:
    """Dense samples in every ledger interval, clustered toward both interval ends (cosine)."""
    u = (1 - np.cos(np.pi * np.linspace(0, 1, count))) / 2
    pieces = [t0 + (t1 - t0) * u for t0, t1 in zip(t_nodes[:-1], t_nodes[1:], strict=True)]
    return np.concatenate(pieces)


def row_positions(part: r6_ledger.Part, t_nodes: FloatArray, segments, n_col: int, params: GridParams) -> FloatArray:
    """Row coordinates: every ledger station plus graded rows from a Lipschitz-limited size field.

    Per sample interval and column: edge = mean adjacent ring edge, speed = grid-line length per unit axis step.
    Row spacing h (axis units) = min( aspect_factor * sqrt(P_p * P_(100-p)) of edge / speed, hard_factor * min(edge / speed), h_max ),
    then capped by the host ledger interval and limited so h grows at most (grade - 1) per unit axis length.
    """
    m = params.samples_per_interval
    ts = _sample_axis(t_nodes, m)
    plane = r6_lines.evaluate_lines(segments, ts, n_col, 2)
    dt = np.diff(ts)
    ring_edge = np.linalg.norm(np.roll(plane, -1, axis=1) - plane, axis=2)
    edge = 0.5 * (ring_edge + np.roll(ring_edge, 1, axis=1))
    edge = 0.5 * (edge[1:] + edge[:-1])
    step = np.sqrt(np.linalg.norm(np.diff(plane, axis=0), axis=2) ** 2 + dt[:, None] ** 2)
    ratio = edge / np.maximum(step / np.maximum(dt[:, None], 1e-300), 1e-12)  # edge / speed
    lo = np.percentile(ratio, params.ref_percentile, axis=1)
    hi = np.percentile(ratio, 100.0 - params.ref_percentile, axis=1)
    balanced = params.aspect_factor * np.sqrt(lo * hi)  # equalises the aspect of the shortest and longest cells
    h_mid = np.maximum(np.minimum(balanced, params.hard_factor * ratio.min(axis=1)), 1e-9)
    h = np.concatenate([h_mid[:1], 0.5 * (h_mid[1:] + h_mid[:-1]), h_mid[-1:]])
    h = np.minimum(h, params.h_max)
    if params.long_turn_deg > 0:  # curvature criterion: turning of the grid line per row <= long_turn_deg for every column
        step3 = np.concatenate([np.broadcast_to(dt[:, None, None], (len(dt), plane.shape[1], 1)), np.diff(plane, axis=0)], axis=2)  # (S-1, ncol, 3) step vectors (axis, u, w)
        norm = np.linalg.norm(step3, axis=2)
        both = (norm[1:] > 0) & (norm[:-1] > 0)
        cosang = np.einsum("kjc,kjc->kj", step3[1:], step3[:-1]) / np.maximum(norm[1:] * norm[:-1], 1e-300)
        angle = np.where(both, np.arccos(np.clip(cosang, -1.0, 1.0)), 0.0)
        tau = angle / np.maximum(0.5 * (dt[1:] + dt[:-1]), 1e-300)[:, None]  # rad per axis unit at the sample between two steps
        tau = np.concatenate([tau[:1], tau, tau[-1:]], axis=0).max(axis=1)
        h = np.minimum(h, np.deg2rad(params.long_turn_deg) / np.maximum(tau, 1e-9))
    interval_of = np.repeat(np.arange(len(t_nodes) - 1), m)
    h = np.minimum(h, np.maximum(np.diff(t_nodes)[interval_of], 1e-12))
    # grading is limited in grid-line length s (median line speed), so steep bands do not squeeze the neighbouring body
    speed_mid = np.median(step / np.maximum(dt[:, None], 1e-300), axis=1)
    speed_mid = np.where(dt > 0, speed_mid, np.nan)
    speed_mid = np.where(np.isnan(speed_mid), np.nanmax(speed_mid), speed_mid)
    speed = np.concatenate([speed_mid[:1], 0.5 * (speed_mid[1:] + speed_mid[:-1]), speed_mid[-1:]])
    s = np.concatenate([[0.0], np.cumsum(dt * speed_mid)])
    hs = h * speed
    if part.name != "fuselage":  # capped airfoil ends: strip faces next to the cap match the cap triangles
        if params.end_h[0] > 0:
            hs[0] = min(hs[0], params.end_h[0])
        if params.end_h[1] > 0:
            hs[-1] = min(hs[-1], params.end_h[1])
    growth = params.grade - 1.0
    for k in range(1, len(hs)):
        hs[k] = min(hs[k], hs[k - 1] + growth * (s[k] - s[k - 1]))
    for k in range(len(hs) - 2, -1, -1):
        hs[k] = min(hs[k], hs[k + 1] + growth * (s[k + 1] - s[k]))
    g = np.concatenate([[0.0], np.cumsum(0.5 * (1 / hs[1:] + 1 / hs[:-1]) * np.diff(s))])
    rows = [t_nodes[0]]
    for i in range(len(t_nodes) - 1):
        lo, hi = i * m, (i + 1) * m - 1
        g0, g1 = g[lo], g[hi]
        count = max(1, int(np.ceil(g1 - g0 - 1e-9)))
        targets = g0 + (g1 - g0) * np.arange(1, count) / count
        inner = np.interp(targets, g[lo:hi + 1], ts[lo:hi + 1]) if count > 1 else np.array([])
        rows.extend(inner.tolist())
        rows.append(t_nodes[i + 1])
    return np.asarray(rows)


def build_grid(part: r6_ledger.Part, params: GridParams) -> Grid:
    """Full pipeline for one component's vertex grid."""
    t, rings = full_stations(part)
    kink_list = part_kinks(part, t, rings)
    taus, plane, ring_kinds, inserted = ring_columns(part, rings, params)
    kink_idx = [k["index"] for k in kink_list]
    closure: list[int] = []
    if part.name == "fuselage":
        c = params.closure_stations
        closure = [c, len(t) - 1 - c]
        kink_idx += closure
    segments = r6_lines.build_segments(t, plane, kink_idx)
    n_col = plane.shape[1]
    rows = row_positions(part, t, segments, n_col, params)
    values = r6_lines.evaluate_lines(segments, rows, n_col, 2)
    station_rows = {i: int(np.argmin(np.abs(rows - ti))) for i, ti in enumerate(t)}
    for i, ti in enumerate(t):  # station rows must hit the ledger exactly
        values[station_rows[i]] = plane[i]
        rows[station_rows[i]] = ti
    records = {
        "ring_curve_kinds": {k: int(sum(1 for x in ring_kinds if x == k)) for k in sorted(set(ring_kinds))},
        "inserted_per_segment": inserted.tolist(),
        "line_method": [{"stations": [int(sg.a), int(sg.b)], "fc_lines": int(sg.use_fc.sum()), "lines": int(len(sg.use_fc))}
                        for sg in segments],
        "kinks": kink_list,
        "closure_station_indices": closure,
    }
    return Grid(part, rows, values, taus, station_rows, kink_list, [station_rows[i] for i in closure], records)

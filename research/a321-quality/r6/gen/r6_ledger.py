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
"""Station ledger access for the R6 generator: station rings as 3-D points, per-part ring conventions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

REPO = Path(__file__).resolve().parents[4]
LEDGER = REPO / "research/a321-integration/evidence/reconstruction-r3.json"
R3_DIR = REPO / "research/a321-integration/artifacts/shell-r3"
LEDGER_SHA = "405aec921c5f492a6841c89102cb0215141a920906baed94298c5c2d3fef15cb"
OTHER_AXES = {0: (1, 2), 1: (0, 2), 2: (0, 1)}  # ring columns -> world axes for each station axis


@dataclass(frozen=True)
class Part:
    """One component: ring points P[n_station, n_ring, 3] (absolute xyz), station axis, corner ring indices."""

    name: str
    axis: int
    stations: FloatArray
    points: FloatArray
    corners: tuple[int, ...]  # ring indices with a declared sharp corner (trailing edge)
    mirrored: bool  # True: wing/horizontal, mirrored about y = 0 into one continuous grid
    root_cap: bool  # True: a planar cap is also needed at the first station (vertical root)


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def ring_points_3d(station: float, ring: FloatArray, axis: int) -> FloatArray:
    """(N, 3) absolute coordinates of one station ring."""
    out = np.zeros((len(ring), 3))
    a, b = OTHER_AXES[axis]
    out[:, axis] = station
    out[:, a], out[:, b] = ring[:, 0], ring[:, 1]
    return out


def load_parts(path: Path = LEDGER) -> dict[str, Part]:
    """All four parts from the ledger. Fuselage rings are rolled to start at the top centreline."""
    if sha256(path) != LEDGER_SHA:
        raise RuntimeError("LEDGER_SHA_CHANGED")
    record = json.loads(path.read_text(encoding="utf-8"))
    parts: dict[str, Part] = {}
    for item in record["parts"]:
        stations = np.asarray(item["stations_m"], dtype=np.float64)
        rings = np.asarray(item["rings_2d_m"], dtype=np.float64)
        points = np.stack([ring_points_3d(s, r, item["axis"]) for s, r in zip(stations, rings, strict=True)])
        name = item["name"]
        n_ring = points.shape[1]
        if name == "fuselage":
            top = int(np.argmax(points[len(stations) // 2, :, 2]))
            points = np.roll(points, -top, axis=1)
            corners: tuple[int, ...] = ()
        else:
            corners = (n_ring // 2,)  # chord_hull layout: LE index 0, trailing-edge vertex at N/2
        parts[name] = Part(name, item["axis"], stations, points, corners, name in ("wing", "horizontal"), name == "vertical")
    return parts


def ledger_bounds(parts: dict[str, Part]) -> dict[str, FloatArray]:
    """Min/max of the ledger points per part (mirrored span for wing and horizontal)."""
    out = {}
    for name, part in parts.items():
        pts = part.points.reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        if part.mirrored:
            lo = lo.copy()
            lo[1] = -hi[1]
        out[name] = np.vstack([lo, hi])
    return out

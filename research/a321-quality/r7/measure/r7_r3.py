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
"""Measurements on the R3 ledger fuselage: station profiles, constant section, rho (read-only)."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "research/a321-quality/r6/gen"))
import r6_ledger  # noqa: E402  (permissive repo module, read-only use)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class R3Profile:
    stations: FloatArray
    width: FloatArray  # full width (max y - min y) of the ring
    crown: FloatArray
    belly: FloatArray
    z_w: FloatArray  # z of the maximum width, quadratic fit near the side
    points: FloatArray  # ledger ring points (n_station, n_ring, 3)


def max_width_z(ring: FloatArray, band: float = 0.03) -> float:
    """z at which |y| is maximal: vertex of a parabola |y| = a + b (z-z0)^2 fitted to the side points within `band` of max."""
    ymax = np.abs(ring[:, 1]).max()
    sel = np.abs(ring[:, 1]) >= ymax - band
    z, y = ring[sel, 2], np.abs(ring[sel, 1])
    if len(z) < 5 or np.ptp(z) < 1e-6:
        return float(ring[np.argmax(np.abs(ring[:, 1])), 2])
    # separate the two sides so the fit uses y>0 and y<0 independently
    zs = []
    for sign in (1.0, -1.0):
        m = np.sign(ring[sel, 1]) == sign
        if m.sum() >= 4:
            c = np.polyfit(z[m], y[m], 2)
            if c[0] < 0:
                zs.append(-c[1] / (2 * c[0]))
    return float(np.mean(zs)) if zs else float(ring[np.argmax(np.abs(ring[:, 1])), 2])


def load_r3_profile() -> R3Profile:
    f = r6_ledger.load_parts()["fuselage"]
    p = f.points
    width = p[:, :, 1].max(1) - p[:, :, 1].min(1)
    crown, belly = p[:, :, 2].max(1), p[:, :, 2].min(1)
    zw = np.array([max_width_z(p[k]) for k in range(len(f.stations))])
    return R3Profile(np.asarray(f.stations), width, crown, belly, zw, p)


def constant_section(prof: R3Profile, tol: float = 1e-3) -> dict[str, float | int | list]:
    """Stations whose crown, belly and width equal their maxima/minima within `tol` (m)."""
    zc0, zb0, w0 = float(np.median(prof.crown[40:100])), float(np.median(prof.belly[40:100])), float(np.median(prof.width[40:100]))
    ok = (np.abs(prof.crown - zc0) < tol) & (np.abs(prof.belly - zb0) < tol) & (np.abs(prof.width - w0) < 2 * tol)
    idx = np.where(ok)[0]
    runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
    run = max(runs, key=len)
    zw_run = prof.z_w[run]
    rho = (zw_run - zb0) / (zc0 - zb0)
    return {
        "tol_m": tol, "crown_z": zc0, "belly_z": zb0, "width": w0, "height": zc0 - zb0,
        "station_index_range": [int(run.min()), int(run.max())], "n_stations": int(len(run)),
        "x_range_m": [float(prof.stations[run.min()]), float(prof.stations[run.max()])],
        "z_w_median": float(np.median(zw_run)), "z_w_min": float(zw_run.min()), "z_w_max": float(zw_run.max()),
        "rho_median": float(np.median(rho)), "rho_min": float(rho.min()), "rho_max": float(rho.max()),
        "rho_mean": float(rho.mean()), "rho_std": float(rho.std()),
        "crown_flat_clip_note": "R3 crown and belly rings are exactly flat clips (C15 records) at the constant z",
    }

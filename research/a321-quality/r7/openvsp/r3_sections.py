# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""R3 lifting-surface sections -> chord-frame data for OpenVSP file airfoils (numpy only).

Wing, horizontal and vertical rings come from the R3 ledger through the read-only r6_ledger.load_parts().
Per station: leading edge point, chord length, twist and a chord-frame airfoil (x', z' in chord lengths).
A greedy subset of stations is chosen so that linear interpolation of the chord-frame data between selected
stations reproduces every other station ring within a tolerance (millimetres)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "r6" / "gen"))
import r6_ledger  # noqa: E402  (read-only import; module is not modified)


def station_frame(ring_xz: np.ndarray, planar_axis_first: bool = True) -> dict:
    """Chord frame of one ring given as (N, 2) = (x, z). Index 0 is the leading edge, N/2 the trailing edge."""
    n = len(ring_xz)
    le, te = ring_xz[0], ring_xz[n // 2]
    chord_vec = te - le
    chord = float(np.hypot(*chord_vec))
    e1 = chord_vec / chord
    e2 = np.array([-e1[1], e1[0]])
    rel = ring_xz - le
    local = np.stack([rel @ e1, rel @ e2], axis=1) / chord
    twist_deg = float(np.degrees(np.arctan2(-chord_vec[1], chord_vec[0])))  # nose-up positive (TE lower than LE)
    return {"le": le, "te": te, "chord": chord, "twist_deg": twist_deg, "local": local}


def side_order(local: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (upper, lower) point arrays, each from LE to TE in chord lengths. Index 0 is LE, N/2 is TE."""
    n = len(local)
    first = local[: n // 2 + 1]            # LE ... TE through one side
    second = np.vstack([local[n // 2:], local[:1]])[::-1]  # LE ... TE through the other side
    if first[:, 1].mean() >= second[:, 1].mean():
        return first, second
    return second, first


def frames_for(part: r6_ledger.Part) -> list[dict]:
    """All station frames of a part; for the vertical fin the (x, y) ring is used (symmetric profile)."""
    frames = []
    for i, s in enumerate(part.stations):
        pts = part.points[i]
        a, b = r6_ledger.OTHER_AXES[part.axis]
        ring = np.stack([pts[:, a], pts[:, b]], axis=1)
        fr = station_frame(ring)
        fr["station"] = float(s)
        fr["ring"] = ring
        frames.append(fr)
    return frames


def reconstruct(frames: list[dict], picks: list[int], j: int) -> np.ndarray:
    """Ring of station j rebuilt by linear interpolation (in station coordinate) of the chord-frame data of the
    two selected neighbours. Returns (N, 2) absolute coordinates."""
    s = frames[j]["station"]
    ps = [frames[k]["station"] for k in picks]
    hi = int(np.searchsorted(ps, s))
    hi = min(max(hi, 1), len(picks) - 1)
    a, b = frames[picks[hi - 1]], frames[picks[hi]]
    t = (s - a["station"]) / (b["station"] - a["station"])
    lerp = lambda u, v: (1 - t) * u + t * v
    le, chord, tw, loc = lerp(a["le"], b["le"]), lerp(a["chord"], b["chord"]), lerp(a["twist_deg"], b["twist_deg"]), lerp(a["local"], b["local"])
    th = np.radians(tw)
    e1 = np.array([np.cos(th), -np.sin(th)])
    e2 = np.array([np.sin(th), np.cos(th)])
    return le + chord * (loc[:, :1] * e1 + loc[:, 1:2] * e2)


def max_error(frames: list[dict], picks: list[int]) -> tuple[float, int]:
    errs = []
    for j in range(len(frames)):
        errs.append(float(np.linalg.norm(reconstruct(frames, picks, j) - frames[j]["ring"], axis=1).max()))
    k = int(np.argmax(errs))
    return errs[k], k


def greedy_picks(frames: list[dict], tol_m: float, forced: tuple[int, ...] = ()) -> list[int]:
    picks = sorted({0, len(frames) - 1, *forced})
    while True:
        err, k = max_error(frames, picks)
        if err <= tol_m or len(picks) >= len(frames):
            return picks
        picks = sorted({*picks, k})

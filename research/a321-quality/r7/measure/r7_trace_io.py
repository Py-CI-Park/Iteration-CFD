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
"""Load the raw traced polylines (written by trace_drawing.py) and split them into the four fuselage outline
branches in PDF points: top-view upper and lower edge, side-view crown and belly. No PyMuPDF here."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
REPO = Path(__file__).resolve().parents[4]
RAW_TRACE = REPO / ".worktmp/r7-trace/raw-trace.json"


@dataclass(frozen=True)
class RawBranches:
    """Outline branches in PDF points (x to the right, y DOWN), each sorted by increasing x."""

    top_upper: FloatArray  # top view, edge above the centre line (page y smaller)
    top_lower: FloatArray
    side_crown: FloatArray  # side view, upper line; the crown gap (arrow white halo) is left open
    side_belly: FloatArray  # side view, lower line; the engine/wing gap is left open
    centreline_y_pt: float
    ground_y_pt: float
    tips74: list
    tips73: list
    sha256: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_loop(loop: FloatArray, centreline_y: float) -> tuple[FloatArray, FloatArray]:
    """Closed outline -> (upper, lower) edge, both from the nose tip to the tail cap corner, increasing x."""
    pts = loop[:-1] if np.hypot(*(loop[0] - loop[-1])) < 1e-6 else loop
    n = len(pts)
    i_nose = int(np.argmin(pts[:, 0]))
    pts = np.roll(pts, -i_nose, axis=0)  # starts at the nose tip
    x_tail = pts[:, 0].max()
    tail_idx = np.where(pts[:, 0] > x_tail - 0.01)[0]
    a, b = int(tail_idx.min()), int(tail_idx.max())
    first = pts[: a + 1]  # nose -> first tail-cap corner
    second = np.vstack([pts[0:1], pts[b:][::-1]])  # nose -> other corner, reversed direction
    upper, lower = (first, second) if first[len(first) // 2, 1] < centreline_y else (second, first)
    return upper, lower


def _monotone(branch: FloatArray, tol_pt: float = 0.02) -> FloatArray:
    """Require a single-valued branch; flat polyline rounding at Bezier joints (< tol_pt) is flattened."""
    drop = -np.diff(branch[:, 0])
    if np.any(drop > tol_pt):
        raise ValueError("branch not single valued in x")
    out = branch.copy()
    out[:, 0] = np.maximum.accumulate(out[:, 0])
    return out


def load_raw(path: Path = RAW_TRACE) -> RawBranches:
    raw = json.loads(path.read_text(encoding="utf-8"))
    top = raw["top_view_page74"]
    cl = float(top["centreline_y_pt"])
    loop = np.asarray(top["runs"][0]["points_pt"], dtype=np.float64)
    upper, lower = _split_loop(loop, cl)
    runs = [np.asarray(r["points_pt"], dtype=np.float64) for r in raw["side_view_page73"]["runs"]]
    run_nose = next(r for r in runs if r[:, 0].min() < 130.0)  # the run holding the nose
    run_tail = next(r for r in runs if r[:, 0].max() > 470.0)  # the run holding the tail cap
    i_nose = int(np.argmin(run_nose[:, 0]))
    crown_front = run_nose[: i_nose + 1][::-1]  # nose tip -> crown gap
    belly_front = run_nose[i_nose:]  # nose tip -> belly gap
    x_tail = run_tail[:, 0].max()
    tail_idx = np.where(run_tail[:, 0] > x_tail - 0.01)[0]
    a, b = int(tail_idx.min()), int(tail_idx.max())
    # run_tail starts at the crown gap end (x=340), goes to the tail cap, comes back along the belly to x=321
    crown_back = run_tail[: a + 1]
    belly_back = run_tail[b:][::-1]
    crown = np.vstack([crown_front, crown_back])
    belly = np.vstack([belly_front, belly_back])
    return RawBranches(
        top_upper=_monotone(upper), top_lower=_monotone(lower),
        side_crown=_monotone(crown), side_belly=_monotone(belly),
        centreline_y_pt=cl, ground_y_pt=float(raw["side_view_page73"]["ground_y_pt"]),
        tips74=raw["dimension_tips_page74"], tips73=raw["dimension_tips_page73"], sha256=sha256_file(path),
    )


def interp_branch(branch: FloatArray, x: FloatArray) -> FloatArray:
    """Linear interpolation of a single-valued branch (flat polyline sampling is already 64 steps per Bezier)."""
    return np.interp(x, branch[:, 0], branch[:, 1])

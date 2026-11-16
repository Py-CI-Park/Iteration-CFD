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
"""Normalise the traced fuselage outlines per contract 03 M2 and describe them as functions of x (metres).

Top view -> full width W(x) (centre-line independent) and centre offset c(x). Side view -> crown z_c(x) and belly
z_b(x) in the R3 frame. Every function is a linear interpolation of the traced polyline (64 steps per Bezier)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from r7_trace_io import RawBranches, interp_branch

FloatArray = NDArray[np.float64]
LENGTH_M, WIDTH_M, HEIGHT_M = 44.51, 3.95, 4.14
# Hidden-line gaps in the side view (PDF points): the crown under the 4.14 m arrow halo and the belly under the
# wing/engine. The traced outline is bridged straight there (both ends lie on the same constant line).
CROWN_GAP_PT = (335.19, 339.95)
BELLY_GAP_PT = (248.90, 321.04)


@dataclass(frozen=True)
class Normalised:
    """Scale factors (pt per m) and reference values of the normalisation, plus accessors in metres."""

    raw: RawBranches
    x0_top_pt: float
    sx_top: float
    sy_top: float  # width scale
    x0_side_pt: float
    sx_side: float
    sz_side: float  # height scale
    z_offset: float  # added to (y_ref - y_pt)/sz_side to land in the R3 frame
    y_ref_pt: float
    crown_const_pt: float
    belly_const_pt: float
    r3_crown_z: float
    r3_belly_z: float

    # ---- top view -------------------------------------------------------------------------------------------
    def top_edges_pt(self, x: FloatArray) -> tuple[FloatArray, FloatArray]:
        xp = self.x0_top_pt + np.asarray(x) * self.sx_top
        return interp_branch(self.raw.top_upper, xp), interp_branch(self.raw.top_lower, xp)

    def width(self, x: FloatArray) -> FloatArray:
        up, lo = self.top_edges_pt(x)
        return (lo - up) / self.sy_top

    def half_widths_from_drawn_centreline(self, x: FloatArray) -> tuple[FloatArray, FloatArray]:
        up, lo = self.top_edges_pt(x)
        cl = self.raw.centreline_y_pt
        return (cl - up) / self.sy_top, (lo - cl) / self.sy_top

    def centre_offset(self, x: FloatArray) -> FloatArray:
        up, lo = self.top_edges_pt(x)
        return ((up + lo) / 2 - self.raw.centreline_y_pt) / self.sy_top

    # ---- side view ------------------------------------------------------------------------------------------
    def side_pt(self, x: FloatArray) -> tuple[FloatArray, FloatArray]:
        xp = self.x0_side_pt + np.asarray(x) * self.sx_side
        return interp_branch(self.raw.side_crown, xp), interp_branch(self.raw.side_belly, xp)

    def z_of_pt(self, y_pt: FloatArray) -> FloatArray:
        return (self.y_ref_pt - np.asarray(y_pt)) / self.sz_side + self.z_offset

    def crown(self, x: FloatArray) -> FloatArray:
        return self.z_of_pt(self.side_pt(x)[0])

    def belly(self, x: FloatArray) -> FloatArray:
        return self.z_of_pt(self.side_pt(x)[1])

    def in_gap(self, x: FloatArray, which: str) -> NDArray[np.bool_]:
        lo, hi = CROWN_GAP_PT if which == "crown" else BELLY_GAP_PT
        xp = self.x0_side_pt + np.asarray(x) * self.sx_side
        return (xp > lo) & (xp < hi)


def build_normalisation(raw: RawBranches, r3_crown_z: float, r3_belly_z: float, r3_mid_z: float | None = None) -> Normalised:
    x0t = float(raw.top_upper[0, 0])
    x_tail_t = float(max(raw.top_upper[:, 0].max(), raw.top_lower[:, 0].max()))
    sx_top = (x_tail_t - x0t) / LENGTH_M
    xx = np.linspace(x0t, x_tail_t, 40001)
    wmax_pt = float((interp_branch(raw.top_lower, xx) - interp_branch(raw.top_upper, xx)).max())
    sy_top = wmax_pt / WIDTH_M

    x0s = float(raw.side_crown[0, 0])
    x_tail_s = float(max(raw.side_crown[:, 0].max(), raw.side_belly[:, 0].max()))
    sx_side = (x_tail_s - x0s) / LENGTH_M
    xs = np.linspace(x0s, x_tail_s, 40001)
    crown_y, belly_y = interp_branch(raw.side_crown, xs), interp_branch(raw.side_belly, xs)
    hmax_pt = float((belly_y - crown_y).max())
    sz_side = hmax_pt / HEIGHT_M
    # constant section lines: crown y at the long straight run, belly y likewise (median over the constant stretch)
    straight = (xs > 200.0) & (xs < 330.0)
    crown_const = float(np.median(crown_y[straight]))
    belly_const = float(np.median(belly_y[(xs > 170.0) & (xs < 245.0)]))
    mid_target = 0.5 * (r3_crown_z + r3_belly_z) if r3_mid_z is None else r3_mid_z
    y_ref = 0.5 * (crown_const + belly_const)
    # z = (y_ref - y)/sz + offset ; offset puts the mid-height of the constant section at the R3 mid-height
    return Normalised(raw, x0t, sx_top, sy_top, x0s, sx_side, sz_side, mid_target, y_ref, crown_const, belly_const, r3_crown_z, r3_belly_z)

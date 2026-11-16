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
"""Analytic R7 fuselage model for the PRE-surface measurements: width/crown/belly curves plus the contract M4
two-half-ellipse section. Nothing here writes a mesh; it is used for implicit tests, ring estimates and distances."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
X_LO, X_HI = 0.001, 44.509


@dataclass(frozen=True)
class FuselageModel:
    width: Callable[[FloatArray], FloatArray]
    crown: Callable[[FloatArray], FloatArray]
    belly: Callable[[FloatArray], FloatArray]
    rho: float

    def section(self, x: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Half-width a, mid-line z_w, upper semi-axis b_u, lower semi-axis b_l at stations x."""
        xc = np.clip(np.asarray(x, dtype=np.float64), X_LO, X_HI)
        a = np.maximum(self.width(xc), 1e-9) / 2.0
        zc, zb = self.crown(xc), self.belly(xc)
        h = np.maximum(zc - zb, 1e-9)
        zw = zb + self.rho * h
        return a, zw, zc - zw, zw - zb

    def implicit(self, p: FloatArray) -> FloatArray:
        """F(x,y,z) = sqrt((y/a)^2 + ((z-z_w)/b)^2) - 1: < 0 inside, > 0 outside (dimensionless)."""
        a, zw, bu, bl = self.section(p[:, 0])
        b = np.where(p[:, 2] >= zw, bu, bl)
        return np.sqrt((p[:, 1] / a) ** 2 + ((p[:, 2] - zw) / b) ** 2) - 1.0

    def gradient(self, p: FloatArray, h: float = 1e-5) -> FloatArray:
        g = np.zeros_like(p)
        for k in range(3):
            d = np.zeros(3)
            d[k] = h
            g[:, k] = (self.implicit(p + d) - self.implicit(p - d)) / (2 * h)
        return g

    def signed_distance_estimate(self, p: FloatArray) -> FloatArray:
        """First-order distance to the surface, positive INSIDE: -F/|grad F| (exact to O(F^2); includes the x-dependence)."""
        f = self.implicit(p)
        g = np.linalg.norm(self.gradient(p), axis=1)
        return -f / np.maximum(g, 1e-12)

    def normal(self, p: FloatArray) -> FloatArray:
        g = self.gradient(p)
        return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)

    # ---- ring points ----------------------------------------------------------------------------------------
    def ring(self, x: float, n_points: int, fine: int = 2000) -> FloatArray:
        """N ring points: vertices at crown (y=0), both max-width points and belly, equal arc length per quadrant."""
        if n_points % 4:
            raise ValueError("n_points must be a multiple of 4")
        a, zw, bu, bl = (float(v[0]) for v in self.section(np.array([x])))
        pts = self._ring_explicit(a, zw, bu, bl, n_points // 4, fine)
        return np.column_stack([np.full(n_points, x), pts])

    @staticmethod
    def _ring_explicit(a: float, zw: float, bu: float, bl: float, m: int, fine: int) -> FloatArray:
        def quadrant(b: float) -> tuple[FloatArray, FloatArray]:
            """Points from the crown/belly (phi=0) to the side (phi=pi/2), equal arc length, m intervals (side excluded)."""
            phi = np.linspace(0.0, np.pi / 2, fine + 1)
            y, z = a * np.sin(phi), b * np.cos(phi)
            arc = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(y), np.diff(z)))])
            ph = np.interp(np.linspace(0.0, arc[-1], m + 1)[:-1], arc, phi)
            return a * np.sin(ph), b * np.cos(ph)

        yu, zu = quadrant(bu)  # crown -> +y side (side point itself excluded)
        yl, zl = quadrant(bl)  # belly -> side, reversed below
        pts = []
        pts += [(yu[k], zw + zu[k]) for k in range(m)]  # crown ... just before +y side
        pts += [(a, zw)]  # +y max-width point
        pts += [(yl[k], zw - zl[k]) for k in range(m - 1, 0, -1)]  # towards belly (belly point excluded here)
        pts += [(0.0, zw - bl)]  # belly
        pts += [(-yl[k], zw - zl[k]) for k in range(1, m)]  # belly -> -y side (side excluded)
        pts += [(-a, zw)]  # -y max-width point
        pts += [(-yu[k], zw + zu[k]) for k in range(m - 1, 0, -1)]  # towards the crown
        return np.array(pts)

    def perimeter(self, x: FloatArray) -> FloatArray:
        a, _, bu, bl = self.section(x)

        def half(b: FloatArray) -> FloatArray:  # half of an ellipse perimeter (Ramanujan)
            h = ((a - b) / (a + b)) ** 2
            return np.pi * (a + b) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h))) / 2

        return half(bu) + half(bl)

# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Parameters of the independent OpenVSP A321 model. Every number has a tag naming its source.

Tags: PRINTED = printed on the Airbus drawing (reference-dimensions.json); R3_STATION_EXTENT = nose/tail tip
height or barrel start/end read from the R3 ledger fuselage stations; R3_SECTIONS = lifting-surface sections of
the R3 ledger; CHOICE = modelling choice made here, not drawing data; OPENVSP = OpenVSP setting."""
from __future__ import annotations

import math

import numpy as np

LENGTH = (44.51, "PRINTED overall length, nose to tail-cone tip (drawing page 74)")
WIDTH = (3.95, "PRINTED maximum fuselage width (drawing page 74)")
HEIGHT = (4.14, "PRINTED maximum fuselage height (drawing page 73)")
HALF_SPAN_WING = (16.29, "PRINTED half-span to the sharklet break (sharklet itself omitted)")
HALF_SPAN_HT = (6.225, "PRINTED horizontal-tail half-span")

# Fuselage stations that the brief allows to be read from R3 (extents only).
BARREL_X0 = (7.2, "R3_STATION_EXTENT: full-height section reached at x = 7.2 m in the R3 ledger fuselage")
BARREL_X1 = (29.8, "R3_STATION_EXTENT: belly starts to rise after x = 29.8 m in the R3 ledger fuselage")
BARREL_ZC = (4.02, "R3_STATION_EXTENT: barrel centre height = (crown 6.09 + belly 1.95) / 2 in the R3 frame")
NOSE_TIP_Z = (3.458, "R3_STATION_EXTENT: z of the nose tip point in the R3 frame")
TAIL_TIP_Z = (5.112, "R3_STATION_EXTENT: z of the tail-cone tip point in the R3 frame")

NOSE_EXP = (2.0, "CHOICE: nose half-width and half-height scale (1-(1-xi)^p)^(1/p), p = 2 is an ellipsoid")
TAIL_EXP = (2.0, "CHOICE: tail-cone scale (1-eta^q)^(1/q), q = 2 is an ellipsoid")
NOSE_ZC_EXP = (2.0, "CHOICE: nose centre line z = tip + (barrel - tip) * (1-(1-xi)^2)")
TAIL_ZC_EXP = (2.0, "CHOICE: tail centre line z = barrel + (tip - barrel) * eta^2")
NOSE_INTERVALS = (10, "CHOICE: cosine clustered stations between nose tip and barrel start")
TAIL_INTERVALS = (10, "CHOICE: cosine clustered stations between barrel end and tail tip")

SECTION_TOL_M = (0.0005, "CHOICE: R3 lifting-surface sections kept so that linear loft reproduces every R3 station within 0.5 mm")

TESS = {
    "fuselage": {"U": 120, "W": 64},
    "wing": {"U": 60, "W": 100},
    "horizontal": {"U": 40, "W": 80},
    "vertical": {"U": 40, "W": 80},
}


GRADE_EXP = (1.6, "CHOICE: station grading x = L*(i/N)^1.6 (nose) and its mirror (tail) so neighbouring station gaps stay within a factor 3 (C2 skinning oscillates on very uneven gaps)")
BARREL_GAP_M = (2.8, "CHOICE: barrel station gap, 8 equal intervals between the barrel start and end")
SECT_TESS_TARGET_M = (0.25, "CHOICE: target axial spacing of tessellation rings, SectTess_U per fuselage section = clip(round(gap / 0.25 m), 2, 16)")


CORRECT_THICKNESS = [0]  # OpenVSP WingGeom CorrectAirfoilthicknessFlag: default 1 makes root sections 1/cos(dihedral) too thick (measured +2.7 mm wing, +5.6 mm horizontal); 0 reproduces the R3 rings (CLI --correct-thickness)
TESS_SCALE = [1.0]  # CLI override (build_a321_vsp.py --tess-scale); a one-element list so that importers see the change


def scaled(n: float, lo: int = 2) -> int:
    return int(max(lo, round(n * TESS_SCALE[0])))


def nose_stations() -> list[tuple[float, float, float]]:
    """(x, scale, zc) for the nose from the first station after the tip to the barrel start (inclusive)."""
    n, p, zt = NOSE_INTERVALS[0], NOSE_EXP[0], NOSE_TIP_Z[0]
    out = []
    for i in range(1, n + 1):
        xi = (i / n) ** GRADE_EXP[0]
        x = BARREL_X0[0] * xi
        s = (1.0 - (1.0 - xi) ** p) ** (1.0 / p)
        zc = zt + (BARREL_ZC[0] - zt) * (1.0 - (1.0 - xi) ** NOSE_ZC_EXP[0])
        out.append((x, s, zc))
    return out


def tail_stations() -> list[tuple[float, float, float]]:
    """(x, scale, zc) from the first station after the barrel end up to (not including) the tail tip."""
    n, q = TAIL_INTERVALS[0], TAIL_EXP[0]
    out = []
    for i in range(1, n):
        eta = 1.0 - (1.0 - i / n) ** GRADE_EXP[0]
        x = BARREL_X1[0] + (LENGTH[0] - BARREL_X1[0]) * eta
        s = (1.0 - eta**q) ** (1.0 / q)
        zc = BARREL_ZC[0] + (TAIL_TIP_Z[0] - BARREL_ZC[0]) * eta**TAIL_ZC_EXP[0]
        out.append((x, s, zc))
    return out



def fuselage_stations() -> list[dict]:
    """All fuselage XSec records, nose tip to tail tip. kind 'point' or 'ellipse'; width/height in metres."""
    st = [{"x": 0.0, "kind": "point", "scale": 0.0, "zc": NOSE_TIP_Z[0]}]
    for x, s, zc in nose_stations():
        st.append({"x": x, "kind": "ellipse", "scale": s, "zc": zc})
    for j in range(1, 8):
        st.append({"x": BARREL_X0[0] + j * (BARREL_X1[0] - BARREL_X0[0]) / 8, "kind": "ellipse", "scale": 1.0, "zc": BARREL_ZC[0]})
    st.append({"x": BARREL_X1[0], "kind": "ellipse", "scale": 1.0, "zc": BARREL_ZC[0]})
    for x, s, zc in tail_stations():
        st.append({"x": x, "kind": "ellipse", "scale": s, "zc": zc})
    st.append({"x": LENGTH[0], "kind": "point", "scale": 0.0, "zc": TAIL_TIP_Z[0]})
    for k, rec in enumerate(st):
        rec["width"] = WIDTH[0] * rec["scale"]
        rec["height"] = HEIGHT[0] * rec["scale"]
        gap = rec["x"] - st[k - 1]["x"] if k else 0.0
        rec["sect_tess_u"] = scaled(min(16, max(2, round(gap / SECT_TESS_TARGET_M[0])))) if k else 2
    return st


def fuselage_target_half_width(x: np.ndarray) -> np.ndarray:
    """Analytic design half-width w(x)/2 used to check what OpenVSP actually built."""
    x = np.asarray(x, dtype=float)
    w = np.full_like(x, WIDTH[0] / 2)
    xi = np.clip(x / BARREL_X0[0], 0, 1)
    nose = (1 - (1 - xi) ** NOSE_EXP[0]) ** (1 / NOSE_EXP[0])
    eta = np.clip((x - BARREL_X1[0]) / (LENGTH[0] - BARREL_X1[0]), 0, 1)
    tail = (1 - eta ** TAIL_EXP[0]) ** (1 / TAIL_EXP[0])
    return w * np.where(x < BARREL_X0[0], nose, np.where(x > BARREL_X1[0], tail, 1.0))

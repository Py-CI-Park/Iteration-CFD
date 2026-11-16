# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Why the fuselage XSec continuity is C1: builds the fuselage with continuity 0, 1 and 2 and samples the surface.

The barrel (x 8 - 29 m) must have a constant half-width of 1.975 m. OpenVSP C2 skinning oscillates on the very uneven
station gaps of the nose and tail; C0 and C1 do not. Run (venv interpreter, isolated):
  .worktmp/venvs/openvsp313/Scripts/python.exe -I research/a321-quality/r7/openvsp/check_fuselage_continuity.py --out X.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a321_params as P  # noqa: E402
import openvsp as vsp  # noqa: E402


def build(continuity: int) -> str:
    vsp.VSPRenew()
    st = P.fuselage_stations()
    geom = vsp.AddGeom("FUSELAGE")
    vsp.SetParmVal(geom, "Length", "Design", P.LENGTH[0])
    xs = vsp.GetXSecSurf(geom, 0)
    while vsp.GetNumXSec(xs) < len(st):
        vsp.InsertXSec(geom, vsp.GetNumXSec(xs) - 2, vsp.XS_ELLIPSE)
    for k, s in enumerate(st):
        vsp.ChangeXSecShape(xs, k, vsp.XS_POINT if s["kind"] == "point" else vsp.XS_ELLIPSE)
    for k in range(len(st) - 1, -1, -1):
        s, x = st[k], vsp.GetXSec(xs, k)
        vsp.SetParmVal(vsp.GetXSecParm(x, "XLocPercent"), s["x"] / P.LENGTH[0])
        vsp.SetParmVal(vsp.GetXSecParm(x, "ZLocPercent"), s["zc"] / P.LENGTH[0])
        if s["kind"] == "ellipse":
            vsp.SetParmVal(vsp.GetXSecParm(x, "Ellipse_Width"), s["width"])
            vsp.SetParmVal(vsp.GetXSecParm(x, "Ellipse_Height"), s["height"])
    vsp.Update()
    for k in range(1, len(st) - 1):
        vsp.SetXSecContinuity(vsp.GetXSec(xs, k), continuity)
    vsp.Update()
    return geom


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = {}
    for c in (0, 1, 2):
        g = build(c)
        rows = []
        for u in np.linspace(0.30, 0.80, 101):
            pts = np.array([[q.x(), q.y()] for q in (vsp.CompPnt01(g, 0, float(u), float(w)) for w in np.linspace(0, 1, 33))])
            rows.append((pts[:, 0].mean(), np.abs(pts[:, 1]).max()))
        r = np.array(rows)
        m = (r[:, 0] > 8) & (r[:, 0] < 29)
        out[f"C{c}"] = {"barrel_half_width_min_m": float(r[m, 1].min()), "barrel_half_width_max_m": float(r[m, 1].max()), "x_monotone_along_u": bool((np.diff(r[:, 0]) >= 0).all())}
        print(f"C{c}", out[f"C{c}"])
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

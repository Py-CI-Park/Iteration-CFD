# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Section-thickness check of the OpenVSP component STL against the R3 rings at R3 stations (numpy only).

Compares, for the stations listed below, the thickness (extent of the slice in the thickness direction) and the
chord extent of the OpenVSP slice with the R3 ring of the same station. Used to show the effect of OpenVSP's
`CorrectAirfoilthicknessFlag` (tag "" = production flag 0, tag "_ct1" = OpenVSP default 1).
Run (venv interpreter): .worktmp/venvs/openvsp313/Scripts/python.exe -I research/a321-quality/r7/openvsp/check_root_thickness.py --out X.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_sections as r3  # noqa: E402

WORKTMP = HERE.parents[3] / ".worktmp" / "r7-openvsp"
STATIONS = {"wing": (1, [0.0, 4.4588, 10.8025]), "horizontal": (1, [0.0, 1.285, 3.162]), "vertical": (2, [5.5, 6.502, 9.139])}


def read_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    n = int.from_bytes(raw[80:84], "little")
    dt = np.dtype([("n", "<f4", (3,)), ("t", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(raw, dtype=dt, count=n, offset=84)["t"].astype(np.float64)


def slice_axis(tri: np.ndarray, axis: int, c: float) -> np.ndarray:
    out = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        pa, pb = tri[:, a], tri[:, b]
        da, db = pa[:, axis] - c, pb[:, axis] - c
        m = da * db < 0
        t = da[m] / (da[m] - db[m])
        out.append(pa[m] + t[:, None] * (pb[m] - pa[m]))
    return np.vstack(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    parts = r3.r6_ledger.load_parts()
    result: dict = {}
    for tag in ("", "_ct1"):
        rows = []
        for name, (axis, stns) in STATIONS.items():
            tri = read_stl(WORKTMP / f"openvsp_{name}{tag}.stl")
            a, b = r3.r6_ledger.OTHER_AXES[axis]
            for s in stns:
                # slice a hair inside the root cap plane / station so the slice is not on the cap
                c = s + (5e-4 if s in (0.0, 5.5) else 0.0)
                p = slice_axis(tri, axis, c)
                i = int(np.argmin(np.abs(parts[name].stations - s)))
                ring = parts[name].points[i]
                thick = (p[:, b].max() - p[:, b].min()) - (ring[:, b].max() - ring[:, b].min())
                chord = (p[:, a].max() - p[:, a].min()) - (ring[:, a].max() - ring[:, a].min())
                rows.append({"component": name, "station_m": s, "thickness_diff_mm": float(thick * 1000), "chord_extent_diff_mm": float(chord * 1000)})
        result["production_flag0" if tag == "" else "openvsp_default_flag1"] = rows
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    for k, rows in result.items():
        print(k)
        for r in rows:
            print("  ", r["component"], r["station_m"], round(r["thickness_diff_mm"], 3), round(r["chord_extent_diff_mm"], 3))


if __name__ == "__main__":
    main()

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
"""A3 reference band: R6 candidate STL extents against reference-dimensions.json printed values (band +-0.1 m).

How to run: python a3_reference.py --attempt <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r6_io

BAND = 0.1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    ref = {d["label_m"]: d for d in json.loads((HERE.parent / "reference/reference-dimensions.json").read_text())["dimensions"]}
    tri = {n: r6_io.read_stl(args.attempt / f"{n}.stl").reshape(-1, 3).astype(np.float64) for n in ("fuselage", "wing", "horizontal", "vertical")}
    fus = tri["fuselage"]
    top30 = fus[np.abs(fus[:, 0] - 30.0) < 0.2][:, 2].max()
    rows = [
        ("overall length (m)", "44.51", tri["fuselage"][:, 0].max() - tri["fuselage"][:, 0].min()),
        ("wing half-span to tip, no sharklet (m)", "16.29", tri["wing"][:, 1].max()),
        ("wing span tip to tip without sharklets (m)", None, tri["wing"][:, 1].max() - tri["wing"][:, 1].min()),
        ("horizontal tail span tip to tip (m)", "12.45", tri["horizontal"][:, 1].max() - tri["horizontal"][:, 1].min()),
        ("vertical tail tip above fuselage crown line at x=30 (m)", "5.87", tri["vertical"][:, 2].max() - top30),
        ("fuselage max width (m)", "3.95", fus[:, 1].max() - fus[:, 1].min()),
        ("fuselage max height (m)", "4.14", fus[:, 2].max() - fus[:, 2].min()),
    ]
    out = []
    for label, key, value in rows:
        printed = ref[key]["value_m"] if key else None
        delta = None if printed is None else float(value - printed)
        out.append({"item": label, "r6_m": float(value), "reference_printed_m": printed, "delta_m": delta, "within_band_0.1": None if delta is None else abs(delta) <= BAND})
    note = ("wing span including sharklets 35.80 m (half 17.90 m) is not modelled: sharklet excluded by contract 02 scope; "
            "its delta -1.61 m per side is the signed finding of reference/REFERENCE_KO.md")
    args.out.write_text(json.dumps({"band_m": BAND, "rows": out, "note": note}, indent=1), encoding="utf-8")
    for r in out:
        print(r)


if __name__ == "__main__":
    main()

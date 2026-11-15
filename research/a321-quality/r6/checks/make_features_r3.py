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
"""Ring-derived LE/TE polylines of the R3 wing, horizontal and vertical tail (demonstration input).

For every saved R3 section ring (reconstruction-r3.json, absolute coordinates in the two axes
perpendicular to the part axis) the extreme point along x is taken as leading edge (min x) and
trailing edge (max x). The mirrored port side is added for wing and horizontal tail. This is a
measured-data demonstration of the feature-exclusion input of r6_gate.py, not an R6 feature contract.

How to run: uv run --no-project make_features_r3.py <reconstruction-r3.json> <features.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# remaining axes of each part, in ring column order: axis 0 -> (y,z); axis 1 -> (x,z); axis 2 -> (x,y)
RING_AXES = {0: (1, 2), 1: (0, 2), 2: (0, 1)}


def extreme_points(part: dict) -> dict[str, np.ndarray]:
    """Leading/trailing-edge points per station (3D)."""
    axis = int(part["axis"])
    rings = np.asarray(part["rings_2d_m"], dtype=np.float64)
    stations = np.asarray(part["stations_m"], dtype=np.float64)
    cols = RING_AXES[axis]
    x_col = cols.index(0)
    out = {}
    for label, pick in (("LE", np.argmin), ("TE", np.argmax)):
        index = pick(rings[:, :, x_col], axis=1)
        chosen = rings[np.arange(len(rings)), index]
        points = np.zeros((len(rings), 3))
        points[:, axis] = stations
        points[:, cols[0]] = chosen[:, 0]
        points[:, cols[1]] = chosen[:, 1]
        out[label] = points
    return out


def main() -> None:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    features = []
    for part in data["parts"]:
        if part["name"] == "fuselage":
            continue
        for label, points in extreme_points(part).items():
            features.append({"name": f"{part['name']}_{label}", "polyline": points.tolist()})
            if part["axis"] == 1:  # mirrored port side
                mirror = points * np.array([1.0, -1.0, 1.0])
                features.append({"name": f"{part['name']}_{label}_port", "polyline": mirror.tolist()})
    with Path(sys.argv[2]).open("x", encoding="utf-8") as stream:
        json.dump({"tolerance_m": 0.002, "origin": "ring extremes of reconstruction-r3.json (demonstration only)",
                   "features": features}, stream)
    print(len(features), "polylines")


if __name__ == "__main__":
    main()

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
"""Empirical check of the triangle-quality formula against surfaceCheck's own per-triangle values.

surfaceCheck -writeSets vtk writes a VTK PolyData whose cell array `quality` holds OpenFOAM's per-triangle
quality (equilateral = 1). This script tests candidate formulas against it; the earlier search found
Q = 4A / (3 sqrt(3) R^2) (triangle area over the area of the equilateral triangle inscribed in the same
circumcircle) with ratio 1 +/- 6e-8 on 46,592 triangles. 2r/R, 4 sqrt(3) A / sum(e^2) and others do not match.
OpenFOAM source was not read; the formula is a fit to the output.

How to run: uv run --no-project calibrate_quality_vs_surfacecheck.py <input.vtp>
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

import numpy as np


def vtp_array(text: str, name: str, dtype: str) -> np.ndarray:
    """Decode an uncompressed base64 appended-header DataArray from the ASCII VTP."""
    match = re.search(r"<DataArray[^>]*Name='%s'[^>]*>\s*([A-Za-z0-9+/=]+)\s*</DataArray>" % name, text)
    raw = base64.b64decode(match.group(1))
    length = int.from_bytes(raw[:8], "little")
    return np.frombuffer(raw[8:8 + length], dtype=dtype)


def main() -> None:
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    quality = vtp_array(text, "quality", "<f4").astype(np.float64)
    points = vtp_array(text, "Points", "<f4").reshape(-1, 3).astype(np.float64)
    connectivity = vtp_array(text, "connectivity", "<i4").reshape(-1, 3)
    a, b, c = (points[connectivity[:, k]] for k in range(3))
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    sides = np.stack([np.linalg.norm(b - c, axis=1), np.linalg.norm(c - a, axis=1), np.linalg.norm(a - b, axis=1)], axis=1)
    half = sides.sum(axis=1) / 2
    circum = sides.prod(axis=1) / (4 * area)
    candidates = {
        "4A/(3 sqrt3 R^2)  [adopted]": 4 * area / (3 * np.sqrt(3) * circum**2),
        "4 sqrt3 A / sum(e^2)": 4 * np.sqrt(3) * area / (sides**2).sum(axis=1),
        "2r/R": 2 * (area / half) / circum,
        "A / (sqrt3/4 emax^2)": area / (np.sqrt(3) / 4 * sides.max(axis=1) ** 2),
    }
    for label, value in candidates.items():
        ratio = quality / value
        print(f"{label:30s} ratio min {ratio.min():.9f} max {ratio.max():.9f}")
    print("triangles", len(quality), "surfaceCheck quality min", quality.min(), "max", quality.max())


if __name__ == "__main__":
    main()

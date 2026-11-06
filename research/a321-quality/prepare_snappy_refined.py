#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: install uv, then uv run prepare_snappy_refined.py. Fresh candidate only.
"""Retain the first control and tighten skewness/weight controls for a second coupled mesh."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

from custody import verify_input_manifest, write_input_manifest

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Copy dictionaries and immutable input, never copy/overwrite any generated mesh."""
    old = ROOT / "artifacts/snappy-01"
    verify_input_manifest(old)
    new = ROOT / "artifacts/snappy-02"
    new.mkdir(parents=True, exist_ok=False)
    shutil.copytree(old / "system", new / "system")
    shutil.copytree(old / "constant/triSurface", new / "constant/triSurface")
    path = new / "system/snappyHexMeshDict"
    text = path.read_text()
    text = text.replace("nSurfaceLayers 8", "nSurfaceLayers 5").replace(
        "firstLayerThickness 0.001", "firstLayerThickness 0.004"
    )
    text = text.replace("minThickness 0.004", "minThickness 0.006").replace(
        "maxBoundarySkewness 20", "maxBoundarySkewness 3"
    )
    text = text.replace("maxInternalSkewness 4", "maxInternalSkewness 3").replace(
        "minFaceWeight 0.02", "minFaceWeight 0.05"
    )
    text = text.replace("minDeterminant 0.001", "minDeterminant 0.01")
    path.write_text(text, encoding="utf8", newline="\n")
    write_input_manifest(new)
    print(new)


if __name__ == "__main__":
    main()

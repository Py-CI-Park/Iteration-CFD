#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: uv run prepare_conditioning_trials.py; fresh CPU experiments, not physical wall-treatment approval.
"""Separate first-height conditioning from exterior surface-cell resolution."""

from __future__ import annotations

import shutil
from pathlib import Path

from custody import verify_input_manifest, write_input_manifest
from prepare_hotspot_trials import replace_once

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Use identical R3 input and quality limits for two isolated conditioning changes."""
    old = ROOT / "artifacts/snappy-04"
    verify_input_manifest(old)
    original = (old / "system/snappyHexMeshDict").read_text(encoding="utf8")
    heights = replace_once(
        original, "firstLayerThickness 0.001;", "firstLayerThickness 0.004;"
    )
    resolution = replace_once(original, "level (4 5);", "level (5 5);")
    for name, text in (("snappy-06", heights), ("snappy-07", resolution)):
        root = ROOT / "artifacts" / name
        root.mkdir(exist_ok=False)
        shutil.copytree(old / "system", root / "system")
        surface = root / "constant/triSurface"
        surface.mkdir(parents=True)
        shutil.copyfile(
            old / "constant/triSurface/aircraft.stl", surface / "aircraft.stl"
        )
        (root / "system/snappyHexMeshDict").write_text(
            text, encoding="utf8", newline="\n"
        )
        write_input_manifest(root)


if __name__ == "__main__":
    main()

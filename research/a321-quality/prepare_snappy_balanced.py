#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: uv run prepare_snappy_balanced.py; preserves prior candidates.
"""Isolate stricter skewness from the determinant/thickness changes that harmed candidate two."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

from custody import verify_input_manifest, write_input_manifest

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Change only skewness limits from candidate one, retaining nonorthogonality at 65 degrees."""
    old = ROOT / "artifacts/snappy-01"
    verify_input_manifest(old)
    new = ROOT / "artifacts/snappy-03"
    new.mkdir(parents=True, exist_ok=False)
    shutil.copytree(old / "system", new / "system")
    shutil.copytree(old / "constant/triSurface", new / "constant/triSurface")
    path = new / "system/snappyHexMeshDict"
    text = path.read_text()
    text = text.replace("maxBoundarySkewness 20", "maxBoundarySkewness 3").replace(
        "maxInternalSkewness 4", "maxInternalSkewness 3"
    )
    path.write_text(text, encoding="utf8", newline="\n")
    write_input_manifest(new)
    print(new)


if __name__ == "__main__":
    main()

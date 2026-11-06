#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: uv run prepare_hotspot_trials.py; then run_hotspot_trial.sh in WSL.
"""Freeze two controlled variations selected from the snappy-03 hotspot map."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Final

from custody import verify_input_manifest, write_input_manifest

ROOT: Final = Path(__file__).resolve().parent / "artifacts"


def replace_once(text: str, source: str, target: str) -> str:
    """Reject drift of the baseline dictionary rather than applying a partial edit."""
    if text.count(source) != 1:
        raise RuntimeError(f"UNEXPECTED_BASELINE_ENTRY: {source}")
    return text.replace(source, target, 1)


def main() -> None:
    """Preserve all inputs except the declared spatial or layer controls."""
    old = ROOT / "snappy-03"
    verify_input_manifest(old)
    dictionary = (old / "system/snappyHexMeshDict").read_text(encoding="utf8")
    spatial = replace_once(
        dictionary,
        "geometry { aircraft.stl {type triSurfaceMesh; name aircraft;} }",
        """geometry {
 aircraft.stl {type triSurfaceMesh; name aircraft;}
 wingRoot {type searchableBox; min (19 -4.6 1.7); max (26.5 4.6 5.6);}
 tailRoot {type searchableBox; min (38.8 -4.6 4.1); max (44.6 4.6 8.3);}
}""",
    )
    spatial = replace_once(
        spatial,
        "refinementRegions {};",
        """refinementRegions {
 wingRoot {mode inside; levels ((1e15 5));}
 tailRoot {mode inside; levels ((1e15 5));}
}""",
    )
    layers = replace_once(
        dictionary,
        "firstLayerThickness 0.001; minThickness 0.004;",
        "firstLayerThickness 0.00075; minThickness 0.002;",
    )
    variants = (("snappy-04", spatial), ("snappy-05", layers))
    for name, text in variants:
        new = ROOT / name
        new.mkdir(exist_ok=False)
        shutil.copytree(old / "system", new / "system")
        target = new / "constant/triSurface"
        target.mkdir(parents=True)
        shutil.copyfile(
            old / "constant/triSurface/aircraft.stl", target / "aircraft.stl"
        )
        (new / "system/snappyHexMeshDict").write_text(
            text, encoding="utf8", newline="\n"
        )
        write_input_manifest(new)


if __name__ == "__main__":
    main()

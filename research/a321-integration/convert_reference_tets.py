#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run convert_reference_tets.py
"""Convert preserved R2 control mesh to polyMesh, explicitly not an improved R3 mesh."""

from __future__ import annotations

from pathlib import Path

import convert_hybrid
import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Reuse fixed converter on stored R2 tets; no mesher or solver invocation."""
    out = ROOT / "artifacts/r2-reference-polymesh"
    out.mkdir(exist_ok=False)
    with np.load(ROOT.parent / "a321-shell/artifacts/meshpy-r1/fluid.npz") as d:
        np.savez_compressed(
            out / "hybrid.npz",
            vertices=d["vertices"],
            tets=d["cells"],
            prisms=np.empty((0, 6), dtype=np.int64),
        )
    convert_hybrid.convert(out, "polyMesh-r2-control-quality.json")


if __name__ == "__main__":
    main()

# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "manifold3d"]
# ///
"""Optional display union of the four component STLs with manifold3d, outside Blender (not a gate, not a CFD input).

How to run: uv run display_union.py --attempt <dir> --out <new stl>
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import manifold3d as mf
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_io


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    start = time.perf_counter()
    solids = []
    for name in ("fuselage", "wing", "horizontal", "vertical"):
        v, f = r6_io.weld(r6_io.read_stl(args.attempt / f"{name}.stl"))
        solid = mf.Manifold(mf.Mesh(v.astype(np.float32), f.astype(np.uint32)))
        if solid.status() != mf.Error.NoError:
            raise RuntimeError(f"{name}: {solid.status()}")
        solids.append(solid)
    union = solids[0]
    for s in solids[1:]:
        union = union + s
    mesh = union.to_mesh()
    tri = mesh.vert_properties[:, :3][mesh.tri_verts]
    r6_io.write_stl(args.out, tri, "display union")
    print({"status": str(union.status()), "triangles": int(len(tri)), "components": len(union.decompose()), "seconds": round(time.perf_counter() - start, 1)})


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "meshpy"]
# ///
# How to run: uv run exterior_tets.py; CPU diagnostic mesh only.
"""Attach an exterior tetrahedral region without moving the prism interface."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import trimesh
from build_layers import jacobian_minimum, require_positive_jacobians
from interface_map import align_interface
from meshpy import tet

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Preserve layer point indices and record exterior mesher failure or success."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", action="store_true")
    quality = parser.parse_args().quality
    source = ROOT / "artifacts/constrained-exact-02"
    root = ROOT / "artifacts/quality-exterior-03" if quality else source
    if quality:
        root.mkdir(parents=True, exist_ok=False)
    if (root / "hybrid.npz").exists() or (root / "tetgen-raw.npz").exists():
        raise RuntimeError("EXTERIOR_ARTIFACT_ALREADY_EXISTS")
    start = time.monotonic()
    with np.load(source / "layers.npz") as data:
        vertices, prisms, faces = data["vertices"], data["prisms"], data["wall_faces"]
        heights, scale = data["heights"], data["scale"]
    require_positive_jacobians(jacobian_minimum(vertices, prisms))
    n = len(vertices) // len(heights)
    outer = vertices[-n:]
    box = trimesh.creation.box(extents=[180, 130, 100])
    box.apply_translation([45, 0, 5])
    box = box.subdivide().subdivide().subdivide()
    info = tet.MeshInfo()
    info.set_points(np.vstack((outer, box.vertices)).tolist())
    info.set_facets(np.vstack((faces, box.faces + n)).tolist())
    info.set_holes([[22, 0, 4]])
    print("TETGEN_START", flush=True)
    options = "pq2a100YMQO/1" if quality else "pYQ"
    record = {"gpu_compute": False, "solver_executed": False, "options": options}
    try:
        result = tet.build(info, options=tet.Options(options), verbose=False)
        tv = np.array(result.points)
        tc = np.array(result.elements, dtype=np.int64)
        np.savez_compressed(root / "tetgen-raw.npz", vertices=tv, tets=tc)
        record["initial_interface_sequence_exact"] = bool(np.array_equal(tv[:n], outer))
        tv, tc = align_interface(tv, tc, outer)
        combined = np.vstack((vertices[:-n], tv))
        tc += (len(heights) - 1) * n
        np.savez_compressed(
            root / "hybrid.npz",
            vertices=combined,
            tets=tc,
            prisms=prisms,
            wall_faces=faces,
            heights=heights,
            layer_scale=scale,
        )
        record.update(
            status="BUILT_QUALITY_PENDING",
            tets=len(tc),
            prisms=len(prisms),
            points=len(combined),
        )
    except RuntimeError as exc:
        record.update(status="EXTERIOR_BUILD_FAILED", error=str(exc))
    record["seconds"] = time.monotonic() - start
    name = "exterior-tets-quality-03.json" if quality else "exterior-tets.json"
    (ROOT / "evidence" / name).write_text(json.dumps(record, indent=2), encoding="utf8")
    print(json.dumps(record))
    if record["status"] != "BUILT_QUALITY_PENDING":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "pymeshlab"]
# ///
"""Second, independent self-intersection checker: PyMeshLab per-face selection.

PyMeshLab is GPL-3.0. It is called only from this separate process, which exchanges
JSON with the gate; no PyMeshLab code is imported by, or copied into, the other modules.
The mesh is built from the gate's own exact-coordinate weld (not MeshLab's STL loader) so
welded face i is STL facet i.

How to run: uv run --no-project r6_meshlab_worker.py <input.stl> <output.json>
"""
from __future__ import annotations

import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np
import pymeshlab

from r6_mesh import load_stl, weld


def run(stl: Path) -> dict:
    """Select self-intersecting faces on the welded mesh; return counts and face ids."""
    started = time.perf_counter()
    vertices, faces = weld(load_stl(stl))
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(pymeshlab.Mesh(vertex_matrix=vertices, face_matrix=faces.astype(np.int32)))
    mesh_set.compute_selection_by_self_intersections_per_face()
    current = mesh_set.current_mesh()
    if current.face_number() != len(faces):
        raise RuntimeError("PyMeshLab changed the face count; face ids no longer map to STL order")
    selected = np.flatnonzero(current.face_selection_array())
    return {"checker": "pymeshlab compute_selection_by_self_intersections_per_face",
            "pymeshlab_version": importlib.metadata.version("pymeshlab"),
            "faces": int(len(faces)), "selected_faces": int(len(selected)),
            "selected_face_ids": selected.tolist(), "wall_seconds": time.perf_counter() - started}


def main() -> None:
    result = run(Path(sys.argv[1]))
    with Path(sys.argv[2]).open("x", encoding="utf-8") as stream:
        json.dump(result, stream, allow_nan=False)
    print(json.dumps({k: result[k] for k in ("selected_faces", "wall_seconds")}))


if __name__ == "__main__":
    main()

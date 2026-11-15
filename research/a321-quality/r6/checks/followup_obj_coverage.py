# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "pymeshlab"]
# ///
"""Follow-up to the baseline run: ask surfaceCheck (outputThreshold 100) for its self-intersection points
and match them to faces flagged by the other checkers and to low-quality faces.

Matching is by AABB within 100 um (the OBJ has 6 significant digits); it is a location-matching radius,
not an intersection tolerance. surfaceCheck runs on a copy in a fresh attempt directory.

How to run: uv run --no-project followup_obj_coverage.py <name> <stl> <logs-dir> <out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from r6_mesh import load_stl, sha256_file, weld
from r6_metrics import triangle_quality
from r6_selfint import points_covered_by_faces, surfacecheck_run


def main() -> None:
    name, stl, logs, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    full = json.loads((logs / f"{name}-full-report.json").read_text(encoding="utf-8"))
    before = sha256_file(stl)
    triangles = load_stl(stl)
    result = surfacecheck_run(f"{name}-obj", stl, threshold=100)
    points = np.array(result["obj_points_m"]).reshape(-1, 3)
    vertices, faces = weld(triangles)
    q = triangle_quality(vertices, faces)["q_of"]
    low = np.flatnonzero(q < 0.01).tolist()
    locator_ids = full["self_intersection"]["locator"]["face_ids"]
    meshlab_ids = full["self_intersection"]["meshlab"]["selected_face_ids"]
    summary = {
        "name": name, "surfacecheck_locations": result["self_intersection_locations"], "obj_points": int(len(points)),
        "unique_obj_points_6sig": int(len({tuple(p) for p in points.tolist()})), "attempt_dir": result["attempt_dir"],
        "points_near_locator_faces": points_covered_by_faces(points, triangles, locator_ids),
        "points_near_meshlab_faces": points_covered_by_faces(points, triangles, meshlab_ids),
        "points_near_faces_with_q_of_below_0.01": points_covered_by_faces(points, triangles, low),
        "faces_q_of_below_0.01": len(low), "meshlab_faces": len(meshlab_ids), "locator_faces": len(locator_ids),
        "meshlab_face_midpoints_m": [triangles[i].mean(axis=0).tolist() for i in meshlab_ids[:20]],
        "meshlab_face_q_of": [float(q[i]) for i in meshlab_ids[:20]],
        "radius_m": 1e-4, "sha256_unchanged": before == sha256_file(stl),
    }
    with out.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, allow_nan=False)
    print({k: v for k, v in summary.items() if not k.startswith("meshlab_face")})


if __name__ == "__main__":
    main()

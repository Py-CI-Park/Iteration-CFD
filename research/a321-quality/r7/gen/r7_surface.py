# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Contract 03 M5 assembly of a ring grid into one closed triangle surface (shared by the barrels and the R7 fuselage).

points (R, N, 3): row 0 and row R-1 are the closure end rings (1 mm bands, scaled end rings), rows 1 and R-2 the band
boundary rings. 02c leaning-strip tessellation over all rows, round caps (no pole fan) on the end rings, float32-exact
vertices, outward orientation, 02d flip with quad-scope refusal and Q margin (r7_flip). No vertex is moved afterwards."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import numpy as np

import r7_common

r7_common.add_paths()
import r6_tess  # noqa: E402
import r7_flip  # noqa: E402


def closure_ring(ring: np.ndarray, x_new: float, scale: float) -> np.ndarray:
    """End ring of a 1 mm closure band: the full ring scaled about its vertex centroid, moved to x_new."""
    c = ring.mean(axis=0)
    out = c + scale * (ring - c)
    out[:, 0] = x_new
    return out


def assemble(points: np.ndarray, x_plateau_end: float | None = None) -> dict:
    rows, cols, _ = points.shape
    vertices, faces, leaning = r6_tess.lean_triangles(points)
    n_grid = len(vertices)
    all_faces = [faces]
    caps = []
    for label, row in (("first", 0), ("last", rows - 1)):
        ids = row * cols + np.arange(cols)
        new, cap = r6_tess.round_cap(vertices, ids)
        cap = r7_common.orient_cap(np.vstack(all_faces), cap, ids)
        start = len(vertices)
        vertices = np.vstack([vertices, new])
        all_faces.append(np.asarray(cap, dtype=np.int64))
        caps.append({"label": label, "row": row, "boundary_ids": ids.tolist(), "new_vertices": [start, len(vertices)], "triangles": len(cap)})
    faces = np.vstack(all_faces)
    vertices = vertices.astype(np.float32).astype(np.float64)
    if r7_common.signed_volume(vertices, faces) < 0:
        faces = faces[:, ::-1].copy()
    feature_rows = (0, 1, rows - 2, rows - 1)
    feature_edges: set = set()
    for row in feature_rows:
        feature_edges |= r7_common.ring_edges(row * cols + np.arange(cols))
    faces_flipped, flip = r7_flip.flip_axis_parallel(vertices, faces, feature_edges, r7_common.load_limits())
    row_of = np.full(len(vertices), -1, dtype=np.int64)
    col_of = np.full(len(vertices), -1, dtype=np.int64)
    row_of[:n_grid] = np.arange(n_grid) // cols
    col_of[:n_grid] = np.arange(n_grid) % cols
    region = np.empty(len(vertices), dtype="<U8")
    for i in range(n_grid):
        r = i // cols
        region[i] = "band" if r in (0, rows - 1) else ("plateau" if (x_plateau_end is None or points[r, 0, 0] <= x_plateau_end + 1e-9) else "taper")
    region[n_grid:] = "cap"
    val = r7_common.valence(faces_flipped, len(vertices))
    manifest = {
        "rows": rows, "columns": cols, "vertices": len(vertices), "triangles": len(faces_flipped), "leaning_strips": len(leaning), "strips_total": rows - 1,
        "leaning_strip_rows": leaning if len(leaning) <= 400 else f"{len(leaning)} strips (list omitted)", "caps": caps, "max_valence": int(val.max()),
        "valence_histogram": np.bincount(val).tolist(), "signed_volume_m3": r7_common.signed_volume(vertices, faces_flipped), "stations_x_m": points[:, 0, 0].tolist(),
        "feature_rows": list(feature_rows), "flip": {k: v for k, v in flip.items() if k not in ("flips", "refusals")}, "flip_refusals": flip["refusals"][:300], "flip_flips": flip["flips"][:300],
    }
    return {"vertices": vertices, "faces": faces_flipped, "row": row_of, "col": col_of, "region": region, "manifest": manifest, "feature_rows": feature_rows}

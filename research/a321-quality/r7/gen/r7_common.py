# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Shared helpers of the R7 generator (cap orientation, volume, valence, 02a limits, paths, hashing).

Derived from research/a321-quality/r6/gen/build_r6.py (copied and trimmed; the R6 files are not modified)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parent
QUALITY = HERE.parents[1]  # research/a321-quality
REPO = HERE.parents[3]
R6_GEN = QUALITY / "r6" / "gen"
R6_CHECKS = QUALITY / "r6" / "checks"
R7_MEASURE = QUALITY / "r7" / "measure"
PLANS = QUALITY / "r6" / "plans"
WORK = REPO / ".worktmp" / "r7-gen"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_paths() -> None:
    """Make the R6 gate suite, the R6 tessellation helpers and the committed R7 measurement modules importable."""
    for p in (R6_GEN, R6_CHECKS, R7_MEASURE, HERE):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def _boundary_directed(faces: np.ndarray, boundary: np.ndarray) -> set:
    big = int(max(faces.max(), boundary.max())) + 1
    keys = np.minimum(boundary, np.roll(boundary, -1)) * big + np.maximum(boundary, np.roll(boundary, -1))
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    ekey = np.minimum(edges[:, 0], edges[:, 1]) * big + np.maximum(edges[:, 0], edges[:, 1])
    hit = edges[np.isin(ekey, keys)]
    return {(int(u), int(v)) for u, v in hit}


def orient_cap(grid_faces: np.ndarray, cap_faces: list, boundary: np.ndarray) -> list:
    """Flip a cap's faces if it traverses a shared boundary edge in the same direction as the grid does."""
    grid_dir = _boundary_directed(grid_faces, boundary)
    cap_dir = _boundary_directed(np.asarray(cap_faces, dtype=np.int64), boundary)
    return [(f[0], f[2], f[1]) for f in cap_faces] if grid_dir & cap_dir else cap_faces


def signed_volume(vertices: np.ndarray, faces: np.ndarray) -> float:
    tri = vertices[faces]
    return float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)


def valence(faces: np.ndarray, count: int) -> np.ndarray:
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    return np.bincount(e.ravel(), minlength=count)


def load_limits() -> dict:
    """02a per-triangle limits used by the 02d flip rule."""
    th = json.loads((PLANS / "r6-geometry-contract-02a.json").read_text(encoding="utf-8"))["thresholds_per_component"]
    return {k: th[k]["value"] for k in ("Q_MIN", "ANGLE_MIN_DEG", "ASPECT_MAX", "GRADE_AREA_MAX", "VALENCE_MAX")}


def ring_edges(ids, closed: bool = True) -> set[tuple[int, int]]:
    ids = [int(i) for i in ids]
    seq = ids + ([ids[0]] if closed else [])
    return {(min(a, b), max(a, b)) for a, b in zip(seq[:-1], seq[1:], strict=True)}

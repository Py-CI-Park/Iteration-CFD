#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run audit_polymesh.py; independent readback of already saved polyMesh.
"""Memory-bounded triangular/quad polyMesh reader and cell quality audit."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from convert_fast import geometry
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parent


def read_rows(path: Path, width: int, real: bool = False) -> np.ndarray:
    """Read counted ASCII arrays line by line, never build million Python face lists."""
    with path.open(encoding="utf8") as handle:
        for line in handle:
            if line.strip().isdigit():
                count = int(line)
                break
        if next(handle).strip() != "(":
            raise RuntimeError("BAD_COUNTED_LIST")
        result = np.full((count, width), -1, dtype=np.float64 if real else np.int64)
        for i in range(count):
            line = next(handle).strip()
            if width == 4:
                n = int(line[: line.index("(")])
                values = np.fromstring(
                    line[line.index("(") + 1 : line.index(")")], sep=" ", dtype=np.int64
                )
                if len(values) != n:
                    raise RuntimeError("FACE_ARITY_MISMATCH")
            else:
                values = np.fromstring(
                    line.replace("(", "").replace(")", ""), sep=" ", dtype=result.dtype
                )
            result[i, : len(values)] = values
    return result


def main() -> None:
    """Audit every saved face, preserving failed gate measurements."""
    root = ROOT / "artifacts/hybrid-r5"
    pm = root / "case/constant/polyMesh"
    v = read_rows(pm / "points", 3, True)
    faces = read_rows(pm / "faces", 4)
    owner = read_rows(pm / "owner", 1).ravel()
    neighbour = read_rows(pm / "neighbour", 1).ravel()
    with np.load(root / "hybrid.npz") as d:
        source = d["vertices"]
        tets = d["tets"]
        prisms = d["prisms"]
        centers = np.vstack((v[tets].mean(axis=1), v[prisms].mean(axis=1)))
        if not np.array_equal(v, source):
            raise RuntimeError("POINT_READBACK_MISMATCH")
    volume = np.zeros(len(centers))
    closure = np.zeros_like(centers)
    max_angle = 0.0
    bad_angle = 0
    worst_ids = []
    nif = len(neighbour)
    for start in range(0, len(faces), 100000):
        end = min(start + 100000, len(faces))
        sf, cf = geometry(v, faces[start:end])
        o = owner[start:end]
        np.add.at(volume, o, np.einsum("ij,ij->i", sf, cf - centers[o]) / 3)
        np.add.at(closure, o, sf)
        inner = max(0, min(end, nif) - start)
        if inner:
            n = neighbour[start : start + inner]
            np.add.at(
                volume,
                n,
                -np.einsum("ij,ij->i", sf[:inner], cf[:inner] - centers[n]) / 3,
            )
            np.add.at(closure, n, -sf[:inner])
            delta = centers[n] - centers[o[:inner]]
            cos = np.einsum("ij,ij->i", sf[:inner], delta) / (
                np.linalg.norm(sf[:inner], axis=1) * np.linalg.norm(delta, axis=1)
            )
            angle = np.degrees(np.arccos(np.clip(cos, -1, 1)))
            max_angle = max(max_angle, float(angle.max()))
            bad_angle += int(np.count_nonzero(angle > 70))
            worst_ids.extend((np.flatnonzero(angle > 70)[:5] + start).tolist())
    closure_error = np.linalg.norm(closure, axis=1) / np.maximum(
        np.abs(volume), 1e-100
    ) ** (2 / 3)
    graph = coo_matrix(
        (np.ones(nif), (owner[:nif], neighbour)), shape=(len(centers), len(centers))
    )
    components, _ = connected_components(graph, directed=False)
    with np.load(root / "hybrid.npz") as d:
        heights = d["heights"]
        scale = d["layer_scale"]
    record = {
        "polyMesh": str(pm),
        "points": len(v),
        "faces": len(faces),
        "internal_faces": nif,
        "cells": len(centers),
        "prisms": len(prisms),
        "tets": len(tets),
        "points_readback_exact": True,
        "fluid_components": components,
        "nonpositive_cells": int(np.count_nonzero(volume <= 0)),
        "min_volume_m3": float(volume.min()),
        "total_volume_m3": float(volume.sum()),
        "max_relative_closure": float(closure_error.max()),
        "max_nonorth_deg": max_angle,
        "faces_nonorth_gt70": bad_angle,
        "bad_face_samples": worst_ids[:15],
        "layers": 5,
        "first_layer_thickness_min_m": float(scale.min() * heights[1]),
        "first_layer_thickness_median_m": float(np.median(scale) * heights[1]),
        "first_layer_thickness_max_m": float(scale.max() * heights[1]),
        "total_stack_min_m": float(scale.min() * heights[-1]),
        "total_stack_median_m": float(np.median(scale) * heights[-1]),
        "status": "FIX_FIRST",
        "ofgpu_gate": "NOT_RUN",
        "solver_executed": False,
        "note": "five thin trial prism layers do not establish useful boundary-layer capture; no solved y+",
    }
    np.savez_compressed(
        root / "audited-cell-geometry.npz", centers=centers, volume=volume
    )
    (ROOT / "evidence/polyMesh-quality.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()
